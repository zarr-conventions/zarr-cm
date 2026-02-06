from __future__ import annotations

import typing
from typing import Any, NotRequired, TypedDict

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

    zarr_conventions: list[ConventionMetadataObject]


def validate_convention_metadata_object(cmo: dict[str, Any]) -> None:
    """Validate that a ConventionMetadataObject has at least one identifier."""
    if not any(k in cmo for k in ("uuid", "schema_url", "spec_url")):
        msg = "ConventionMetadataObject must have at least one of 'uuid', 'schema_url', or 'spec_url'"
        raise ValueError(msg)


def insert_convention(
    attrs: dict[str, Any],
    cmo: ConventionMetadataObject,
    convention_data: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
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
    existing: list[ConventionMetadataObject] = list(result.get("zarr_conventions", []))
    if cmo not in existing:
        existing.append(cmo)
    result["zarr_conventions"] = existing
    return result


def extract_convention(
    attrs: dict[str, Any],
    convention_keys: set[str],
    match_fn: Callable[[ConventionMetadataObject], bool],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract convention metadata from an attributes dict.

    Returns ``(remaining_attrs, convention_data)`` where the matching CMO
    is removed from ``zarr_conventions`` and the convention-specific keys
    are separated out.
    """
    remaining: dict[str, Any] = {}
    convention_data: dict[str, Any] = {}

    for key, value in attrs.items():
        if key == "zarr_conventions":
            continue
        if key in convention_keys:
            convention_data[key] = value
        else:
            remaining[key] = value

    old_conventions: list[ConventionMetadataObject] = attrs.get("zarr_conventions", [])
    new_conventions = [cmo for cmo in old_conventions if not match_fn(cmo)]
    if new_conventions:
        remaining["zarr_conventions"] = new_conventions

    return remaining, convention_data
