"""multiscales convention: https://github.com/zarr-conventions/multiscales"""

from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)


class Transform(TypedDict):
    """Coordinate transformation with scale and translation."""

    scale: NotRequired[list[float]]
    translation: NotRequired[list[float]]


class LayoutObject(TypedDict):
    """A single resolution level in a multiscale pyramid."""

    asset: str
    derived_from: NotRequired[str]
    transform: NotRequired[Transform]
    resampling_method: NotRequired[str]


class MultiscalesAttrs(TypedDict):
    """Multiscale pyramid layout and metadata."""

    layout: list[LayoutObject]
    resampling_method: NotRequired[str]


class MultiscalesConventionAttrs(TypedDict):
    """Attributes dict containing multiscales convention metadata."""

    zarr_conventions: list[ConventionMetadataObject]
    multiscales: MultiscalesAttrs


UUID: Final = "d35379db-88df-4056-af3a-620245f8e347"
SCHEMA_URL: Final = "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v1/schema.json"
SPEC_URL: Final = "https://github.com/zarr-conventions/multiscales/blob/v1/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "multiscales",
    "description": "Multiscale layout of zarr datasets",
}

CONVENTION_KEYS: Final = {"multiscales"}


def create(
    *,
    layout: list[LayoutObject],
    resampling_method: str | None = None,
) -> MultiscalesAttrs:
    """Create a ``MultiscalesAttrs`` dict from keyword arguments."""
    result = MultiscalesAttrs(layout=layout)
    if resampling_method is not None:
        result["resampling_method"] = resampling_method
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: MultiscalesAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert multiscales convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, {"multiscales": dict(data)}, overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], MultiscalesAttrs]:
    """Extract multiscales convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    if not convention_data:
        return remaining, MultiscalesAttrs(layout=[])
    if "multiscales" not in convention_data:
        msg = "Extracted convention data does not contain 'multiscales' key"
        raise KeyError(msg)
    return remaining, MultiscalesAttrs(**convention_data["multiscales"])  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> MultiscalesAttrs:
    """Validate multiscales convention data.

    ``layout`` must have at least one item, and each layout entry
    that has ``derived_from`` must also have ``transform``.
    """
    if "layout" not in data:
        msg = "'layout' is required"
        raise ValueError(msg)

    if len(data["layout"]) < 1:
        msg = "'layout' must have at least one item"
        raise ValueError(msg)

    for i, entry in enumerate(data["layout"]):
        if "derived_from" in entry and "transform" not in entry:
            msg = f"layout[{i}] has 'derived_from' but is missing 'transform'"
            raise ValueError(msg)
    return data  # type: ignore[return-value]
