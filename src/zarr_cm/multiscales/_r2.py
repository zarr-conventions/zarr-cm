"""multiscales convention, revision r2 (v0.1).

Snapshot of upstream at commit 9b78efa75fef0fed302d9cf880037c569354d860.
Identical in shape to r1; pins the schema/spec URLs to the v0.1 release.
"""

from __future__ import annotations

import re

# Imported at runtime, not under TYPE_CHECKING: the class-form `TypedDict`s
# below store their annotations as strings (`from __future__ import
# annotations`), and a downstream consumer that resolves them -- pydantic's
# `model_rebuild()`, `typing.get_type_hints()` -- evaluates those strings in
# THIS module's namespace. A `Sequence` visible only to the type checker
# type-checks fine and then raises `NameError` for that consumer.
# See tests/test_pydantic.py::test_every_public_typeddict_rebuilds.
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Never, NotRequired, cast

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping


from zarr_cm._core import (
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
    validate_json_object,
)
from zarr_cm._node import NodeContext, node_convention_data, node_type_of, prepare_node


class Transform(TypedDict, extra_items=JSONValue):
    """Coordinate transformation with scale and translation."""

    scale: NotRequired[Sequence[float]]
    translation: NotRequired[Sequence[float]]


class LayoutObject(TypedDict, extra_items=JSONValue):
    """A single resolution level in a multiscale pyramid."""

    asset: str
    derived_from: NotRequired[str]
    transform: NotRequired[Transform]
    resampling_method: NotRequired[str]


class MultiscalesAttrs(TypedDict, extra_items=JSONValue):
    """Multiscale pyramid layout and metadata."""

    layout: Sequence[LayoutObject]
    resampling_method: NotRequired[str]


class MultiscalesConventionAttrs(TypedDict, extra_items=JSONValue):
    """Attributes dict containing multiscales convention metadata."""

    zarr_conventions: Sequence[ConventionMetadataObject]
    multiscales: MultiscalesAttrs


# UUID identifies the convention *family*, not the revision; it is shared with
# r1. Revisions are distinguished by the SCHEMA_URL below, which is what
# revision detection on read matches against.
#
# Unlike spatial/proj, the multiscales v0.1 schema ENFORCES schema_url as a
# `const` equal to the refs/tags/v0.1 tag URL (its conventionMetadata has no
# escape hatch), so a document we emit must carry that exact tag URL to validate
# against the official schema. We therefore pin to the tag here rather than the
# commit SHA. The snapshot is still taken at commit _COMMIT (vendored under that
# name); _TAG is the published tag at that commit.
UUID: Final = "d35379db-88df-4056-af3a-620245f8e347"
_COMMIT: Final = "9b78efa75fef0fed302d9cf880037c569354d860"
_TAG: Final = "v0.1"
SCHEMA_URL: Final = f"https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/{_TAG}/schema.json"
SPEC_URL: Final = (
    f"https://github.com/zarr-conventions/multiscales/blob/{_TAG}/README.md"
)

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "multiscales",
    "description": "Multiscale layout of zarr datasets",
}

CONVENTION_KEYS: Final = {"multiscales"}
_PATH_PATTERN: Final = re.compile(r"^(?!/)(?!.*(\.\.))([^/]+(/[^/]+)*)$")


def create(
    *,
    layout: tuple[LayoutObject, ...],
    resampling_method: str | None = None,
) -> MultiscalesAttrs:
    """Create a `MultiscalesAttrs` dict from keyword arguments."""
    result = MultiscalesAttrs(layout=layout)
    if resampling_method is not None:
        result["resampling_method"] = resampling_method
    validate(result)
    return result


def create_convention_attrs(
    *,
    layout: tuple[LayoutObject, ...],
    resampling_method: str | None = None,
) -> MultiscalesConventionAttrs:
    """Create a stand-alone attributes dict carrying multiscales and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return MultiscalesConventionAttrs(
        zarr_conventions=[CMO],
        multiscales=create(layout=layout, resampling_method=resampling_method),
    )


def insert(
    attrs: Mapping[str, JSONValue], data: MultiscalesAttrs, *, overwrite: bool = False
) -> JSONDict:
    """Insert multiscales convention metadata into an attributes dict."""
    return insert_convention(
        attrs,
        CMO,
        {"multiscales": data},
        overwrite=overwrite,
    )


def extract(
    attrs: Mapping[str, JSONValue],
) -> tuple[JSONDict, MultiscalesAttrs]:
    """Extract multiscales convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    if not convention_data:
        return remaining, MultiscalesAttrs(layout=[])
    if "multiscales" not in convention_data:
        msg = "Extracted convention data does not contain 'multiscales' key"
        raise KeyError(msg)
    value = convention_data["multiscales"]
    if not isinstance(value, dict):
        msg = f"'multiscales' must be a JSON object, got {type(value).__name__}"
        raise TypeError(msg)
    return remaining, cast("MultiscalesAttrs", value)


def validate(data: Mapping[str, JSONValue]) -> MultiscalesAttrs:
    """Validate multiscales convention data.

    `layout` must have at least one item, and each layout entry
    that has `derived_from` must also have `transform`.
    """
    if "layout" not in data:
        msg = "'layout' is required"
        raise ValueError(msg)

    layout = data["layout"]
    if not isinstance(layout, (list, tuple)):
        msg = "'layout' must be an array"
        raise TypeError(msg)

    if len(layout) < 1:
        msg = "'layout' must have at least one item"
        raise ValueError(msg)

    for i, entry in enumerate(layout):
        if not isinstance(entry, dict):
            msg = f"layout[{i}] must be an object"
            raise TypeError(msg)
        entry_object = validate_json_object(entry)
        asset = entry_object.get("asset")
        if not isinstance(asset, str) or not _PATH_PATTERN.match(asset):
            msg = f"layout[{i}].asset must be a valid relative path"
            raise ValueError(msg)
        if "derived_from" in entry_object:
            derived_from = entry_object["derived_from"]
            if not isinstance(derived_from, str) or not _PATH_PATTERN.match(
                derived_from
            ):
                msg = f"layout[{i}].derived_from must be a valid relative path"
                raise ValueError(msg)
        if "derived_from" in entry_object and "transform" not in entry_object:
            msg = f"layout[{i}] has 'derived_from' but is missing 'transform'"
            raise ValueError(msg)
        if "transform" in entry_object:
            transform_value = entry_object["transform"]
            if not isinstance(transform_value, dict):
                msg = f"layout[{i}].transform must be an object"
                raise TypeError(msg)
            transform = validate_json_object(transform_value)
            for key in ("scale", "translation"):
                if key not in transform:
                    continue
                values = transform[key]
                if not isinstance(values, (list, tuple)):
                    msg = f"layout[{i}].transform.{key} must be an array"
                    raise TypeError(msg)
                if any(
                    isinstance(value, bool) or not isinstance(value, int | float)
                    for value in values
                ):
                    msg = f"layout[{i}].transform.{key} items must be numbers"
                    raise TypeError(msg)
        if "resampling_method" in entry_object and not isinstance(
            entry_object["resampling_method"], str
        ):
            msg = f"layout[{i}].resampling_method must be a string"
            raise TypeError(msg)
    if "resampling_method" in data and not isinstance(data["resampling_method"], str):
        msg = "'resampling_method' must be a string"
        raise TypeError(msg)
    return cast("MultiscalesAttrs", data)


def _validate_context(context: NodeContext) -> None:
    """Validate multiscales against an already prepared node."""
    raw = node_convention_data(context, CMO, CONVENTION_KEYS)
    if context.node_type == "array":
        msg = "the 'multiscales' convention does not apply to array nodes"
        raise ValueError(msg)
    if "multiscales" not in raw:
        msg = "'multiscales' is required"
        raise ValueError(msg)
    value = raw["multiscales"]
    if not isinstance(value, dict):
        msg = f"'multiscales' must be a JSON object, got {type(value).__name__}"
        raise TypeError(msg)
    validate(validate_json_object(value))


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[MultiscalesConventionAttrs]:
    """Validate a v3 group metadata document against multiscales (r2)."""
    context = prepare_node(metadata, expected_node_type="group")
    _validate_context(context)
    return cast("GroupMetadata[MultiscalesConventionAttrs]", context.metadata)


def validate_array_metadata(metadata: ArrayMetadataInput) -> Never:
    """Reject a v3 array metadata document: multiscales is a group-only convention.

    The schema restricts `node_type` to `"group"`, so there is no valid
    array form of this convention and this always raises.
    """
    _validate_context(prepare_node(metadata, expected_node_type="array"))
    msg = "multiscales array validation unexpectedly returned"
    raise AssertionError(msg)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> Metadata[MultiscalesConventionAttrs]:
    """Validate a v3 node metadata document against multiscales (r2).

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`. Only the
    group arm can return: multiscales has no valid array form.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
