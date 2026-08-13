"""uom convention: https://github.com/clbarnes/zarr-convention-uom"""

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
    JsonDict,
    JsonValue,
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


class UCUM(TypedDict, extra_items=JsonValue):
    """Unified Code for Units of Measurement information."""

    unit: NotRequired[str]
    version: NotRequired[str]


class UomAttrs(TypedDict, extra_items=JsonValue):
    """Unit of measurement metadata for a Zarr array."""

    ucum: UCUM
    description: NotRequired[str]


class UomConventionAttrs(TypedDict, extra_items=JsonValue):
    """Attributes dict containing uom convention metadata."""

    zarr_conventions: Sequence[ConventionMetadataObject]
    uom: UomAttrs


UUID: Final = "3bbe438d-df37-49fe-8e2b-739296d46dfb"
SCHEMA_URL: Final = "https://raw.githubusercontent.com/clbarnes/zarr-convention-uom/refs/tags/v1/schema.json"
SPEC_URL: Final = "https://github.com/clbarnes/zarr-convention-uom/blob/v1/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "uom",
    "description": "Units of measurement for Zarr arrays",
}

CONVENTION_KEYS: Final = {"uom"}

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {"v1": SCHEMA_URL}


def detect(attrs: Mapping[str, JsonValue]) -> str | None:
    """Return the revision label this document claims for the uom convention.

    Uom has a single revision (``"v1"``); returns it when present with the
    known schema_url, ``None`` if present with an unrecognized schema_url, and
    raises ``ValueError`` if the convention is absent.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "uom")


def create(
    *,
    ucum: UCUM,
    description: str | None = None,
) -> UomAttrs:
    """Create a ``UomAttrs`` dict from keyword arguments."""
    result = UomAttrs(ucum=ucum)
    if description is not None:
        result["description"] = description
    validate(result)
    return result


def create_convention_attrs(
    *,
    ucum: UCUM,
    description: str | None = None,
) -> UomConventionAttrs:
    """Create a stand-alone attributes dict carrying uom and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return UomConventionAttrs(
        zarr_conventions=[CMO],
        uom=create(ucum=ucum, description=description),
    )


def insert(
    attrs: Mapping[str, JsonValue], data: UomAttrs, *, overwrite: bool = False
) -> JsonDict:
    """Insert uom convention metadata into an attributes dict."""
    return insert_convention(
        attrs,
        CMO,
        {"uom": data},
        overwrite=overwrite,
    )


def extract(
    attrs: Mapping[str, JsonValue],
) -> tuple[JsonDict, UomAttrs]:
    """Extract uom convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    if not convention_data:
        return remaining, UomAttrs(ucum={})
    if "uom" not in convention_data:
        msg = "Extracted convention data does not contain 'uom' key"
        raise KeyError(msg)
    return remaining, UomAttrs(**convention_data["uom"])  # type: ignore[typeddict-item]


def validate(data: Mapping[str, JsonValue]) -> UomAttrs:
    """Validate uom convention data.

    ``ucum`` must be present.
    """
    if "ucum" not in data:
        msg = "'ucum' is required"
        raise ValueError(msg)
    return data  # type: ignore[return-value]


def _convention_data(metadata: Mapping[str, object], node_type: NodeType) -> UomAttrs:
    """Pull this document's uom data out and run the attribute-level rules."""
    attributes = convention_attributes(
        metadata, convention="uom", uuid=UUID, expected_node_type=node_type
    )
    _, data = extract(attributes)
    return validate(data)


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[UomConventionAttrs]:
    """Validate a v3 group metadata document against the uom convention."""
    _convention_data(metadata, "group")
    return cast("GroupMetadata[UomConventionAttrs]", metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput,
) -> ArrayMetadata[UomConventionAttrs]:
    """Validate a v3 array metadata document against the uom convention.

    The uom convention places no node-type-specific requirements on either
    node type, so this matches `validate_group_metadata()`.
    """
    _convention_data(metadata, "array")
    return cast("ArrayMetadata[UomConventionAttrs]", metadata)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> ArrayMetadata[UomConventionAttrs] | GroupMetadata[UomConventionAttrs]:
    """Validate a v3 node metadata document against the uom convention.

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
