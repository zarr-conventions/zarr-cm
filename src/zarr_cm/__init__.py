"""
Copyright (c) 2026 Davis Bennett. All rights reserved.

zarr-cm: Python implementation of Zarr Conventions Metadata
"""

from __future__ import annotations

import typing
from collections.abc import Sequence
from typing import Final, Literal, NamedTuple, NotRequired

from typing_extensions import TypedDict

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

from . import license as license_
from . import multiscales, proj, spatial, uom
from ._core import (
    ArrayMetadata,
    ArrayMetadataInput,
    ConventionAttrs,
    ConventionMetadataObject,
    GroupMetadata,
    GroupMetadataInput,
    JSONDict,
    JSONValue,
    Metadata,
    NodeMetadataInput,
    validate_convention_metadata_object,
    validate_convention_metadata_objects,
    validate_json_object,
)
from ._version import version as __version__
from .geo_proj import (
    GeoProjAttrs,
    GeoProjAttrsR2,
    GeoProjAttrsR3,
    GeoProjConventionAttrs,
    GeoProjConventionAttrsR2,
    GeoProjConventionAttrsR3,
)
from .license import LicenseAttrs, LicenseConventionAttrs
from .multiscales import (
    LayoutObject,
    LayoutObjectR2,
    MultiscalesAttrs,
    MultiscalesAttrsR2,
    MultiscalesConventionAttrs,
    MultiscalesConventionAttrsR2,
    Transform,
    TransformR2,
)
from .spatial import (
    SpatialAttrs,
    SpatialAttrsR2,
    SpatialAttrsR3,
    SpatialConventionAttrs,
    SpatialConventionAttrsR2,
    SpatialConventionAttrsR3,
)
from .uom import UCUM, UomAttrs, UomConventionAttrs

ConventionName = Literal["geo-proj", "spatial", "multiscales", "license", "uom"]


class _ConventionModule(NamedTuple):
    UUID: str
    CONVENTION_KEYS: set[str]
    validate: typing.Callable[..., object]
    insert: typing.Callable[..., JSONDict]
    extract: typing.Callable[..., tuple[JSONDict, object]]
    detect: typing.Callable[[Mapping[str, JSONValue]], str | None]
    resolve_read_revision: (
        typing.Callable[[Mapping[str, JSONValue], str | None], str] | None
    ) = None


_REGISTRY: Final[dict[ConventionName, _ConventionModule]] = {
    "geo-proj": _ConventionModule(
        proj.UUID,
        proj.CONVENTION_KEYS,
        proj.validate,
        proj.insert,
        proj.extract,
        proj.detect,
        proj._resolve_read_revision,  # pylint: disable=protected-access
    ),
    "spatial": _ConventionModule(
        spatial.UUID,
        spatial.CONVENTION_KEYS,
        spatial.validate,
        spatial.insert,
        spatial.extract,
        spatial.detect,
        spatial._resolve_read_revision,  # pylint: disable=protected-access
    ),
    "multiscales": _ConventionModule(
        multiscales.UUID,
        multiscales.CONVENTION_KEYS,
        multiscales.validate,
        multiscales.insert,
        multiscales.extract,
        multiscales.detect,
        multiscales._resolve_read_revision,  # pylint: disable=protected-access
    ),
    "license": _ConventionModule(
        license_.UUID,
        license_.CONVENTION_KEYS,
        license_.validate,
        license_.insert,
        license_.extract,
        license_.detect,
    ),
    "uom": _ConventionModule(
        uom.UUID,
        uom.CONVENTION_KEYS,
        uom.validate,
        uom.insert,
        uom.extract,
        uom.detect,
    ),
}

CONVENTION_NAMES: Final = frozenset(_REGISTRY)

ALL_CONVENTION_KEYS: Final = frozenset(
    proj.CONVENTION_KEYS
    | spatial.CONVENTION_KEYS
    | multiscales.CONVENTION_KEYS
    | license_.CONVENTION_KEYS
    | uom.CONVENTION_KEYS
)

MultiConventionAttrs = TypedDict(
    "MultiConventionAttrs",
    {
        "zarr_conventions": NotRequired[Sequence[ConventionMetadataObject]],
        # geo-proj
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[JSONDict],
        # spatial
        "spatial:dimensions": NotRequired[Sequence[str]],
        "spatial:bbox": NotRequired[Sequence[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[Sequence[float]],
        "spatial:shape": NotRequired[Sequence[int]],
        "spatial:registration": NotRequired[str],
        # multiscales
        "multiscales": NotRequired[MultiscalesAttrs],
        # license
        "license": NotRequired[LicenseAttrs],
        # uom
        "uom": NotRequired[UomAttrs],
    },
    extra_items=JSONValue,
)


def _get_module(name: ConventionName) -> _ConventionModule:
    """Look up convention module by display name, raise ValueError if unknown."""
    try:
        return _REGISTRY[name]
    except KeyError:
        msg = f"Unknown convention {name!r}. Valid names: {sorted(CONVENTION_NAMES)}"
        raise ValueError(msg) from None


def _rev_kwargs(
    mod: _ConventionModule,
    revisions: dict[ConventionName, str] | None,
    name: ConventionName,
) -> dict[str, str]:
    """Return `{'revision': label}` if this module supports revisions and a
    label was requested for *name*, else an empty dict.

    For the WRITE path (`create_many`/`insert_many`) only: there is no
    document to detect from, so without an explicit override the module's own
    default (LATEST) applies.
    """
    if revisions and name in revisions and mod.resolve_read_revision is not None:
        return {"revision": revisions[name]}
    return {}


def _read_rev_kwargs(
    mod: _ConventionModule,
    revisions: dict[ConventionName, str] | None,
    name: ConventionName,
    attrs: Mapping[str, JSONValue],
) -> dict[str, str]:
    """Resolve the revision for a READ over *attrs* and return it as kwargs.

    Like `_rev_kwargs`, but when no explicit override is given and the module
    supports revisions, the revision is detected once from `attrs` and pinned.
    This must be threaded to both `extract` and `validate` so extraction cannot
    remove the declaration before validation resolves the revision.
    """
    if mod.resolve_read_revision is None:
        return {}
    if revisions and name in revisions:
        return {"revision": revisions[name]}
    return {"revision": mod.resolve_read_revision(attrs, None)}


def _detect_conventions(attrs: Mapping[str, JSONValue]) -> frozenset[ConventionName]:
    """Identify which conventions are present by matching UUIDs in zarr_conventions."""
    conventions = validate_convention_metadata_objects(attrs.get("zarr_conventions"))
    uuids = {cmo.get("uuid") for cmo in conventions}
    return frozenset(name for name, mod in _REGISTRY.items() if mod.UUID in uuids)


def create_many(
    conventions: Mapping[ConventionName, Mapping[str, JSONValue]],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> JSONDict:
    """Create and insert multiple conventions into a single attributes dict.

    Args:
        conventions: Convention names mapped to already-formed convention data.
        revisions: Optional convention names mapped to revision labels.

    Returns:
        A new attributes dict containing all convention data and a combined
        `zarr_conventions` array.
    """
    result: JSONDict = {}
    for name, data in conventions.items():
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        mod.validate(data, **rk)
        result = mod.insert(result, data, overwrite=True, **rk)
    return result


def validate_many(
    attrs: Mapping[str, JSONValue],
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> Mapping[str, JSONValue]:
    """Validate multiple conventions within an attributes dict.

    Args:
        attrs: The attributes dict to validate.
        conventions: Convention names to validate.
        revisions: Optional convention names mapped to revision labels.

    Returns:
        The input `attrs`, unchanged.
    """
    for name in conventions:
        mod = _get_module(name)
        rk = _read_rev_kwargs(mod, revisions, name, attrs)
        _, extracted = mod.extract(attrs, **rk)
        mod.validate(validate_json_object(extracted), **rk)
    return attrs


def insert_many(
    attrs: Mapping[str, JSONValue],
    conventions: Mapping[ConventionName, Mapping[str, JSONValue]],
    *,
    overwrite: bool = False,
    revisions: dict[ConventionName, str] | None = None,
) -> JSONDict:
    """Insert multiple conventions into an attributes dict.

    Args:
        attrs: The existing attributes dict.
        conventions: Convention names mapped to already-formed convention data.
        overwrite: Whether convention data may replace existing keys.
        revisions: Optional convention names mapped to revision labels.

    Returns:
        A new attributes dict with all convention data merged in.
    """
    result = dict(attrs)
    for name, data in conventions.items():
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        mod.validate(data, **rk)
        result = mod.insert(result, data, overwrite=overwrite, **rk)
    return result


def extract_many(
    attrs: Mapping[str, JSONValue],
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> tuple[JSONDict, dict[ConventionName, JSONDict]]:
    """Extract multiple conventions from an attributes dict.

    Args:
        attrs: The attributes dict to extract from.
        conventions: Convention names to extract.
        revisions: Optional convention names mapped to revision labels.

    Returns:
        `(remaining_attrs, extracted)`, where `extracted` maps convention names
        to their convention data.
    """
    remaining = dict(attrs)
    extracted: dict[ConventionName, JSONDict] = {}
    for name in conventions:
        mod = _get_module(name)
        rk = _read_rev_kwargs(mod, revisions, name, remaining)
        remaining, data = mod.extract(remaining, **rk)
        extracted[name] = validate_json_object(data)
    return remaining, extracted


def validate_all(
    attrs: Mapping[str, JSONValue],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> Mapping[str, JSONValue]:
    """Validate all detected conventions within an attributes dict.

    Detects which conventions are present by matching UUIDs in
    `zarr_conventions`, then validates each one.

    Args:
        attrs: The attributes dict to validate.
        revisions: Optional convention names mapped to revision labels.

    Returns:
        The input `attrs`, unchanged.
    """
    return validate_many(attrs, _detect_conventions(attrs), revisions=revisions)


def extract_all(
    attrs: Mapping[str, JSONValue],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> tuple[JSONDict, dict[ConventionName, JSONDict]]:
    """Extract all detected conventions from an attributes dict.

    Detects which conventions are present by matching UUIDs in
    `zarr_conventions`, then extracts each one.

    Args:
        attrs: The attributes dict to extract from.
        revisions: Optional convention names mapped to revision labels.

    Returns:
        `(remaining_attrs, extracted)`, where `extracted` maps convention names
        to their convention data.
    """
    return extract_many(attrs, _detect_conventions(attrs), revisions=revisions)


def detect_revisions(
    attrs: Mapping[str, JSONValue],
) -> dict[ConventionName, str | None]:
    """Map each present convention to the revision label it claims.

    Detects which conventions are present (by UUID) and returns a mapping from
    each present convention's display name to its claimed revision label, or
    `None` if present at an unrecognized revision. Absent conventions are not
    included.
    """
    result: dict[ConventionName, str | None] = {}
    for name in _detect_conventions(attrs):
        result[name] = _get_module(name).detect(attrs)
    return result


__all__ = [
    "ALL_CONVENTION_KEYS",
    "CONVENTION_NAMES",
    "UCUM",
    "ArrayMetadata",
    "ArrayMetadataInput",
    "ConventionAttrs",
    "ConventionMetadataObject",
    "ConventionName",
    "GeoProjAttrs",
    "GeoProjAttrsR2",
    "GeoProjAttrsR3",
    "GeoProjConventionAttrs",
    "GeoProjConventionAttrsR2",
    "GeoProjConventionAttrsR3",
    "GroupMetadata",
    "GroupMetadataInput",
    "JSONDict",
    "JSONValue",
    "LayoutObject",
    "LayoutObjectR2",
    "LicenseAttrs",
    "LicenseConventionAttrs",
    "Metadata",
    "MultiConventionAttrs",
    "MultiscalesAttrs",
    "MultiscalesAttrsR2",
    "MultiscalesConventionAttrs",
    "MultiscalesConventionAttrsR2",
    "NodeMetadataInput",
    "SpatialAttrs",
    "SpatialAttrsR2",
    "SpatialAttrsR3",
    "SpatialConventionAttrs",
    "SpatialConventionAttrsR2",
    "SpatialConventionAttrsR3",
    "Transform",
    "TransformR2",
    "UomAttrs",
    "UomConventionAttrs",
    "__version__",
    "create_many",
    "detect_revisions",
    "extract_all",
    "extract_many",
    "insert_many",
    "validate_all",
    "validate_convention_metadata_object",
    "validate_many",
]
