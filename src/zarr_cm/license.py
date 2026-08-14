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
    NodeMetadataInput,
    NodeType,
    convention_attributes,
    extract_convention,
    insert_convention,
    node_type_of,
    resolve_revision_label,
)

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

    License has a single revision (``"v1"``); returns it when present with the
    known schema_url, ``None`` if present with an unrecognized schema_url, and
    raises ``ValueError`` if the convention is absent.
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
    """Create a ``LicenseAttrs`` dict from keyword arguments."""
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
    return remaining, LicenseAttrs(**convention_data["license"])  # type: ignore[typeddict-item]


def validate(data: Mapping[str, JSONValue]) -> LicenseAttrs:
    """Validate license convention data.

    At least one of ``spdx``, ``url``, ``text``, ``file``, or ``path``
    must be present.
    """
    if not any(k in data for k in ("spdx", "url", "text", "file", "path")):
        msg = "At least one of 'spdx', 'url', 'text', 'file', or 'path' must be present"
        raise ValueError(msg)
    return data  # type: ignore[return-value]


def _convention_data(
    metadata: Mapping[str, object], node_type: NodeType
) -> LicenseAttrs:
    """Pull this document's license data out and run the attribute-level rules."""
    attributes = convention_attributes(
        metadata, convention="license", uuid=UUID, expected_node_type=node_type
    )
    _, data = extract(attributes)
    return validate(data)


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[LicenseConventionAttrs]:
    """Validate a v3 group metadata document against the license convention."""
    _convention_data(metadata, "group")
    return cast("GroupMetadata[LicenseConventionAttrs]", metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput,
) -> ArrayMetadata[LicenseConventionAttrs]:
    """Validate a v3 array metadata document against the license convention.

    The license convention places no node-type-specific requirements on either
    node type, so this matches `validate_group_metadata()`.
    """
    _convention_data(metadata, "array")
    return cast("ArrayMetadata[LicenseConventionAttrs]", metadata)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> ArrayMetadata[LicenseConventionAttrs] | GroupMetadata[LicenseConventionAttrs]:
    """Validate a v3 node metadata document against the license convention.

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
