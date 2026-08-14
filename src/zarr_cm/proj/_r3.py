"""proj convention, revision r3 (v0.1).

Snapshot of upstream at commit 5ca5b2f92e5c7245f957d9128b289ee535f0720d (tag
v0.1). Relaxes the ``proj:code`` pattern (now ``^[^:]+:[^:]+$``) and the CRS
rule (now at least one of code/wkt2/projjson, i.e. anyOf rather than oneOf) to
match upstream v0.1.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, NotRequired, cast

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping


from zarr_cm._core import (
    ArrayMetadata,
    ArrayMetadataInput,
    ConventionMetadataObject,
    GroupMetadata,
    GroupMetadataInput,
    JSONDict,
    JSONValue,
    NodeMetadataInput,
    convention_attributes,
    extract_convention,
    insert_convention,
    node_type_of,
)

GeoProjAttrs = TypedDict(
    "GeoProjAttrs",
    {
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[JSONDict],
    },
    extra_items=JSONValue,
)

GeoProjConventionAttrs = TypedDict(
    "GeoProjConventionAttrs",
    {
        "zarr_conventions": Sequence[ConventionMetadataObject],
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[JSONDict],
    },
    extra_items=JSONValue,
)

# UUID identifies the convention *family*, not the revision; it is shared with
# r1. Revisions are distinguished by the commit-pinned SCHEMA_URL below, which
# is what revision detection on read matches against.
UUID: Final = "f17cb550-5864-4468-aeb7-f3180cfb622f"
_COMMIT: Final = "5ca5b2f92e5c7245f957d9128b289ee535f0720d"
SCHEMA_URL: Final = (
    f"https://raw.githubusercontent.com/zarr-conventions/proj/{_COMMIT}/schema.json"
)
SPEC_URL: Final = f"https://github.com/zarr-conventions/proj/blob/{_COMMIT}/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "proj:",
    "description": "Coordinate reference system information for geospatial data",
}

CONVENTION_KEYS: Final = {"proj:code", "proj:wkt2", "proj:projjson"}

_CODE_PATTERN: Final = re.compile(r"^[^:]+:[^:]+$")


def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JSONDict | None = None,
) -> GeoProjAttrs:
    """Create a ``GeoProjAttrs`` dict (r3) from keyword arguments."""
    result = GeoProjAttrs()
    if code is not None:
        result["proj:code"] = code
    if wkt2 is not None:
        result["proj:wkt2"] = wkt2
    if projjson is not None:
        result["proj:projjson"] = projjson
    validate(result)
    return result


def create_convention_attrs(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JSONDict | None = None,
) -> GeoProjConventionAttrs:
    """Create a stand-alone attributes dict carrying proj (r3) and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    result: GeoProjConventionAttrs = {
        "zarr_conventions": [CMO],
        **create(code=code, wkt2=wkt2, projjson=projjson),
    }
    return result


def insert(
    attrs: Mapping[str, JSONValue], data: GeoProjAttrs, *, overwrite: bool = False
) -> JSONDict:
    """Insert proj (r3) convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, data, overwrite=overwrite)


def extract(
    attrs: Mapping[str, JSONValue],
) -> tuple[JSONDict, GeoProjAttrs]:
    """Extract proj (r3) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, GeoProjAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: Mapping[str, JSONValue]) -> GeoProjAttrs:
    """Validate proj (r3) data.

    At least one of ``proj:code``, ``proj:wkt2``, or ``proj:projjson`` must be
    present, and ``proj:code`` (if present) must match ``^[^:]+:[^:]+$``.
    """
    present = [k for k in ("proj:code", "proj:wkt2", "proj:projjson") if k in data]
    if not present:
        msg = (
            "At least one of 'proj:code', 'proj:wkt2', 'proj:projjson' must be present"
        )
        raise ValueError(msg)
    if "proj:code" in data and (
        not isinstance(data["proj:code"], str)
        or not _CODE_PATTERN.match(data["proj:code"])
    ):
        msg = f"'proj:code' must match {_CODE_PATTERN.pattern!r}, got {data['proj:code']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]


def _convention_data(metadata: Mapping[str, object]) -> GeoProjAttrs:
    """Pull this document's proj data out and run the attribute-level rules."""
    attributes = convention_attributes(metadata, CMO)
    _, data = extract(attributes)
    return validate(data)


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[GeoProjConventionAttrs]:
    """Validate a v3 group metadata document against proj (r3)."""
    node_type_of(metadata, expected="group")
    _convention_data(metadata)
    return cast("GroupMetadata[GeoProjConventionAttrs]", metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput,
) -> ArrayMetadata[GeoProjConventionAttrs]:
    """Validate a v3 array metadata document against proj (r3).

    Proj (r3) places no node-type-specific requirements on either
    node type, so this matches `validate_group_metadata()`.
    """
    node_type_of(metadata, expected="array")
    _convention_data(metadata)
    return cast("ArrayMetadata[GeoProjConventionAttrs]", metadata)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> ArrayMetadata[GeoProjConventionAttrs] | GroupMetadata[GeoProjConventionAttrs]:
    """Validate a v3 node metadata document against proj (r3).

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
