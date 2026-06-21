from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, NotRequired, TypeGuard

from typing_extensions import TypeAliasType, TypedDict

if TYPE_CHECKING:
    from collections.abc import Callable

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
    present = any(
        cmo.get("uuid") == uuid
        for cmo in validate_convention_metadata_objects(attrs.get("zarr_conventions"))
    )
    if not present:
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
