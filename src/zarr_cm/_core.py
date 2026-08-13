from __future__ import annotations

import sys
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

if TYPE_CHECKING:
    from collections.abc import Callable

    from zarr_metadata import ZarrV3ArrayMetadataJSON, ZarrV3GroupMetadataJSON

NodeType = Literal["array", "group"]
"""The two node types a Zarr v3 metadata document can describe."""

NODE_TYPES: Final[frozenset[NodeType]] = frozenset({"array", "group"})
"""Every value `node_type` may take in a Zarr v3 metadata document."""

JsonPrimitive = bool | int | float | str | None
# A read-only, covariant *type-level* view of a JSON value. ``Sequence`` and
# ``Mapping`` are covariant in their item/value type (unlike the invariant
# ``list``/``dict``), so concrete JSON-shaped values -- and the convention
# ``TypedDict``s -- are assignable to it. This says nothing about the concrete
# runtime container: a JSON array is a ``list`` at runtime (that is what
# ``json.loads`` produces and what ``json.dumps``/jsonschema expect); the
# ``Sequence`` arm just declines to *require* a particular container at the type
# level so both lists and tuples type-check.
#
# ``JsonValue`` is a *recursive* alias and MUST be a real ``TypeAliasType`` (the
# PEP 695 ``type`` form), not a bare ``X = ... "X" ...`` union: the convention
# ``TypedDict``s use it as ``extra_items``, and a downstream pydantic model that
# embeds one of those ``TypedDict``s would otherwise raise ``RecursionError`` in
# ``model_rebuild()``. On Python 3.12+ we use the native ``type`` statement (from
# ``_json_alias``, which pyright resolves cleanly); on 3.11 -- where ``type`` is a
# syntax error -- we fall back to the runtime-equivalent ``TypeAliasType``. The
# project type-checks at ``pythonVersion = 3.12`` so the native form is the one
# pyright sees. See https://github.com/zarr-conventions/zarr-cm/issues/18.
if sys.version_info >= (3, 12):
    from ._json_alias import JsonDict, JsonValue
else:  # pragma: no cover - exercised only on Python 3.11
    JsonValue = TypeAliasType(
        "JsonValue",
        JsonPrimitive | Sequence["JsonValue"] | Mapping[str, "JsonValue"],
    )
    JsonDict = TypeAliasType("JsonDict", dict[str, JsonValue])


AttrsT_co = TypeVar("AttrsT_co", covariant=True, default=Mapping[str, JsonValue])
"""Type parameter for a metadata document's `attributes` field.

Covariant, so a document whose attributes satisfy a *narrower* TypedDict is
assignable wherever a wider one is expected -- `GroupMetadata[BothConventions]`
flows into a parameter of `GroupMetadata[SpatialConventionAttrs]`. The PEP 696
default makes the bare `GroupMetadata` / `ArrayMetadata` spell the wide,
unvalidated form.
"""


class ArrayMetadata(TypedDict, Generic[AttrsT_co], extra_items=JsonValue):
    """A Zarr v3 array metadata document, generic over its `attributes` type.

    The type parameter states what is known about `attributes`. Bare
    `ArrayMetadata` is the wide form -- attributes are an arbitrary JSON object
    -- and the `validate_*_metadata` functions narrow it: validating against
    spatial returns `ArrayMetadata[SpatialConventionAttrs]`, so the validated
    document's convention keys are typed rather than `JsonValue`.

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


class GroupMetadata(TypedDict, Generic[AttrsT_co], extra_items=JsonValue):
    """A Zarr v3 group metadata document, generic over its `attributes` type.

    The group counterpart of `ArrayMetadata`; see there for the semantics.
    """

    zarr_format: Literal[3]
    node_type: Literal["group"]
    attributes: ReadOnly[AttrsT_co]


ArrayMetadataInput: TypeAlias = "ZarrV3ArrayMetadataJSON | ArrayMetadata"
"""What an array validator accepts: a raw `zarr-metadata` document or ours.

The second arm is the wide `ArrayMetadata` (its type parameter defaults to
`Mapping[str, JsonValue]`), and covariance means every *narrowed*
`ArrayMetadata[...]` is assignable to it too -- so validators chain:
`proj.validate_array_metadata(spatial.validate_array_metadata(doc))`.

`zarr-metadata` is a typing-only dependency: it is imported under
`TYPE_CHECKING` and the validators read documents structurally at runtime, so
it stays out of the minimal runtime dependency set. The test suite runs
without it (`just test-ci` installs the test group alone), which keeps that
honest.
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


class ConventionMetadataObject(TypedDict, extra_items=JsonValue):
    """A convention metadata object for the ``zarr_conventions`` array."""

    uuid: NotRequired[str]
    schema_url: NotRequired[str]
    spec_url: NotRequired[str]
    name: NotRequired[str]
    description: NotRequired[str]


class ConventionAttrs(TypedDict, extra_items=JsonValue):
    """Attributes dict with a ``zarr_conventions`` array."""

    zarr_conventions: Sequence[ConventionMetadataObject]


def validate_json_value(value: object) -> JsonValue:
    """Validate and return a JSON-shaped value."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if _is_mapping(value):
        return validate_json_object(value)
    if _is_sequence(value):
        return [validate_json_value(item) for item in value]
    msg = f"expected a JSON value, got {type(value).__name__}"
    raise TypeError(msg)


def validate_json_object(value: object) -> JsonDict:
    """Validate and return a mutable JSON object with string keys."""
    if not _is_mapping(value):
        msg = f"expected a JSON object, got {type(value).__name__}"
        raise TypeError(msg)
    result: JsonDict = {}
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


def validate_convention_metadata_object(cmo: JsonDict) -> None:
    """Validate that a ConventionMetadataObject has at least one identifier."""
    if not any(k in cmo for k in ("uuid", "schema_url", "spec_url")):
        msg = "ConventionMetadataObject must have at least one of 'uuid', 'schema_url', or 'spec_url'"
        raise ValueError(msg)


def node_attributes(metadata: Mapping[str, object]) -> JsonDict:
    """Return the `attributes` object of a Zarr v3 node metadata document.

    `attributes` is optional in the v3 spec; a document without it is treated
    as carrying none. Raises `TypeError` if it is present but is not a JSON
    object.
    """
    return validate_json_object(metadata.get("attributes", {}))


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


def convention_present(attrs: Mapping[str, JsonValue], uuid: str) -> bool:
    """Report whether *attrs* declares the convention identified by *uuid*."""
    return any(
        cmo.get("uuid") == uuid
        for cmo in validate_convention_metadata_objects(attrs.get("zarr_conventions"))
    )


def convention_attributes(
    metadata: Mapping[str, object],
    *,
    convention: str,
    uuid: str,
    expected_node_type: NodeType | None = None,
) -> JsonDict:
    """Return the `attributes` of a v3 node document that declares *convention*.

    This is the preamble every convention's node validators share, and only the
    preamble: the document is Zarr v3, its `node_type` is a known one (and the
    expected one), `attributes` is a JSON object, and *convention* is actually
    declared there. What the convention then requires of those attributes --
    which keys, on which node type, or whether the node type is allowed at all
    -- is the convention's own business, expressed in its own module.

    Args:
        metadata: The full metadata document (the contents of a node's `zarr.json`).
        convention: Display name of the convention, used in error messages.
        uuid: The convention's UUID, which the document must declare in
            `attributes['zarr_conventions']`.
        expected_node_type: Passed through to `node_type_of()`.
    """
    node_type_of(metadata, expected=expected_node_type)
    attributes = node_attributes(metadata)
    if not convention_present(attributes, uuid):
        msg = f"the {convention!r} convention is not declared in this document's 'zarr_conventions'"
        raise ValueError(msg)
    return attributes


def insert_convention(
    attrs: Mapping[str, JsonValue],
    cmo: ConventionMetadataObject,
    convention_data: Mapping[str, JsonValue],
    *,
    overwrite: bool = False,
) -> JsonDict:
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
    attrs: Mapping[str, JsonValue],
    convention_keys: set[str],
    match_fn: Callable[[ConventionMetadataObject], bool],
) -> tuple[JsonDict, JsonDict]:
    """Extract convention metadata from an attributes dict.

    Returns ``(remaining_attrs, convention_data)`` where the matching CMO
    is removed from ``zarr_conventions`` and the convention-specific keys
    are separated out.
    """
    remaining: JsonDict = {}
    convention_data: JsonDict = {}

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
    attrs: Mapping[str, JsonValue],
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
    attrs: Mapping[str, JsonValue],
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
