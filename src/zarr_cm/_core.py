from __future__ import annotations

import typing
from typing import NotRequired, TypedDict

JsonPrimitive = bool | int | float | str | None
JsonType = (
    JsonPrimitive | list["JsonType"] | tuple["JsonType", ...] | dict[str, "JsonType"]
)
JsonDict = dict[str, JsonType]

if typing.TYPE_CHECKING:
    from collections.abc import Callable


class ConventionMetadataObject(TypedDict):
    """A convention metadata object for the ``zarr_conventions`` array."""

    uuid: NotRequired[str]
    schema_url: NotRequired[str]
    spec_url: NotRequired[str]
    name: NotRequired[str]
    description: NotRequired[str]


class ConventionAttrs(TypedDict):
    """Attributes dict with a ``zarr_conventions`` array."""

    zarr_conventions: tuple[ConventionMetadataObject, ...]


def validate_convention_metadata_object(cmo: JsonDict) -> None:
    """Validate that a ConventionMetadataObject has at least one identifier."""
    if not any(k in cmo for k in ("uuid", "schema_url", "spec_url")):
        msg = "ConventionMetadataObject must have at least one of 'uuid', 'schema_url', or 'spec_url'"
        raise ValueError(msg)


def insert_convention(
    attrs: JsonDict,
    cmo: ConventionMetadataObject,
    convention_data: JsonDict,
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
    existing: list[ConventionMetadataObject] = list(
        typing.cast(
            "typing.Iterable[ConventionMetadataObject]",
            result.get("zarr_conventions", ()),
        )
    )
    if cmo not in existing:
        existing.append(cmo)
    result["zarr_conventions"] = typing.cast("JsonType", existing)
    return result


def extract_convention(
    attrs: JsonDict,
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

    old_conventions = typing.cast(
        "typing.Iterable[ConventionMetadataObject]", attrs.get("zarr_conventions", ())
    )
    new_conventions = [cmo for cmo in old_conventions if not match_fn(cmo)]
    if new_conventions:
        remaining["zarr_conventions"] = typing.cast("JsonType", new_conventions)

    return remaining, convention_data


def resolve_revision_label(
    attrs: JsonDict,
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
        for cmo in typing.cast(
            "typing.Iterable[ConventionMetadataObject]",
            attrs.get("zarr_conventions", ()),
        )
    )
    if not present:
        msg = f"convention {convention_name!r} is not present in attrs"
        raise ValueError(msg)
    return detect_revision(attrs, uuid, schema_url_by_revision)


def detect_revision(
    attrs: JsonDict,
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
    for cmo in typing.cast(
        "typing.Iterable[ConventionMetadataObject]", attrs.get("zarr_conventions", ())
    ):
        if cmo.get("uuid") == uuid:
            return by_url.get(cmo.get("schema_url", ""))
    return None
