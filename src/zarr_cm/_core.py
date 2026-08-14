from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import (
    TYPE_CHECKING,
    Final,
    Generic,
    Literal,
    NotRequired,
    TypeAlias,
    TypeGuard,
)

from typing_extensions import ReadOnly, TypeAliasType, TypedDict, TypeVar

# `JSONValue` is zarr-metadata's, imported under its own name: one definition
# of "a JSON value" across both packages, so their document types and ours
# unify without casts. The convention modules and the public package import
# it from here. The properties this package relies on hold upstream by
# construction:
#
# * The array arm is the covariant ``Sequence`` (not the invariant
#   ``list``/``tuple``), so concrete JSON-shaped values -- and the convention
#   ``TypedDict``s, whose fields carry narrower types like ``Sequence[str]`` --
#   are assignable to it. A JSON array is still a ``list`` at runtime; the
#   ``Sequence`` arm just declines to require a particular container at the
#   type level.
# * It is a real recursive ``TypeAliasType``, which is what lets a downstream
#   pydantic model embed the convention ``TypedDict``s (which use it as
#   ``extra_items``) without ``RecursionError`` in ``model_rebuild()``. See
#   https://github.com/zarr-conventions/zarr-cm/issues/18.
#
# This import is the reason zarr-metadata is a runtime dependency:
# ``extra_items=JSONValue`` is evaluated at class-creation time.
from zarr_metadata import JSONValue

if TYPE_CHECKING:
    from collections.abc import Callable

    from zarr_metadata import ZarrV3ArrayMetadataJSON, ZarrV3GroupMetadataJSON

NodeType = Literal["array", "group"]
"""The two node types a Zarr v3 metadata document can describe."""

NODE_TYPES: Final[frozenset[NodeType]] = frozenset({"array", "group"})
"""Every value `node_type` may take in a Zarr v3 metadata document."""

JSONDict = TypeAliasType("JSONDict", dict[str, JSONValue])
"""A mutable JSON object: what `json.loads` yields for a JSON document.

Named to match zarr-metadata's `JSONValue` grammar; zarr-metadata itself
exports no dict alias, so this is the one JSON name this package defines.
"""


AttrsT_co = TypeVar("AttrsT_co", covariant=True, default=Mapping[str, JSONValue])
"""Type parameter for a metadata document's `attributes` field.

Covariant, so a document whose attributes satisfy a *narrower* TypedDict is
assignable wherever a wider one is expected -- `GroupMetadata[BothConventions]`
flows into a parameter of `GroupMetadata[SpatialConventionAttrs]`. The PEP 696
default makes the bare `GroupMetadata` / `ArrayMetadata` spell the wide,
unvalidated form.
"""


class ArrayMetadata(TypedDict, Generic[AttrsT_co], extra_items=JSONValue):
    """A Zarr v3 array metadata document, generic over its `attributes` type.

    The type parameter states what is known about `attributes`. Bare
    `ArrayMetadata` is the wide form -- attributes are an arbitrary JSON object
    -- and the `validate_*_metadata` functions narrow it: validating against
    spatial returns `ArrayMetadata[SpatialConventionAttrs]`, so the validated
    document's convention keys are typed rather than `JSONValue`.

    `attributes` is `ReadOnly`, which is what makes the parameter covariant; the
    other v3 array fields (`shape`, `data_type`, `codecs`, ...) fall under
    `extra_items` -- this type models the convention-bearing part of the
    document, not the whole array schema. Use `zarr-metadata`'s
    `ZarrV3ArrayMetadataJSON` when those fields matter.

    Narrowing is a claim about the moment of validation: the mapping underneath
    is still mutable, so mutating a narrowed document does not un-narrow it.
    """

    zarr_format: Literal[3]
    node_type: Literal["array"]
    attributes: ReadOnly[AttrsT_co]


class GroupMetadata(TypedDict, Generic[AttrsT_co], extra_items=JSONValue):
    """A Zarr v3 group metadata document, generic over its `attributes` type.

    The group counterpart of `ArrayMetadata`; see there for the semantics.
    """

    zarr_format: Literal[3]
    node_type: Literal["group"]
    attributes: ReadOnly[AttrsT_co]


ArrayMetadataInput: TypeAlias = "ZarrV3ArrayMetadataJSON | ArrayMetadata"
"""What an array validator accepts: a raw `zarr-metadata` document or ours.

The second arm is the wide `ArrayMetadata` (its type parameter defaults to
`Mapping[str, JSONValue]`), and covariance means every *narrowed*
`ArrayMetadata[...]` is assignable to it too -- so validators chain:
`proj.validate_array_metadata(spatial.validate_array_metadata(doc))`.
"""

GroupMetadataInput: TypeAlias = "ZarrV3GroupMetadataJSON | GroupMetadata"
"""What a group validator accepts; see `ArrayMetadataInput`."""

NodeMetadataInput: TypeAlias = "ArrayMetadataInput | GroupMetadataInput"
"""What a node validator accepts: either node type, raw or narrowed."""

NodeMetadataInputT = TypeVar("NodeMetadataInputT", bound=NodeMetadataInput)
"""Type variable over `NodeMetadataInput`, for pass-through validators.

The package-level validators fan out over whichever conventions the document
declares -- a runtime-determined set -- so there is no single convention to
narrow to; they return their input at the type it came in with.
"""


def _is_mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, Mapping)


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(
        value, str | bytes | bytearray
    )


class ConventionMetadataObject(TypedDict, extra_items=JSONValue):
    """A convention metadata object for the ``zarr_conventions`` array."""

    uuid: NotRequired[str]
    schema_url: NotRequired[str]
    spec_url: NotRequired[str]
    name: NotRequired[str]
    description: NotRequired[str]


class ConventionAttrs(TypedDict, extra_items=JSONValue):
    """Attributes dict with a ``zarr_conventions`` array."""

    zarr_conventions: Sequence[ConventionMetadataObject]


def validate_json_value(value: object) -> JSONValue:
    """Validate and return a JSON-shaped value."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if _is_mapping(value):
        return validate_json_object(value)
    if _is_sequence(value):
        return [validate_json_value(item) for item in value]
    msg = f"expected a JSON value, got {type(value).__name__}"
    raise TypeError(msg)


def validate_json_object(value: object) -> JSONDict:
    """Validate and return a mutable JSON object with string keys."""
    if not _is_mapping(value):
        msg = f"expected a JSON object, got {type(value).__name__}"
        raise TypeError(msg)
    result: JSONDict = {}
    for key, item in value.items():
        if not isinstance(key, str):
            msg = f"expected JSON object keys to be str, got {type(key).__name__}"
            raise TypeError(msg)
        result[key] = validate_json_value(item)
    return result


def validate_convention_metadata_objects(
    value: object,
) -> list[ConventionMetadataObject]:
    """Validate a ``zarr_conventions`` value."""
    if value is None:
        return []
    if not _is_sequence(value):
        msg = "zarr_conventions must be an array of convention metadata objects"
        raise TypeError(msg)

    result: list[ConventionMetadataObject] = []
    for item in value:
        obj = validate_json_object(item)
        cmo = ConventionMetadataObject()
        for key in ("uuid", "schema_url", "spec_url", "name", "description"):
            if key not in obj:
                continue
            field = obj[key]
            if not isinstance(field, str):
                msg = f"ConventionMetadataObject field {key!r} must be a string"
                raise TypeError(msg)
            cmo[key] = field
        result.append(cmo)
    return result


def validate_convention_metadata_object(cmo: JSONDict) -> None:
    """Validate that a ConventionMetadataObject has at least one identifier."""
    if not any(k in cmo for k in ("uuid", "schema_url", "spec_url")):
        msg = "ConventionMetadataObject must have at least one of 'uuid', 'schema_url', or 'spec_url'"
        raise ValueError(msg)


def node_attributes(metadata: Mapping[str, object]) -> JSONDict:
    """Return the `attributes` object of a Zarr v3 node metadata document.

    `attributes` is optional in the v3 spec; a document without it is treated
    as carrying none. Raises `TypeError` if it is present but is not a JSON
    object.
    """
    attributes = metadata.get("attributes", {})
    if not _is_mapping(attributes):
        # Name the field: the generic "expected a JSON object" from
        # validate_json_object would leave the caller to work out, from
        # traceback frames alone, which of a document's many objects was wrong.
        msg = f"'attributes' must be a JSON object, got {type(attributes).__name__}"
        raise TypeError(msg)
    return validate_json_object(attributes)


def node_type_of(
    metadata: Mapping[str, object],
    *,
    expected: NodeType | None = None,
) -> NodeType:
    """Return the `node_type` of a Zarr v3 node metadata document.

    Args:
        metadata: The full metadata document (the contents of a node's `zarr.json`).
        expected: When given, raise `ValueError` unless the document's `node_type`
            equals it. Callers that already know which node type they want -- e.g.
            `validate_array_metadata` -- pass it, so that a mismatched document is
            rejected rather than quietly validated under the other node type's rules.
    """
    zarr_format = metadata.get("zarr_format")
    if zarr_format != 3:
        msg = f"conventions are defined for zarr_format 3, got {zarr_format!r}"
        raise ValueError(msg)

    node_type = metadata.get("node_type")
    if node_type not in NODE_TYPES:
        msg = f"'node_type' must be one of {sorted(NODE_TYPES)}, got {node_type!r}"
        raise ValueError(msg)

    if expected is not None and node_type != expected:
        msg = f"expected a {expected!r} metadata document, got node_type {node_type!r}"
        raise ValueError(msg)

    return node_type


def convention_present(attrs: Mapping[str, JSONValue], uuid: str) -> bool:
    """Report whether *attrs* declares the convention identified by *uuid*."""
    return any(
        cmo.get("uuid") == uuid
        for cmo in validate_convention_metadata_objects(attrs.get("zarr_conventions"))
    )


def convention_attributes(
    metadata: Mapping[str, object],
    cmo: ConventionMetadataObject,
    *,
    expected_node_type: NodeType | None = None,
) -> JSONDict:
    """Return the `attributes` of a v3 node document that declares *cmo*'s convention.

    This is the preamble every convention's node validators share, and only the
    preamble: the document is Zarr v3, its `node_type` is a known one (and the
    expected one), `attributes` is a JSON object, and the convention is actually
    declared there. What the convention then requires of those attributes --
    which keys, on which node type, or whether the node type is allowed at all
    -- is the convention's own business, expressed in its own module.

    A convention identifies itself by its convention metadata object -- the same
    `CMO` constant it writes into documents -- rather than by loose name/uuid
    strings at the call site. The declaration check matches on the CMO's
    `uuid`, and error messages use its spec `name`.

    Args:
        metadata: The full metadata document (the contents of a node's `zarr.json`).
        cmo: The calling convention's metadata object (its module's `CMO`).
        expected_node_type: Passed through to `node_type_of()`.
    """
    node_type_of(metadata, expected=expected_node_type)
    attributes = node_attributes(metadata)
    uuid = cmo.get("uuid")
    if uuid is None or not convention_present(attributes, uuid):
        name = cmo.get("name") or uuid or "<unnamed>"
        msg = f"the {name!r} convention is not declared in this document's 'zarr_conventions'"
        raise ValueError(msg)
    return attributes


def insert_convention(
    attrs: Mapping[str, JSONValue],
    cmo: ConventionMetadataObject,
    convention_data: Mapping[str, JSONValue],
    *,
    overwrite: bool = False,
) -> JSONDict:
    """Insert convention metadata into an attributes dict.

    Returns a new dict with the convention data merged in and the CMO
    appended to the ``zarr_conventions`` array.

    Parameters
    ----------
    attrs
        The existing attributes dict.
    cmo
        The convention metadata object to append to ``zarr_conventions``.
    convention_data
        Convention-specific keys to merge into *attrs*.
    overwrite
        If False (default), raise ``ValueError`` when *attrs* already
        contains keys present in *convention_data*.  If True, the
        convention data silently overwrites colliding keys.
    """
    if not overwrite:
        collisions = set(attrs) & (set(convention_data) - {"zarr_conventions"})
        if collisions:
            msg = f"attrs already contains keys that would be overwritten by convention data: {sorted(collisions)}. Pass overwrite=True to allow."
            raise ValueError(msg)
    result = {**attrs, **convention_data}
    existing = validate_convention_metadata_objects(result.get("zarr_conventions"))
    if cmo not in existing:
        existing.append(cmo)
    result["zarr_conventions"] = existing
    return result


def extract_convention(
    attrs: Mapping[str, JSONValue],
    convention_keys: set[str],
    match_fn: Callable[[ConventionMetadataObject], bool],
) -> tuple[JSONDict, JSONDict]:
    """Extract convention metadata from an attributes dict.

    Returns ``(remaining_attrs, convention_data)`` where the matching CMO
    is removed from ``zarr_conventions`` and the convention-specific keys
    are separated out.
    """
    remaining: JSONDict = {}
    convention_data: JSONDict = {}

    for key, value in attrs.items():
        if key == "zarr_conventions":
            continue
        if key in convention_keys:
            convention_data[key] = value
        else:
            remaining[key] = value

    old_conventions = validate_convention_metadata_objects(
        attrs.get("zarr_conventions")
    )
    new_conventions = [cmo for cmo in old_conventions if not match_fn(cmo)]
    if new_conventions:
        remaining["zarr_conventions"] = new_conventions

    return remaining, convention_data


def resolve_revision_label(
    attrs: Mapping[str, JSONValue],
    uuid: str,
    schema_url_by_revision: dict[str, str],
    convention_name: str,
) -> str | None:
    """Return the revision label a document claims for a convention.

    Returns the label whose ``schema_url`` matches the convention's CMO, or
    ``None`` if the convention's ``uuid`` is present but its ``schema_url`` is
    unrecognized (an older/newer/foreign revision). Raises ``ValueError`` if the
    convention is absent (no CMO with *uuid*) -- asking which revision is present
    for a convention that is not there is a caller error.
    """
    if not convention_present(attrs, uuid):
        msg = f"convention {convention_name!r} is not present in attrs"
        raise ValueError(msg)
    return detect_revision(attrs, uuid, schema_url_by_revision)


def detect_revision(
    attrs: Mapping[str, JSONValue],
    uuid: str,
    schema_url_by_revision: dict[str, str],
) -> str | None:
    """Return the revision label whose pinned schema_url matches the document's CMO.

    Looks for a convention-metadata object in ``attrs['zarr_conventions']``
    whose ``uuid`` matches *uuid*. If found, returns the revision label whose
    ``schema_url`` equals that CMO's ``schema_url``. Returns ``None`` if the
    convention is absent, or present but carrying an unrecognized schema_url
    (e.g. a legacy/dangling URL) -- callers fall back to the latest revision.

    Entries in ``zarr_conventions`` are assumed to be CMO dicts (consistent
    with the rest of this module). Revisions are assumed to have distinct
    ``schema_url`` values; if two share one, the inverse mapping is ambiguous.
    """
    by_url = {url: label for label, url in schema_url_by_revision.items()}
    for cmo in validate_convention_metadata_objects(attrs.get("zarr_conventions")):
        if cmo.get("uuid") == uuid:
            schema_url = cmo.get("schema_url")
            if isinstance(schema_url, str):
                return by_url.get(schema_url)
    return None
