"""spatial convention, revision r2 (strict 2D).

Snapshot of upstream main at commit f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.
Narrows every dimension-bearing key to a fixed 2D length and requires shape
items to be positive.
"""

from __future__ import annotations

from typing import Final, NotRequired, TypedDict, cast

from zarr_cm._core import (
    ConventionMetadataObject,
    JsonDict,
    extract_convention,
    insert_convention,
)

SpatialAttrs = TypedDict(
    "SpatialAttrs",
    {
        "spatial:dimensions": list[str] | tuple[str, ...],
        "spatial:bbox": NotRequired[list[float] | tuple[float, ...]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float] | tuple[float, ...]],
        "spatial:shape": NotRequired[list[int] | tuple[int, ...]],
        "spatial:registration": NotRequired[str],
    },
)

SpatialConventionAttrs = TypedDict(
    "SpatialConventionAttrs",
    {
        "zarr_conventions": tuple[ConventionMetadataObject, ...],
        "spatial:dimensions": list[str] | tuple[str, ...],
        "spatial:bbox": NotRequired[list[float] | tuple[float, ...]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float] | tuple[float, ...]],
        "spatial:shape": NotRequired[list[int] | tuple[int, ...]],
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
    dimensions: list[str] | tuple[str, ...],
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
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
    validate(dict(cast("JsonDict", result)))
    return result


def insert(attrs: JsonDict, data: SpatialAttrs, *, overwrite: bool = False) -> JsonDict:
    """Insert spatial (r2) convention metadata into an attributes dict."""
    return insert_convention(
        attrs, CMO, dict(cast("JsonDict", data)), overwrite=overwrite
    )


def extract(
    attrs: JsonDict,
) -> tuple[JsonDict, SpatialAttrs]:
    """Extract spatial (r2) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, SpatialAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: JsonDict) -> SpatialAttrs:
    """Validate spatial (r2) convention data: strict 2D, positive shape items."""
    if "spatial:dimensions" not in data:
        msg = "'spatial:dimensions' is required"
        raise ValueError(msg)

    for key, expected in _VALID_LENGTHS.items():
        if key in data:
            value = data[key]
            if not isinstance(value, (list, tuple)):
                msg = f"'{key}' must be an array with exactly {expected} items, got {type(value).__name__}"
                raise ValueError(msg)
            n = len(value)
            if n != expected:
                msg = f"'{key}' must have exactly {expected} items, got {n}"
                raise ValueError(msg)

    if "spatial:shape" in data:
        shape = data["spatial:shape"]
        if not isinstance(shape, (list, tuple)):
            msg = "'spatial:shape' must be an array"
            raise TypeError(msg)
        for v in shape:
            if not isinstance(v, int):
                msg = "'spatial:shape' items must be integers"
                raise TypeError(msg)
            if v < 1:
                msg = "'spatial:shape' items must be positive (>= 1)"
                raise ValueError(msg)

    if (
        "spatial:registration" in data
        and data["spatial:registration"] not in _VALID_REGISTRATIONS
    ):
        msg = f"'spatial:registration' must be one of {_VALID_REGISTRATIONS}, got {data['spatial:registration']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
