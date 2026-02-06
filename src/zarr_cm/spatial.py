"""spatial convention: https://github.com/zarr-conventions/spatial"""

from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)

SpatialAttrs = TypedDict(
    "SpatialAttrs",
    {
        "spatial:dimensions": list[str],
        "spatial:bbox": NotRequired[list[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float]],
        "spatial:shape": NotRequired[list[int]],
        "spatial:registration": NotRequired[str],
    },
)

SpatialConventionAttrs = TypedDict(
    "SpatialConventionAttrs",
    {
        "zarr_conventions": list[ConventionMetadataObject],
        "spatial:dimensions": list[str],
        "spatial:bbox": NotRequired[list[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float]],
        "spatial:shape": NotRequired[list[int]],
        "spatial:registration": NotRequired[str],
    },
)

UUID: Final = "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4"
SCHEMA_URL: Final = "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json"
SPEC_URL: Final = "https://github.com/zarr-conventions/spatial/blob/v1/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "spatial:",
    "description": "Spatial coordinate information",
}

CONVENTION_KEYS: Final = {
    "spatial:dimensions",
    "spatial:bbox",
    "spatial:transform_type",
    "spatial:transform",
    "spatial:shape",
    "spatial:registration",
}


_VALID_LENGTHS: Final[dict[str, tuple[int, ...]]] = {
    "spatial:dimensions": (2, 3),
    "spatial:bbox": (4, 6),
    "spatial:transform": (6, 9),
    "spatial:shape": (2, 3),
}

_VALID_REGISTRATIONS: Final = ("node", "pixel")


def create(
    *,
    dimensions: list[str],
    bbox: list[float] | None = None,
    transform_type: str | None = None,
    transform: list[float] | None = None,
    shape: list[int] | None = None,
    registration: str | None = None,
) -> SpatialAttrs:
    """Create a ``SpatialAttrs`` dict from keyword arguments."""
    result = SpatialAttrs({"spatial:dimensions": dimensions})
    if bbox is not None:
        result["spatial:bbox"] = bbox
    if transform_type is not None:
        result["spatial:transform_type"] = transform_type
    if transform is not None:
        result["spatial:transform"] = transform
    if shape is not None:
        result["spatial:shape"] = shape
    if registration is not None:
        result["spatial:registration"] = registration
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: SpatialAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert spatial convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, dict(data), overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], SpatialAttrs]:
    """Extract spatial convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, SpatialAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> SpatialAttrs:
    """Validate spatial convention data."""
    if "spatial:dimensions" not in data:
        msg = "'spatial:dimensions' is required"
        raise ValueError(msg)

    for key, valid in _VALID_LENGTHS.items():
        if key in data:
            n = len(data[key])
            if n not in valid:
                msg = f"'{key}' must have {' or '.join(str(v) for v in valid)} items, got {n}"
                raise ValueError(msg)

    if "spatial:registration" in data and data["spatial:registration"] not in _VALID_REGISTRATIONS:
        msg = f"'spatial:registration' must be one of {_VALID_REGISTRATIONS}, got {data['spatial:registration']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
