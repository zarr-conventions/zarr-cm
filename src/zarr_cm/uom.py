"""uom convention: https://github.com/clbarnes/zarr-convention-uom"""

from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)


class UCUM(TypedDict):
    """Unified Code for Units of Measurement information."""

    unit: NotRequired[str]
    version: NotRequired[str]


class UomAttrs(TypedDict):
    """Unit of measurement metadata for a Zarr array."""

    ucum: UCUM
    description: NotRequired[str]


class UomConventionAttrs(TypedDict):
    """Attributes dict containing uom convention metadata."""

    zarr_conventions: list[ConventionMetadataObject]
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


def create(
    *,
    ucum: UCUM,
    description: str | None = None,
) -> UomAttrs:
    """Create a ``UomAttrs`` dict from keyword arguments."""
    result = UomAttrs(ucum=ucum)
    if description is not None:
        result["description"] = description
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: UomAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert uom convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, {"uom": dict(data)}, overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], UomAttrs]:
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


def validate(data: dict[str, Any]) -> UomAttrs:
    """Validate uom convention data.

    ``ucum`` must be present.
    """
    if "ucum" not in data:
        msg = "'ucum' is required"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
