"""
Copyright (c) 2026 Davis Bennett. All rights reserved.

zarr-cm: Python implementation of Zarr Conventions Metadata
"""

from __future__ import annotations

import typing
from typing import Final, Literal, NotRequired, Protocol, TypedDict, cast

if typing.TYPE_CHECKING:
    from collections.abc import Iterable

from . import license as license_
from . import multiscales, proj, spatial, uom
from ._core import (
    ConventionAttrs,
    ConventionMetadataObject,
    JsonDict,
    validate_convention_metadata_object,
)
from ._version import version as __version__
from .geo_proj import (
    GeoProjAttrs,
    GeoProjAttrsR1,
    GeoProjAttrsR2,
    GeoProjAttrsR3,
    GeoProjConventionAttrs,
    GeoProjConventionAttrsR1,
    GeoProjConventionAttrsR2,
    GeoProjConventionAttrsR3,
)
from .license import LicenseAttrs, LicenseConventionAttrs
from .multiscales import (
    LayoutObject,
    LayoutObjectR1,
    LayoutObjectR2,
    MultiscalesAttrs,
    MultiscalesAttrsR1,
    MultiscalesAttrsR2,
    MultiscalesConventionAttrs,
    MultiscalesConventionAttrsR1,
    MultiscalesConventionAttrsR2,
    Transform,
    TransformR1,
    TransformR2,
)
from .spatial import (
    SpatialAttrs,
    SpatialAttrsR1,
    SpatialAttrsR2,
    SpatialAttrsR3,
    SpatialConventionAttrs,
    SpatialConventionAttrsR1,
    SpatialConventionAttrsR2,
    SpatialConventionAttrsR3,
)
from .uom import UCUM, UomAttrs, UomConventionAttrs

ConventionName = Literal["geo-proj", "spatial", "multiscales", "license", "uom"]


class _ConventionModule(Protocol):
    UUID: str
    CONVENTION_KEYS: set[str]
    validate: typing.Callable[..., object]
    insert: typing.Callable[..., JsonDict]
    extract: typing.Callable[..., tuple[JsonDict, object]]
    detect: typing.Callable[[JsonDict], str | None]


class _RevisionedConventionModule(_ConventionModule, Protocol):
    _resolve_read_revision: typing.Callable[[JsonDict, str | None], str]


_REGISTRY: Final[dict[ConventionName, _ConventionModule]] = {
    "geo-proj": cast("_ConventionModule", proj),
    "spatial": cast("_ConventionModule", spatial),
    "multiscales": cast("_ConventionModule", multiscales),
    "license": cast("_ConventionModule", license_),
    "uom": cast("_ConventionModule", uom),
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
        "zarr_conventions": NotRequired[
            list[ConventionMetadataObject] | tuple[ConventionMetadataObject, ...]
        ],
        # geo-proj
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[JsonDict],
        # spatial
        "spatial:dimensions": NotRequired[list[str] | tuple[str, ...]],
        "spatial:bbox": NotRequired[list[float] | tuple[float, ...]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float] | tuple[float, ...]],
        "spatial:shape": NotRequired[list[int] | tuple[int, ...]],
        "spatial:registration": NotRequired[str],
        # multiscales
        "multiscales": NotRequired[MultiscalesAttrs],
        # license
        "license": NotRequired[LicenseAttrs],
        # uom
        "uom": NotRequired[UomAttrs],
    },
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
    if revisions and name in revisions and hasattr(mod, "_REVISIONS"):
        return {"revision": revisions[name]}
    return {}


def _read_rev_kwargs(
    mod: _ConventionModule,
    revisions: dict[ConventionName, str] | None,
    name: ConventionName,
    attrs: JsonDict,
) -> dict[str, str]:
    """Resolve the revision for a READ over *attrs* and return it as kwargs.

    Like :func:`_rev_kwargs`, but when no explicit override is given and the
    module supports revisions, the revision is detected ONCE from *attrs* and
    pinned. This must be threaded to *both* ``extract`` and ``validate`` so a
    document detected as (say) r1 is not re-detected as LATEST after ``extract``
    has stripped its ``zarr_conventions`` entry.
    """
    if not hasattr(mod, "_REVISIONS"):
        return {}
    if revisions and name in revisions:
        return {"revision": revisions[name]}
    # The aggregate layer is a privileged consumer of a revisioned convention's
    # read-revision resolver; it is internal to the package, not third-party.
    revisioned = cast("_RevisionedConventionModule", mod)
    return {
        "revision": revisioned._resolve_read_revision(attrs, None)  # pylint: disable=protected-access
    }


def _detect_conventions(attrs: JsonDict) -> frozenset[ConventionName]:
    """Identify which conventions are present by matching UUIDs in zarr_conventions."""
    conventions = cast(
        "typing.Iterable[ConventionMetadataObject]",
        attrs.get("zarr_conventions", ()),
    )
    uuids = {cmo.get("uuid") for cmo in conventions}
    return frozenset(name for name, mod in _REGISTRY.items() if mod.UUID in uuids)


def create_many(
    conventions: dict[ConventionName, JsonDict],
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
    attrs: JsonDict,
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> JsonDict:
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
        mod.validate(dict(cast("JsonDict", extracted)), **rk)
    return attrs


def insert_many(
    attrs: JsonDict,
    conventions: dict[ConventionName, JsonDict],
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
    result = attrs
    for name, data in conventions.items():
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        mod.validate(data, **rk)
        result = mod.insert(result, data, overwrite=overwrite, **rk)
    return result


def extract_many(
    attrs: JsonDict,
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
    remaining = attrs
    extracted: dict[ConventionName, JsonDict] = {}
    for name in conventions:
        mod = _get_module(name)
        rk = _read_rev_kwargs(mod, revisions, name, remaining)
        remaining, data = mod.extract(remaining, **rk)
        extracted[name] = dict(cast("JsonDict", data))
    return remaining, extracted


def validate_all(
    attrs: JsonDict,
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> JsonDict:
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
    attrs: JsonDict,
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


def detect_revisions(
    attrs: JsonDict,
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
    "ConventionAttrs",
    "ConventionMetadataObject",
    "ConventionName",
    "GeoProjAttrs",
    "GeoProjAttrsR1",
    "GeoProjAttrsR2",
    "GeoProjAttrsR3",
    "GeoProjConventionAttrs",
    "GeoProjConventionAttrsR1",
    "GeoProjConventionAttrsR2",
    "GeoProjConventionAttrsR3",
    "LayoutObject",
    "LayoutObjectR1",
    "LayoutObjectR2",
    "LicenseAttrs",
    "LicenseConventionAttrs",
    "MultiConventionAttrs",
    "MultiscalesAttrs",
    "MultiscalesAttrsR1",
    "MultiscalesAttrsR2",
    "MultiscalesConventionAttrs",
    "MultiscalesConventionAttrsR1",
    "MultiscalesConventionAttrsR2",
    "SpatialAttrs",
    "SpatialAttrsR1",
    "SpatialAttrsR2",
    "SpatialAttrsR3",
    "SpatialConventionAttrs",
    "SpatialConventionAttrsR1",
    "SpatialConventionAttrsR2",
    "SpatialConventionAttrsR3",
    "Transform",
    "TransformR1",
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
