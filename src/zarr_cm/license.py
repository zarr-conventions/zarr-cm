"""license convention: https://github.com/clbarnes/zarr-convention-license"""

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
    resolve_revision_label,
    validate_json_object,
)
from zarr_cm._node import NodeContext, node_convention_data, node_type_of, prepare_node

if TYPE_CHECKING:
    from collections.abc import Mapping


class LicenseAttrs(TypedDict, extra_items=JSONValue):
    """License metadata for a Zarr node."""

    spdx: NotRequired[str]
    url: NotRequired[str]
    text: NotRequired[str]
    file: NotRequired[str]
    path: NotRequired[str]


class LicenseConventionAttrs(TypedDict, extra_items=JSONValue):
    """Attributes dict containing license convention metadata."""

    zarr_conventions: Sequence[ConventionMetadataObject]
    license: LicenseAttrs


UUID: Final = "b77365e5-2b0c-4141-b917-c03b7c68e935"
SCHEMA_URL: Final = "https://raw.githubusercontent.com/clbarnes/zarr-convention-license/refs/tags/v1/schema.json"
SPEC_URL: Final = (
    "https://github.com/clbarnes/zarr-convention-license/blob/v1/README.md"
)

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "license",
    "description": "License specifier for Zarr data",
}

CONVENTION_KEYS: Final = {"license"}

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {"v1": SCHEMA_URL}


def detect(attrs: Mapping[str, JSONValue]) -> str | None:
    """Return the revision label this document claims for the license convention.

    License has a single revision (`"v1"`); returns it when present with the
    known schema_url, `None` if present with an unrecognized schema_url, and
    raises `ValueError` if the convention is absent.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "license")


def create(
    *,
    spdx: str | None = None,
    url: str | None = None,
    text: str | None = None,
    file: str | None = None,
    path: str | None = None,
) -> LicenseAttrs:
    """Create a `LicenseAttrs` dict from keyword arguments."""
    result = LicenseAttrs()
    if spdx is not None:
        result["spdx"] = spdx
    if url is not None:
        result["url"] = url
    if text is not None:
        result["text"] = text
    if file is not None:
        result["file"] = file
    if path is not None:
        result["path"] = path
    validate(result)
    return result


def create_convention_attrs(
    *,
    spdx: str | None = None,
    url: str | None = None,
    text: str | None = None,
    file: str | None = None,
    path: str | None = None,
) -> LicenseConventionAttrs:
    """Create a stand-alone attributes dict carrying license and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return LicenseConventionAttrs(
        zarr_conventions=[CMO],
        license=create(spdx=spdx, url=url, text=text, file=file, path=path),
    )


def insert(
    attrs: Mapping[str, JSONValue], data: LicenseAttrs, *, overwrite: bool = False
) -> JSONDict:
    """Insert license convention metadata into an attributes dict."""
    return insert_convention(
        attrs,
        CMO,
        {"license": data},
        overwrite=overwrite,
    )


def extract(
    attrs: Mapping[str, JSONValue],
) -> tuple[JSONDict, LicenseAttrs]:
    """Extract license convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    if not convention_data:
        return remaining, LicenseAttrs()
    if "license" not in convention_data:
        msg = "Extracted convention data does not contain 'license' key"
        raise KeyError(msg)
    value = convention_data["license"]
    if not isinstance(value, dict):
        msg = f"'license' must be a JSON object, got {type(value).__name__}"
        raise TypeError(msg)
    return remaining, cast("LicenseAttrs", value)


def validate(data: Mapping[str, JSONValue]) -> LicenseAttrs:
    """Validate license convention data.

    At least one of `spdx`, `url`, `text`, `file`, or `path`
    must be present.
    """
    keys = ("spdx", "url", "text", "file", "path")
    if not any(k in data for k in keys):
        msg = "At least one of 'spdx', 'url', 'text', 'file', or 'path' must be present"
        raise ValueError(msg)
    for key in keys:
        if key in data and not isinstance(data[key], str):
            msg = f"'{key}' must be a string, got {type(data[key]).__name__}"
            raise TypeError(msg)
    return cast("LicenseAttrs", data)


def _validate_context(context: NodeContext) -> None:
    """Validate license against an already prepared node."""
    data = node_convention_data(context, CMO, CONVENTION_KEYS)
    if "license" not in data:
        msg = "'license' is required"
        raise ValueError(msg)
    value = data["license"]
    if not isinstance(value, dict):
        msg = f"'license' must be a JSON object, got {type(value).__name__}"
        raise TypeError(msg)
    validate(validate_json_object(value))


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[LicenseConventionAttrs]:
    """Validate a v3 group metadata document against the license convention."""
    context = prepare_node(metadata, expected_node_type="group")
    _validate_context(context)
    return cast("GroupMetadata[LicenseConventionAttrs]", context.metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput,
) -> ArrayMetadata[LicenseConventionAttrs]:
    """Validate a v3 array metadata document against the license convention.

    The license convention places no node-type-specific requirements on either
    node type, so this matches `validate_group_metadata()`.
    """
    context = prepare_node(metadata, expected_node_type="array")
    _validate_context(context)
    return cast("ArrayMetadata[LicenseConventionAttrs]", context.metadata)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> Metadata[LicenseConventionAttrs]:
    """Validate a v3 node metadata document against the license convention.

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
