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
    JsonDict,
    JsonValue,
    NodeMetadataInput,
    NodeMetadataInputT,
    NodeType,
    node_attributes,
    node_type_of,
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
    insert: typing.Callable[..., JsonDict]
    extract: typing.Callable[..., tuple[JsonDict, object]]
    detect: typing.Callable[[Mapping[str, JsonValue]], str | None]
    validate_group_metadata: typing.Callable[..., object]
    validate_array_metadata: typing.Callable[..., object]
    validate_node_metadata: typing.Callable[..., object]
    resolve_read_revision: (
        typing.Callable[[Mapping[str, JsonValue], str | None], str] | None
    ) = None


_REGISTRY: Final[dict[ConventionName, _ConventionModule]] = {
    "geo-proj": _ConventionModule(
        proj.UUID,
        proj.CONVENTION_KEYS,
        proj.validate,
        proj.insert,
        proj.extract,
        proj.detect,
        proj.validate_group_metadata,
        proj.validate_array_metadata,
        proj.validate_node_metadata,
        proj._resolve_read_revision,  # pylint: disable=protected-access
    ),
    "spatial": _ConventionModule(
        spatial.UUID,
        spatial.CONVENTION_KEYS,
        spatial.validate,
        spatial.insert,
        spatial.extract,
        spatial.detect,
        spatial.validate_group_metadata,
        spatial.validate_array_metadata,
        spatial.validate_node_metadata,
        spatial._resolve_read_revision,  # pylint: disable=protected-access
    ),
    "multiscales": _ConventionModule(
        multiscales.UUID,
        multiscales.CONVENTION_KEYS,
        multiscales.validate,
        multiscales.insert,
        multiscales.extract,
        multiscales.detect,
        multiscales.validate_group_metadata,
        multiscales.validate_array_metadata,
        multiscales.validate_node_metadata,
        multiscales._resolve_read_revision,  # pylint: disable=protected-access
    ),
    "license": _ConventionModule(
        license_.UUID,
        license_.CONVENTION_KEYS,
        license_.validate,
        license_.insert,
        license_.extract,
        license_.detect,
        license_.validate_group_metadata,
        license_.validate_array_metadata,
        license_.validate_node_metadata,
    ),
    "uom": _ConventionModule(
        uom.UUID,
        uom.CONVENTION_KEYS,
        uom.validate,
        uom.insert,
        uom.extract,
        uom.detect,
        uom.validate_group_metadata,
        uom.validate_array_metadata,
        uom.validate_node_metadata,
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
        "proj:projjson": NotRequired[JsonDict],
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
    extra_items=JsonValue,
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
    """Return ``{'revision': label}`` if this module supports revisions and a
    label was requested for *name*, else an empty dict.

    For the WRITE path (``create_many``/``insert_many``) only: there is no
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
    attrs: Mapping[str, JsonValue],
) -> dict[str, str]:
    """Resolve the revision for a READ over *attrs* and return it as kwargs.

    Like :func:`_rev_kwargs`, but when no explicit override is given and the
    module supports revisions, the revision is detected ONCE from *attrs* and
    pinned. This must be threaded to *both* ``extract`` and ``validate`` so a
    document detected as (say) r1 is not re-detected as LATEST after ``extract``
    has stripped its ``zarr_conventions`` entry.
    """
    if mod.resolve_read_revision is None:
        return {}
    if revisions and name in revisions:
        return {"revision": revisions[name]}
    return {"revision": mod.resolve_read_revision(attrs, None)}


def _detect_conventions(attrs: Mapping[str, JsonValue]) -> frozenset[ConventionName]:
    """Identify which conventions are present by matching UUIDs in zarr_conventions."""
    conventions = validate_convention_metadata_objects(attrs.get("zarr_conventions"))
    uuids = {cmo.get("uuid") for cmo in conventions}
    return frozenset(name for name, mod in _REGISTRY.items() if mod.UUID in uuids)


def create_many(
    conventions: Mapping[ConventionName, Mapping[str, JsonValue]],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> JsonDict:
    """Create and insert multiple conventions into a single attributes dict.

    Parameters
    ----------
    conventions
        Mapping from convention display name (e.g. ``"geo-proj"``) to
        already-formed convention data (the ``AttrsT`` value).
    revisions
        Optional mapping from convention name to revision label. When a
        convention is listed here and its module supports revisions, that
        revision is used; otherwise the module's default applies.

    Returns
    -------
    JsonDict
        A new attributes dict containing all convention data and a
        combined ``zarr_conventions`` array.
    """
    result: JsonDict = {}
    for name, data in conventions.items():
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        mod.validate(data, **rk)
        result = mod.insert(result, data, overwrite=True, **rk)
    return result


def validate_many(
    attrs: Mapping[str, JsonValue],
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> Mapping[str, JsonValue]:
    """Validate multiple conventions within an attributes dict.

    Parameters
    ----------
    attrs
        The attributes dict to validate.
    conventions
        Convention names to validate.
    revisions
        Optional mapping from convention name to revision label. When a
        convention is listed here and its module supports revisions, that
        revision is used; otherwise the module's default applies.

    Returns
    -------
    JsonDict
        The input *attrs* (pass-through on success).
    """
    for name in conventions:
        mod = _get_module(name)
        rk = _read_rev_kwargs(mod, revisions, name, attrs)
        _, extracted = mod.extract(attrs, **rk)
        mod.validate(validate_json_object(extracted), **rk)
    return attrs


def insert_many(
    attrs: Mapping[str, JsonValue],
    conventions: Mapping[ConventionName, Mapping[str, JsonValue]],
    *,
    overwrite: bool = False,
    revisions: dict[ConventionName, str] | None = None,
) -> JsonDict:
    """Insert multiple conventions into an attributes dict.

    Parameters
    ----------
    attrs
        The existing attributes dict.
    conventions
        Mapping from convention display name to already-formed convention data.
    overwrite
        If False (default), raise ``ValueError`` when *attrs* already
        contains keys present in a convention's data.
    revisions
        Optional mapping from convention name to revision label. When a
        convention is listed here and its module supports revisions, that
        revision is used; otherwise the module's default applies.

    Returns
    -------
    JsonDict
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
    attrs: Mapping[str, JsonValue],
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> tuple[JsonDict, dict[ConventionName, JsonDict]]:
    """Extract multiple conventions from an attributes dict.

    Parameters
    ----------
    attrs
        The attributes dict to extract from.
    conventions
        Convention names to extract.
    revisions
        Optional mapping from convention name to revision label. When a
        convention is listed here and its module supports revisions, that
        revision is used; otherwise the module's default applies.

    Returns
    -------
    tuple[JsonDict, dict[str, JsonDict]]
        ``(remaining_attrs, extracted)`` where *extracted* maps
        convention names to their convention data dicts.
    """
    remaining = dict(attrs)
    extracted: dict[ConventionName, JsonDict] = {}
    for name in conventions:
        mod = _get_module(name)
        rk = _read_rev_kwargs(mod, revisions, name, remaining)
        remaining, data = mod.extract(remaining, **rk)
        extracted[name] = validate_json_object(data)
    return remaining, extracted


def validate_all(
    attrs: Mapping[str, JsonValue],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> Mapping[str, JsonValue]:
    """Validate all detected conventions within an attributes dict.

    Detects which conventions are present by matching UUIDs in
    ``zarr_conventions``, then validates each one.

    Parameters
    ----------
    attrs
        The attributes dict to validate.
    revisions
        Optional mapping from convention name to revision label. When a
        convention is listed here and its module supports revisions, that
        revision is used; otherwise the module's default applies.

    Returns
    -------
    JsonDict
        The input *attrs* (pass-through on success).
    """
    return validate_many(attrs, _detect_conventions(attrs), revisions=revisions)


def extract_all(
    attrs: Mapping[str, JsonValue],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> tuple[JsonDict, dict[ConventionName, JsonDict]]:
    """Extract all detected conventions from an attributes dict.

    Detects which conventions are present by matching UUIDs in
    ``zarr_conventions``, then extracts each one.

    Parameters
    ----------
    attrs
        The attributes dict to extract from.
    revisions
        Optional mapping from convention name to revision label. When a
        convention is listed here and its module supports revisions, that
        revision is used; otherwise the module's default applies.

    Returns
    -------
    tuple[JsonDict, dict[str, JsonDict]]
        ``(remaining_attrs, extracted)`` where *extracted* maps
        convention names to their convention data dicts.
    """
    return extract_many(attrs, _detect_conventions(attrs), revisions=revisions)


def validate_group_metadata(
    metadata: NodeMetadataInputT,
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> NodeMetadataInputT:
    """Validate a full v3 group metadata document against every convention it declares.

    The node-level counterpart of `validate_all()`: it sees the whole
    document, so conventions can enforce the rules that depend on `node_type`
    -- `multiscales` applies only to groups, and `spatial:dimensions` is
    required only on arrays.

    Conventions the document does not declare are skipped. Which conventions
    those are is runtime data, so unlike the per-convention validators this
    cannot narrow the document's `attributes` type; it returns its input at
    the type it came in with. Call a convention's own
    `validate_group_metadata` when you want the narrowed result.

    Args:
        metadata: The full metadata document (the contents of a group's `zarr.json`).
        revisions: Optional mapping from convention name to revision label. When a
            convention is listed here and its module supports revisions, that
            revision is used; otherwise the revision is detected from the document.

    Returns:
        The input `metadata`, unchanged.
    """
    _validate_node_metadata(metadata, "group", revisions=revisions)
    return metadata


def validate_array_metadata(
    metadata: NodeMetadataInputT,
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> NodeMetadataInputT:
    """Validate a full v3 array metadata document against every convention it declares.

    The array counterpart of `validate_group_metadata()`; see there for
    parameters and semantics.
    """
    _validate_node_metadata(metadata, "array", revisions=revisions)
    return metadata


def validate_node_metadata(
    metadata: NodeMetadataInputT,
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> NodeMetadataInputT:
    """Validate a full v3 node metadata document against every convention it declares.

    Dispatches on the document's `node_type` to `validate_array_metadata()`
    or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(metadata, revisions=revisions)
    return validate_group_metadata(metadata, revisions=revisions)


def _validate_node_metadata(
    metadata: NodeMetadataInput,
    node_type: NodeType,
    *,
    revisions: dict[ConventionName, str] | None,
) -> None:
    """Fan a node metadata document out over every convention it declares."""
    node_type_of(metadata, expected=node_type)
    attrs = node_attributes(metadata)
    for name in sorted(_detect_conventions(attrs)):
        mod = _get_module(name)
        rk = _read_rev_kwargs(mod, revisions, name, attrs)
        if node_type == "array":
            mod.validate_array_metadata(metadata, **rk)
        else:
            mod.validate_group_metadata(metadata, **rk)


def detect_revisions(
    attrs: Mapping[str, JsonValue],
) -> dict[ConventionName, str | None]:
    """Map each present convention to the revision label it claims.

    Detects which conventions are present (by UUID) and returns a mapping from
    each present convention's display name to its claimed revision label, or
    ``None`` if present at an unrecognized revision. Absent conventions are not
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
    "JsonDict",
    "JsonValue",
    "LayoutObject",
    "LayoutObjectR2",
    "LicenseAttrs",
    "LicenseConventionAttrs",
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
    "validate_array_metadata",
    "validate_convention_metadata_object",
    "validate_group_metadata",
    "validate_many",
    "validate_node_metadata",
]
