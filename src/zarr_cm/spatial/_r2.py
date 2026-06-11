"""spatial convention, revision r2 (strict 2D).

Snapshot of upstream main at commit f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.
Narrows every dimension-bearing key to a fixed 2D length and requires shape
items to be positive.
"""

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

# UUID identifies the convention *family*, not the revision; it is shared with
# r1. Revisions are distinguished by the commit-pinned SCHEMA_URL below, which
# is what revision detection on read matches against.
UUID: Final = "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4"
_COMMIT: Final = "f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a"
SCHEMA_URL: Final = (
    f"https://raw.githubusercontent.com/zarr-conventions/spatial/{_COMMIT}/schema.json"
)
SPEC_URL: Final = (
    f"https://github.com/zarr-conventions/spatial/blob/{_COMMIT}/README.md"
)

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

# r2: every dimension-bearing key is a fixed 2D length.
_VALID_LENGTHS: Final[dict[str, int]] = {
    "spatial:dimensions": 2,
    "spatial:bbox": 4,
    "spatial:transform": 6,
    "spatial:shape": 2,
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
    """Create a ``SpatialAttrs`` dict (r2, strict 2D) from keyword arguments."""
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
    """Insert spatial (r2) convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, dict(data), overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], SpatialAttrs]:
    """Extract spatial (r2) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, SpatialAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> SpatialAttrs:
    """Validate spatial (r2) convention data: strict 2D, positive shape items."""
    if "spatial:dimensions" not in data:
        msg = "'spatial:dimensions' is required"
        raise ValueError(msg)

    for key, expected in _VALID_LENGTHS.items():
        if key in data:
            n = len(data[key])
            if n != expected:
                msg = f"'{key}' must have exactly {expected} items, got {n}"
                raise ValueError(msg)

    if "spatial:shape" in data and any(v < 1 for v in data["spatial:shape"]):
        msg = "'spatial:shape' items must be positive (>= 1)"
        raise ValueError(msg)

    if (
        "spatial:registration" in data
        and data["spatial:registration"] not in _VALID_REGISTRATIONS
    ):
        msg = f"'spatial:registration' must be one of {_VALID_REGISTRATIONS}, got {data['spatial:registration']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
