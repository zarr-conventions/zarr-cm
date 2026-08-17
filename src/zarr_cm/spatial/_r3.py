"""spatial convention, revision r3 (strict 2D, v0.1).

Snapshot of upstream at commit 54d81b7ced0376e63ee10f34db31db7d08dcc28d.
Narrows every dimension-bearing key to a fixed 2D length and requires shape
items to be positive. `spatial:dimensions` is optional here: upstream makes
it required only when `node_type` is `"array"`, and these functions see
attributes without the surrounding node, so a group carrying only
`spatial:bbox` is valid.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, NotRequired, cast

from typing_extensions import TypedDict

from zarr_cm._core import (
    ArrayMetadata,
    ArrayMetadataInput,
    ConventionMetadataObject,
    GroupMetadata,
    GroupMetadataInput,
    JSONDict,
    JSONValue,
    Metadata,
    NodeMetadataInput,
    extract_convention,
    insert_convention,
)
from zarr_cm._node import NodeContext, node_convention_data, node_type_of, prepare_node

if TYPE_CHECKING:
    from collections.abc import Mapping


SpatialAttrs = TypedDict(
    "SpatialAttrs",
    {
        "spatial:dimensions": NotRequired[Sequence[str]],
        "spatial:bbox": NotRequired[Sequence[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[Sequence[float]],
        "spatial:shape": NotRequired[Sequence[int]],
        "spatial:registration": NotRequired[str],
    },
    extra_items=JSONValue,
)

SpatialConventionAttrs = TypedDict(
    "SpatialConventionAttrs",
    {
        "zarr_conventions": Sequence[ConventionMetadataObject],
        "spatial:dimensions": NotRequired[Sequence[str]],
        "spatial:bbox": NotRequired[Sequence[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[Sequence[float]],
        "spatial:shape": NotRequired[Sequence[int]],
        "spatial:registration": NotRequired[str],
    },
    extra_items=JSONValue,
)

# UUID identifies the convention *family*, not the revision; it is shared with
# r1. Revisions are distinguished by the commit-pinned SCHEMA_URL below, which
# is what revision detection on read matches against.
UUID: Final = "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4"
_COMMIT: Final = "54d81b7ced0376e63ee10f34db31db7d08dcc28d"
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

# r3: every dimension-bearing key is a fixed 2D length.
_VALID_LENGTHS: Final[dict[str, int]] = {
    "spatial:dimensions": 2,
    "spatial:bbox": 4,
    "spatial:transform": 6,
    "spatial:shape": 2,
}

_VALID_REGISTRATIONS: Final = ("node", "pixel")


def create(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
) -> SpatialAttrs:
    """Create a `SpatialAttrs` dict (r3, strict 2D) from keyword arguments."""
    result = SpatialAttrs()
    if dimensions is not None:
        result["spatial:dimensions"] = dimensions
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
    validate(result)
    return result


def create_convention_attrs(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
) -> SpatialConventionAttrs:
    """Create a stand-alone attributes dict carrying spatial (r3) and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return cast(
        "SpatialConventionAttrs",
        {
            "zarr_conventions": [CMO],
            **create(
                dimensions=dimensions,
                bbox=bbox,
                transform_type=transform_type,
                transform=transform,
                shape=shape,
                registration=registration,
            ),
        },
    )


def insert(
    attrs: Mapping[str, JSONValue], data: SpatialAttrs, *, overwrite: bool = False
) -> JSONDict:
    """Insert spatial (r3) convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, data, overwrite=overwrite)


def extract(
    attrs: Mapping[str, JSONValue],
) -> tuple[JSONDict, SpatialAttrs]:
    """Extract spatial (r3) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, cast("SpatialAttrs", convention_data)


def validate(data: Mapping[str, JSONValue]) -> SpatialAttrs:
    """Validate spatial (r3) convention data: strict 2D, positive shape items.

    `spatial:dimensions` is not required: upstream requires it only for
    `node_type == "array"`, which is not visible from *data* alone.
    """
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

    if "spatial:dimensions" in data:
        dimensions = data["spatial:dimensions"]
        if not isinstance(dimensions, (list, tuple)):
            msg = "'spatial:dimensions' must be an array"
            raise TypeError(msg)
        for value in dimensions:
            if not isinstance(value, str):
                msg = "'spatial:dimensions' items must be strings"
                raise TypeError(msg)

    for key in ("spatial:bbox", "spatial:transform"):
        if key in data:
            values = data[key]
            if not isinstance(values, (list, tuple)):
                msg = f"'{key}' must be an array"
                raise TypeError(msg)
            for value in values:
                if isinstance(value, bool) or not isinstance(value, int | float):
                    msg = f"'{key}' items must be numbers"
                    raise TypeError(msg)

    if "spatial:transform_type" in data and not isinstance(
        data["spatial:transform_type"], str
    ):
        msg = "'spatial:transform_type' must be a string"
        raise TypeError(msg)

    if "spatial:shape" in data:
        shape = data["spatial:shape"]
        if not isinstance(shape, (list, tuple)):
            msg = "'spatial:shape' must be an array"
            raise TypeError(msg)
        for v in shape:
            if isinstance(v, bool) or not isinstance(v, int):
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
    return cast("SpatialAttrs", data)


def _validate_context(context: NodeContext) -> SpatialAttrs:
    """Validate spatial against an already prepared node."""
    data = validate(node_convention_data(context, CMO, CONVENTION_KEYS))
    if context.node_type == "array" and "spatial:dimensions" not in data:
        msg = "'spatial:dimensions' is required on array nodes"
        raise ValueError(msg)
    return data


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[SpatialConventionAttrs]:
    """Validate a v3 group metadata document against spatial (r3).

    `spatial:dimensions` is not required here: upstream marks it required only
    when `node_type` is `"array"`, so a group may carry the other spatial:
    keys -- a union footprint, say -- on their own.
    """
    context = prepare_node(metadata, expected_node_type="group")
    _validate_context(context)
    return cast("GroupMetadata[SpatialConventionAttrs]", context.metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput,
) -> ArrayMetadata[SpatialConventionAttrs]:
    """Validate a v3 array metadata document against spatial (r3).

    Arrays must carry `spatial:dimensions`; groups need not.
    """
    context = prepare_node(metadata, expected_node_type="array")
    _validate_context(context)
    return cast("ArrayMetadata[SpatialConventionAttrs]", context.metadata)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> Metadata[SpatialConventionAttrs]:
    """Validate a v3 node metadata document against spatial (r3).

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
