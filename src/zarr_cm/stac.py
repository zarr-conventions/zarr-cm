"""stac convention: https://github.com/zarr-conventions/stac

Single revision (v0.1, Proposal maturity): unlike `proj`/`spatial`, there is no
known prior draft revision to give a package-local `r2`-style label to, so this
follows the flat, unrevisioned shape of `license.py`/`uom.py`. Its attributes
are flat and key-prefixed (`stac:item`, ...) rather than nested under one
wrapper key, so the flat-key mechanics mirror `proj`'s "exactly one of" rule
instead.

The experimental `stac:array` field (Collection Array Storage) is out of
scope: it has no JSON Schema yet and is explicitly not accepted by the current
schema. See the upstream README's "Status" section.

Like every convention in this package, this module works on plain
attributes/metadata dicts -- it does no Zarr store I/O. In particular,
`stac:key` only carries and validates the *key string*; writing the JSON value
it points to (e.g. a `stac.json` next to `zarr.json`) into an actual store is
the caller's responsibility (with `zarr-python` or another store-writing
library), not this module's.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final, Never, NotRequired, cast

from typing_extensions import TypedDict

from zarr_cm._core import (
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
    resolve_revision_label,
)
from zarr_cm._node import NodeContext, node_convention_data, node_type_of, prepare_node

if TYPE_CHECKING:
    from collections.abc import Mapping


class StacLink(TypedDict, extra_items=JSONValue):
    """This type models the spec defined at https://github.com/zarr-conventions/stac/blob/v0.1/README.md#staclink"""

    href: str
    rel: NotRequired[str]
    type: NotRequired[str]


StacAttrs = TypedDict(
    "StacAttrs",
    {
        "stac:item": NotRequired[JSONDict],
        "stac:collection": NotRequired[JSONDict],
        "stac:key": NotRequired[str],
        "stac:link": NotRequired[StacLink],
    },
    extra_items=JSONValue,
)
"""This type models the spec defined at https://github.com/zarr-conventions/stac/blob/v0.1/README.md#fields"""

StacConventionAttrs = TypedDict(
    "StacConventionAttrs",
    {
        "zarr_conventions": Sequence[ConventionMetadataObject],
        "stac:item": NotRequired[JSONDict],
        "stac:collection": NotRequired[JSONDict],
        "stac:key": NotRequired[str],
        "stac:link": NotRequired[StacLink],
    },
    extra_items=JSONValue,
)
"""`StacAttrs` plus its `zarr_conventions` registration.

See https://github.com/zarr-conventions/stac/blob/v0.1/README.md#convention-metadata"""


UUID: Final = "b3703368-7e7e-4e8e-9e0e-6d0f0d5e8e8e"
_TAG: Final = "v0.1"
SCHEMA_URL: Final = f"https://raw.githubusercontent.com/zarr-conventions/stac/refs/tags/{_TAG}/schema.json"
SPEC_URL: Final = f"https://github.com/zarr-conventions/stac/blob/{_TAG}/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "stac:",
    "description": "STAC convention for embedding or referencing STAC objects in Zarr group metadata",
}


ALIAS_SCHEMA_URLS: Final[frozenset[str]] = frozenset()
"""Other schema_urls this revision recognizes: none besides `SCHEMA_URL`."""

RECOGNIZED_SCHEMA_URLS: Final[frozenset[str]] = frozenset(
    {SCHEMA_URL, *ALIAS_SCHEMA_URLS}
)
"""Every schema_url this revision reads as its own: `SCHEMA_URL` plus aliases."""

CONVENTION_KEYS: Final = {"stac:item", "stac:collection", "stac:key", "stac:link"}

REVISION_BY_SCHEMA_URL: Final[dict[str, str]] = dict.fromkeys(
    {SCHEMA_URL, *ALIAS_SCHEMA_URLS}, _TAG
)


def detect(attrs: Mapping[str, JSONValue]) -> str | None:
    """Return the revision label this document claims for the stac convention.

    Stac has a single revision (`"v0.1"`); returns it when present with the
    known schema_url, `None` if present with an unrecognized schema_url, and
    raises `ValueError` if the convention is absent.
    """
    return resolve_revision_label(attrs, UUID, REVISION_BY_SCHEMA_URL, "stac")


def create(
    *,
    item: JSONDict | None = None,
    collection: JSONDict | None = None,
    key: str | None = None,
    link: StacLink | None = None,
) -> StacAttrs:
    """Create a `StacAttrs` dict from keyword arguments."""
    result = StacAttrs()
    if item is not None:
        result["stac:item"] = item
    if collection is not None:
        result["stac:collection"] = collection
    if key is not None:
        result["stac:key"] = key
    if link is not None:
        result["stac:link"] = link
    validate(result)
    return result


def create_convention_attrs(
    *,
    item: JSONDict | None = None,
    collection: JSONDict | None = None,
    key: str | None = None,
    link: StacLink | None = None,
) -> StacConventionAttrs:
    """Create a stand-alone attributes dict carrying stac and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return cast(
        "StacConventionAttrs",
        {
            "zarr_conventions": [CMO],
            **create(item=item, collection=collection, key=key, link=link),
        },
    )


def insert(
    attrs: Mapping[str, JSONValue], data: StacAttrs, *, overwrite: bool = False
) -> JSONDict:
    """Insert stac convention metadata into an attributes dict."""
    return insert_convention(
        attrs, CMO, data, overwrite=overwrite, schema_urls=RECOGNIZED_SCHEMA_URLS
    )


def extract(
    attrs: Mapping[str, JSONValue],
) -> tuple[JSONDict, StacAttrs]:
    """Extract stac convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: declares_convention(cmo, UUID, RECOGNIZED_SCHEMA_URLS),
    )
    return remaining, cast("StacAttrs", convention_data)


def validate(data: Mapping[str, JSONValue]) -> StacAttrs:
    """Validate stac convention data.

    Exactly one of `stac:item`, `stac:collection`, `stac:key`, or `stac:link`
    must be present. `stac:item`/`stac:collection` are only checked for being
    JSON objects -- validating them as STAC Items/Collections is STAC's own
    job (see the spec's "Validation" section), not this convention's.

    The spec requires `stac:link.href` to be an absolute URL; this only checks
    that it is a string, not that it is absolute (the same shallow treatment
    `license`'s `url` field gets).
    """
    present = [k for k in CONVENTION_KEYS if k in data]
    if len(present) != 1:
        msg = (
            "Exactly one of 'stac:item', 'stac:collection', 'stac:key', "
            f"'stac:link' must be present, got: {present}"
        )
        raise ValueError(msg)
    if "stac:item" in data and not isinstance(data["stac:item"], dict):
        msg = (
            f"'stac:item' must be a JSON object, got {type(data['stac:item']).__name__}"
        )
        raise TypeError(msg)
    if "stac:collection" in data and not isinstance(data["stac:collection"], dict):
        msg = (
            "'stac:collection' must be a JSON object, "
            f"got {type(data['stac:collection']).__name__}"
        )
        raise TypeError(msg)
    if "stac:key" in data and not isinstance(data["stac:key"], str):
        msg = f"'stac:key' must be a string, got {type(data['stac:key']).__name__}"
        raise TypeError(msg)
    if "stac:link" in data:
        link = data["stac:link"]
        if not isinstance(link, dict):
            msg = f"'stac:link' must be a JSON object, got {type(link).__name__}"
            raise TypeError(msg)
        if "href" not in link:
            msg = "'stac:link' is missing required key 'href'"
            raise ValueError(msg)
        if not isinstance(link["href"], str):
            msg = (
                f"'stac:link.href' must be a string, got {type(link['href']).__name__}"
            )
            raise TypeError(msg)
        for key in ("rel", "type"):
            if key in link and not isinstance(link[key], str):
                msg = f"'stac:link.{key}' must be a string, got {type(link[key]).__name__}"
                raise TypeError(msg)
    return cast("StacAttrs", data)


def _validate_context(context: NodeContext) -> None:
    """Validate stac against an already prepared node."""
    if context.node_type == "array":
        msg = "the 'stac:' convention does not apply to array nodes"
        raise ValueError(msg)
    data = node_convention_data(
        context, CMO, CONVENTION_KEYS, schema_urls=RECOGNIZED_SCHEMA_URLS
    )
    validate(data)


def validate_group_metadata(
    metadata: GroupMetadataInput,
) -> GroupMetadata[StacConventionAttrs]:
    """Validate a v3 group metadata document against the stac convention."""
    context = prepare_node(metadata, expected_node_type="group")
    _validate_context(context)
    return cast("GroupMetadata[StacConventionAttrs]", context.metadata)


def validate_array_metadata(metadata: ArrayMetadataInput) -> Never:
    """Reject a v3 array metadata document: stac is a group-only convention.

    The schema restricts `node_type` to `"group"`, so there is no valid
    array form of this convention and this always raises.
    """
    _validate_context(prepare_node(metadata, expected_node_type="array"))
    msg = "stac array validation unexpectedly returned"
    raise AssertionError(msg)


def validate_node_metadata(
    metadata: NodeMetadataInput,
) -> Metadata[StacConventionAttrs]:
    """Validate a v3 node metadata document against the stac convention.

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`. Only the
    group arm can return: stac has no valid array form.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(cast("ArrayMetadataInput", metadata))
    return validate_group_metadata(cast("GroupMetadataInput", metadata))
