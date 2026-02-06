"""
Copyright (c) 2026 Davis Bennett. All rights reserved.

zarr-cm: Python implementation of Zarr Conventions Metadata
"""

from __future__ import annotations

import typing
from typing import Any, Final, Literal, NotRequired, TypedDict

if typing.TYPE_CHECKING:
    import types
    from collections.abc import Iterable

from . import geo_proj, license, multiscales, spatial, uom
from ._core import (
    ConventionAttrs,
    ConventionMetadataObject,
    validate_convention_metadata_object,
)
from ._version import version as __version__
from .geo_proj import GeoProjAttrs, GeoProjConventionAttrs
from .license import LicenseAttrs, LicenseConventionAttrs
from .multiscales import (
    LayoutObject,
    MultiscalesAttrs,
    MultiscalesConventionAttrs,
    Transform,
)
from .spatial import SpatialAttrs, SpatialConventionAttrs
from .uom import UCUM, UomAttrs, UomConventionAttrs

ConventionName = Literal["geo-proj", "spatial", "multiscales", "license", "uom"]

_REGISTRY: Final[dict[ConventionName, types.ModuleType]] = {
    "geo-proj": geo_proj,
    "spatial": spatial,
    "multiscales": multiscales,
    "license": license,
    "uom": uom,
}

CONVENTION_NAMES: Final = frozenset(_REGISTRY)

ALL_CONVENTION_KEYS: Final = frozenset(
    geo_proj.CONVENTION_KEYS
    | spatial.CONVENTION_KEYS
    | multiscales.CONVENTION_KEYS
    | license.CONVENTION_KEYS
    | uom.CONVENTION_KEYS
)

MultiConventionAttrs = TypedDict(
    "MultiConventionAttrs",
    {
        "zarr_conventions": NotRequired[list[ConventionMetadataObject]],
        # geo-proj
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[dict[str, Any]],
        # spatial
        "spatial:dimensions": NotRequired[list[str]],
        "spatial:bbox": NotRequired[list[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float]],
        "spatial:shape": NotRequired[list[int]],
        "spatial:registration": NotRequired[str],
        # multiscales
        "multiscales": NotRequired[MultiscalesAttrs],
        # license
        "license": NotRequired[LicenseAttrs],
        # uom
        "uom": NotRequired[UomAttrs],
    },
)


def _get_module(name: ConventionName) -> types.ModuleType:
    """Look up convention module by display name, raise ValueError if unknown."""
    try:
        return _REGISTRY[name]
    except KeyError:
        msg = f"Unknown convention {name!r}. Valid names: {sorted(CONVENTION_NAMES)}"
        raise ValueError(msg) from None


def _detect_conventions(attrs: dict[str, Any]) -> frozenset[ConventionName]:
    """Identify which conventions are present by matching UUIDs in zarr_conventions."""
    uuids = {cmo.get("uuid") for cmo in attrs.get("zarr_conventions", [])}
    return frozenset(name for name, mod in _REGISTRY.items() if mod.UUID in uuids)


def create_many(
    conventions: dict[ConventionName, dict[str, Any]],
) -> dict[str, Any]:
    """Create and insert multiple conventions into a single attributes dict.

    Parameters
    ----------
    conventions
        Mapping from convention display name (e.g. ``"geo-proj"``) to
        already-formed convention data (the ``AttrsT`` value).

    Returns
    -------
    dict[str, Any]
        A new attributes dict containing all convention data and a
        combined ``zarr_conventions`` array.
    """
    result: dict[str, Any] = {}
    for name, data in conventions.items():
        mod = _get_module(name)
        mod.validate(data)
        result = mod.insert(result, data, overwrite=True)
    return result


def validate_many(
    attrs: dict[str, Any],
    conventions: Iterable[ConventionName],
) -> dict[str, Any]:
    """Validate multiple conventions within an attributes dict.

    Parameters
    ----------
    attrs
        The attributes dict to validate.
    conventions
        Convention names to validate.

    Returns
    -------
    dict[str, Any]
        The input *attrs* (pass-through on success).
    """
    for name in conventions:
        mod = _get_module(name)
        _, extracted = mod.extract(attrs)
        mod.validate(dict(extracted))
    return attrs


def insert_many(
    attrs: dict[str, Any],
    conventions: dict[ConventionName, dict[str, Any]],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
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

    Returns
    -------
    dict[str, Any]
        A new attributes dict with all convention data merged in.
    """
    result = attrs
    for name, data in conventions.items():
        mod = _get_module(name)
        mod.validate(data)
        result = mod.insert(result, data, overwrite=overwrite)
    return result


def extract_many(
    attrs: dict[str, Any],
    conventions: Iterable[ConventionName],
) -> tuple[dict[str, Any], dict[ConventionName, dict[str, Any]]]:
    """Extract multiple conventions from an attributes dict.

    Parameters
    ----------
    attrs
        The attributes dict to extract from.
    conventions
        Convention names to extract.

    Returns
    -------
    tuple[dict[str, Any], dict[str, dict[str, Any]]]
        ``(remaining_attrs, extracted)`` where *extracted* maps
        convention names to their convention data dicts.
    """
    remaining = attrs
    extracted: dict[ConventionName, dict[str, Any]] = {}
    for name in conventions:
        mod = _get_module(name)
        remaining, data = mod.extract(remaining)
        extracted[name] = dict(data)
    return remaining, extracted


def validate_all(
    attrs: dict[str, Any],
) -> dict[str, Any]:
    """Validate all detected conventions within an attributes dict.

    Detects which conventions are present by matching UUIDs in
    ``zarr_conventions``, then validates each one.

    Parameters
    ----------
    attrs
        The attributes dict to validate.

    Returns
    -------
    dict[str, Any]
        The input *attrs* (pass-through on success).
    """
    return validate_many(attrs, _detect_conventions(attrs))


def extract_all(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], dict[ConventionName, dict[str, Any]]]:
    """Extract all detected conventions from an attributes dict.

    Detects which conventions are present by matching UUIDs in
    ``zarr_conventions``, then extracts each one.

    Parameters
    ----------
    attrs
        The attributes dict to extract from.

    Returns
    -------
    tuple[dict[str, Any], dict[str, dict[str, Any]]]
        ``(remaining_attrs, extracted)`` where *extracted* maps
        convention names to their convention data dicts.
    """
    return extract_many(attrs, _detect_conventions(attrs))


__all__ = [
    "ALL_CONVENTION_KEYS",
    "CONVENTION_NAMES",
    "UCUM",
    "ConventionAttrs",
    "ConventionMetadataObject",
    "ConventionName",
    "GeoProjAttrs",
    "GeoProjConventionAttrs",
    "LayoutObject",
    "LicenseAttrs",
    "LicenseConventionAttrs",
    "MultiConventionAttrs",
    "MultiscalesAttrs",
    "MultiscalesConventionAttrs",
    "SpatialAttrs",
    "SpatialConventionAttrs",
    "Transform",
    "UomAttrs",
    "UomConventionAttrs",
    "__version__",
    "create_many",
    "extract_all",
    "extract_many",
    "insert_many",
    "validate_all",
    "validate_convention_metadata_object",
    "validate_many",
]
