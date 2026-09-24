"""proj convention, revision r3 (v0.1).

Snapshot of upstream at commit 5ca5b2f92e5c7245f957d9128b289ee535f0720d (tag
v0.1). Relaxes the `proj:code` pattern (now `^[^:]+:[^:]+$`) and the CRS
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
    Metadata,
    NodeMetadataInput,
    declares_convention,
    extract_convention,
    insert_convention,
)
from zarr_cm._node import NodeContext, node_convention_data, node_type_of, prepare_node

GeoProjAttrs = TypedDict(
    "GeoProjAttrs",
    {
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[JSONDict],
    },
    extra_items=JSONValue,
)
"""This type models the spec defined at https://github.com/zarr-conventions/proj/blob/5ca5b2f92e5c7245f957d9128b289ee535f0720d/README.md#field-details"""

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
"""`GeoProjAttrs` plus its `zarr_conventions` registration.

See https://github.com/zarr-conventions/proj/blob/5ca5b2f92e5c7245f957d9128b289ee535f0720d/README.md#convention-registration"""

# UUID identifies the convention *family*, not the revision; it is shared by
# every revision. Revisions are distinguished by the SCHEMA_URL below, which is what
# revision detection on read matches against.
#
# The upstream v0.1 schema ENFORCES schema_url/spec_url as `const` equal to the
# refs/tags/v0.1 URLs (no escape hatch), so we must emit those exact tag URLs to
# validate. The snapshot is still taken at commit _COMMIT; _TAG is the
# published tag at that commit.
UUID: Final = "f17cb550-5864-4468-aeb7-f3180cfb622f"
_COMMIT: Final = "5ca5b2f92e5c7245f957d9128b289ee535f0720d"
_TAG: Final = "v0.1"
SCHEMA_URL: Final = f"https://raw.githubusercontent.com/zarr-conventions/proj/refs/tags/{_TAG}/schema.json"
SPEC_URL: Final = f"https://github.com/zarr-conventions/proj/blob/{_TAG}/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "proj",
    "description": "Coordinate reference system information for geospatial data",
}


ALIAS_SCHEMA_URLS: Final[frozenset[str]] = frozenset(
    {
        f"https://raw.githubusercontent.com/zarr-conventions/proj/{_COMMIT}/schema.json",
    }
)
"""Other schema_urls this revision recognizes as its own identity.

The commit-pinned URL is what earlier `zarr-cm` releases wrote before the
`v0.1` tag URL was confirmed resolvable; documents carrying it must still read
as this revision.
"""

RECOGNIZED_SCHEMA_URLS: Final[frozenset[str]] = frozenset(
    {SCHEMA_URL, *ALIAS_SCHEMA_URLS}
)
"""Every schema_url this revision reads as its own: `SCHEMA_URL` plus aliases."""

CONVENTION_KEYS: Final = {"proj:code", "proj:wkt2", "proj:projjson"}

_CODE_PATTERN: Final = re.compile(r"^[^:]+:[^:]+$")


def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JSONDict | None = None,
) -> GeoProjAttrs:
    """Create a `GeoProjAttrs` dict (r3) from keyword arguments."""
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
    return cast(
        "GeoProjConventionAttrs",
        {
            "zarr_conventions": [CMO],
            **create(code=code, wkt2=wkt2, projjson=projjson),
        },
    )


def insert(
    attrs: Mapping[str, JSONValue], data: GeoProjAttrs, *, overwrite: bool = False
) -> JSONDict:
    """Insert proj (r3) convention metadata into an attributes dict."""
    return insert_convention(
        attrs, CMO, data, overwrite=overwrite, schema_urls=RECOGNIZED_SCHEMA_URLS
    )


def extract(
    attrs: Mapping[str, JSONValue],
) -> tuple[JSONDict, GeoProjAttrs]:
    """Extract proj (r3) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: declares_convention(cmo, UUID, RECOGNIZED_SCHEMA_URLS),
    )
    return remaining, cast("GeoProjAttrs", convention_data)


def validate(data: Mapping[str, JSONValue]) -> GeoProjAttrs:
    """Validate proj (r3) data.

    At least one of `proj:code`, `proj:wkt2`, or `proj:projjson` must be
    present, and `proj:code` (if present) must match `^[^:]+:[^:]+$`.
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
    if "proj:wkt2" in data and not isinstance(data["proj:wkt2"], str):
        msg = f"'proj:wkt2' must be a string, got {type(data['proj:wkt2']).__name__}"
        raise TypeError(msg)
    if "proj:projjson" in data and not isinstance(data["proj:projjson"], dict):
        msg = (
            "'proj:projjson' must be a JSON object, "
            f"got {type(data['proj:projjson']).__name__}"
        )
        raise TypeError(msg)
    return cast("GeoProjAttrs", data)


def _validate_context(context: NodeContext) -> None:
    """Validate proj against an already prepared node."""
    validate(
        node_convention_data(
            context, CMO, CONVENTION_KEYS, schema_urls=RECOGNIZED_SCHEMA_URLS
        )
    )


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[GeoProjConventionAttrs]:
    """Validate a v3 group metadata document against proj (r3)."""
    context = prepare_node(metadata, expected_node_type="group")
    _validate_context(context)
    return cast("GroupMetadata[GeoProjConventionAttrs]", context.metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput,
) -> ArrayMetadata[GeoProjConventionAttrs]:
    """Validate a v3 array metadata document against proj (r3).

    Proj (r3) places no node-type-specific requirements on either
    node type, so this matches `validate_group_metadata()`.
    """
    context = prepare_node(metadata, expected_node_type="array")
    _validate_context(context)
    return cast("ArrayMetadata[GeoProjConventionAttrs]", context.metadata)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> Metadata[GeoProjConventionAttrs]:
    """Validate a v3 node metadata document against proj (r3).

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
