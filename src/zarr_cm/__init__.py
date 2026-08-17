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

ConventionName = Literal["proj", "spatial", "multiscales", "license", "uom", "geo-proj"]
"""Display names accepted by the multi-convention functions.

`"geo-proj"` is the pre-rename spelling of `"proj"`; it is still accepted
everywhere a name is taken as input, but functions that *report* names
(`extract_all`, `detect_revisions` ...) always use the canonical `"proj"`.
"""

CanonicalConventionName = Literal["proj", "spatial", "multiscales", "license", "uom"]
"""The canonical subset of `ConventionName` (no aliases)."""


class _ConventionModule(NamedTuple):
    UUID: str
    CMO: ConventionMetadataObject
    CONVENTION_KEYS: set[str]
    validate: typing.Callable[..., object]
    insert: typing.Callable[..., JSONDict]
    extract: typing.Callable[..., tuple[JSONDict, object]]
    detect: typing.Callable[[Mapping[str, JSONValue]], str | None]
    resolve_read_revision: (
        typing.Callable[[Mapping[str, JSONValue], str | None], str] | None
    ) = None
    LATEST: str | None = None
    revision_cmos: Mapping[str, ConventionMetadataObject] | None = None


_REGISTRY: Final[dict[CanonicalConventionName, _ConventionModule]] = {
    "proj": _ConventionModule(
        proj.UUID,
        proj.CMO,
        proj.CONVENTION_KEYS,
        proj.validate,
        proj.insert,
        proj.extract,
        proj.detect,
        proj._resolve_read_revision,  # pylint: disable=protected-access
        proj.LATEST,
        {"r2": proj.r2.CMO, "r3": proj.r3.CMO},
    ),
    "spatial": _ConventionModule(
        spatial.UUID,
        spatial.CMO,
        spatial.CONVENTION_KEYS,
        spatial.validate,
        spatial.insert,
        spatial.extract,
        spatial.detect,
        spatial._resolve_read_revision,  # pylint: disable=protected-access
        spatial.LATEST,
        {"r2": spatial.r2.CMO, "r3": spatial.r3.CMO},
    ),
    "multiscales": _ConventionModule(
        multiscales.UUID,
        multiscales.CMO,
        multiscales.CONVENTION_KEYS,
        multiscales.validate,
        multiscales.insert,
        multiscales.extract,
        multiscales.detect,
        multiscales._resolve_read_revision,  # pylint: disable=protected-access
        multiscales.LATEST,
        {"r2": multiscales.r2.CMO},
    ),
    "license": _ConventionModule(
        license_.UUID,
        license_.CMO,
        license_.CONVENTION_KEYS,
        license_.validate,
        license_.insert,
        license_.extract,
        license_.detect,
    ),
    "uom": _ConventionModule(
        uom.UUID,
        uom.CMO,
        uom.CONVENTION_KEYS,
        uom.validate,
        uom.insert,
        uom.extract,
        uom.detect,
    ),
}

CONVENTION_ALIASES: Final[dict[str, CanonicalConventionName]] = {"geo-proj": "proj"}
"""Accepted non-canonical spellings, mapped to their canonical name."""

CONVENTION_NAMES: Final = frozenset(_REGISTRY)
"""The canonical convention names (aliases excluded)."""

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
        # proj
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


def _canonical(name: str) -> CanonicalConventionName:
    """Resolve *name* (canonical or alias) to its canonical convention name."""
    resolved = CONVENTION_ALIASES.get(name, name)
    # Iterating the registry keys (rather than `if resolved in _REGISTRY`) is
    # what lets every mypy version narrow `str` to the Literal without a cast;
    # some versions flag the cast as redundant, others require it.
    for key in _REGISTRY:
        if key == resolved:
            return key
    msg = f"Unknown convention {name!r}. Valid names: {sorted(CONVENTION_NAMES)}"
    raise ValueError(msg)


def _get_module(name: ConventionName) -> _ConventionModule:
    """Look up convention module by display name, raise ValueError if unknown."""
    return _REGISTRY[_canonical(name)]


def latest_revisions() -> dict[CanonicalConventionName, str]:
    """Map each revisioned convention to the revision label it writes by default.

    Only conventions that ship more than one revision (`proj`, `spatial`,
    `multiscales`) appear; unrevisioned conventions (`license`, `uom`) are
    omitted. Downstream packages can pin against this to notice when a
    `zarr-cm` upgrade changes what gets written.

    Returns
    -------
    dict[str, str]
        e.g. `{"proj": "r3", "spatial": "r3", "multiscales": "r2"}`.
    """
    return {
        name: mod.LATEST for name, mod in _REGISTRY.items() if mod.LATEST is not None
    }


def convention_metadata(
    name: ConventionName, *, revision: str | None = None
) -> ConventionMetadataObject:
    """Return the `zarr_conventions` registry entry for a convention.

    Parameters
    ----------
    name
        Convention display name (`"proj"`, `"spatial"` ...). The `"geo-proj"`
        alias is accepted.
    revision
        Revision label. Defaults to the latest revision for revisioned
        conventions. Must be `None` for unrevisioned conventions.

    Returns
    -------
    ConventionMetadataObject
        A fresh copy of the convention's metadata object (`uuid`, `schema_url`,
        `spec_url`, `name`, `description`), safe to mutate.

    Raises
    ------
    ValueError
        If *name* is unknown, *revision* is unknown, or *revision* is given for
        an unrevisioned convention.
    """
    mod = _get_module(name)
    if revision is None:
        return ConventionMetadataObject(**mod.CMO)
    if mod.revision_cmos is None:
        msg = f"Convention {name!r} has no revisions; got revision={revision!r}"
        raise ValueError(msg)
    try:
        cmo = mod.revision_cmos[revision]
    except KeyError:
        msg = f"Unknown revision {revision!r} for {name!r}. Valid revisions: {sorted(mod.revision_cmos)}"
        raise ValueError(msg) from None
    return ConventionMetadataObject(**cmo)


def _requested_revision(
    revisions: dict[ConventionName, str] | None, name: ConventionName
) -> str | None:
    """Look up the revision requested for *name*, matching aliases as well.

    Keys in *revisions* that name no known convention are ignored, as before
    aliases existed.
    """
    if not revisions:
        return None
    canonical = _canonical(name)
    for key, label in revisions.items():
        if CONVENTION_ALIASES.get(key, key) == canonical:
            return label
    return None


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
    label = _requested_revision(revisions, name)
    if label is not None and mod.resolve_read_revision is not None:
        return {"revision": label}
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
    label = _requested_revision(revisions, name)
    if label is not None:
        return {"revision": label}
    return {"revision": mod.resolve_read_revision(attrs, None)}


def _detect_conventions(
    attrs: Mapping[str, JSONValue],
) -> frozenset[CanonicalConventionName]:
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
) -> dict[CanonicalConventionName, str | None]:
    """Map each present convention to the revision label it claims.

    Detects which conventions are present (by UUID) and returns a mapping from
    each present convention's display name to its claimed revision label, or
    `None` if present at an unrecognized revision. Absent conventions are not
    included.
    """
    result: dict[CanonicalConventionName, str | None] = {}
    for name in _detect_conventions(attrs):
        result[name] = _get_module(name).detect(attrs)
    return result


__all__ = [
    "ALL_CONVENTION_KEYS",
    "CONVENTION_ALIASES",
    "CONVENTION_NAMES",
    "UCUM",
    "ArrayMetadata",
    "ArrayMetadataInput",
    "CanonicalConventionName",
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
    "convention_metadata",
    "create_many",
    "detect_revisions",
    "extract_all",
    "extract_many",
    "insert_many",
    "latest_revisions",
    "validate_all",
    "validate_convention_metadata_object",
    "validate_many",
]
