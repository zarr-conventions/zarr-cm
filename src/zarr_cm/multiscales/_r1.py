"""multiscales convention: https://github.com/zarr-conventions/multiscales"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NotRequired

from typing_extensions import TypedDict

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from zarr_cm._core import (
    ConventionMetadataObject,
    JsonDict,
    JsonValue,
    extract_convention,
    insert_convention,
)


class Transform(TypedDict, extra_items=JsonValue):
    """Coordinate transformation with scale and translation."""

    scale: NotRequired[Sequence[float]]
    translation: NotRequired[Sequence[float]]


class LayoutObject(TypedDict, extra_items=JsonValue):
    """A single resolution level in a multiscale pyramid."""

    asset: str
    derived_from: NotRequired[str]
    transform: NotRequired[Transform]
    resampling_method: NotRequired[str]


class MultiscalesAttrs(TypedDict, extra_items=JsonValue):
    """Multiscale pyramid layout and metadata."""

    layout: Sequence[LayoutObject]
    resampling_method: NotRequired[str]


class MultiscalesConventionAttrs(TypedDict, extra_items=JsonValue):
    """Attributes dict containing multiscales convention metadata."""

    zarr_conventions: Sequence[ConventionMetadataObject]
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
    layout: tuple[LayoutObject, ...],
    resampling_method: str | None = None,
) -> MultiscalesAttrs:
    """Create a ``MultiscalesAttrs`` dict from keyword arguments."""
    result = MultiscalesAttrs(layout=layout)
    if resampling_method is not None:
        result["resampling_method"] = resampling_method
    validate(result)
    return result


def insert(
    attrs: Mapping[str, JsonValue], data: MultiscalesAttrs, *, overwrite: bool = False
) -> JsonDict:
    """Insert multiscales convention metadata into an attributes dict."""
    return insert_convention(
        attrs,
        CMO,
        {"multiscales": data},
        overwrite=overwrite,
    )


def extract(
    attrs: Mapping[str, JsonValue],
) -> tuple[JsonDict, MultiscalesAttrs]:
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


def validate(data: Mapping[str, JsonValue]) -> MultiscalesAttrs:
    """Validate multiscales convention data.

    ``layout`` must have at least one item, and each layout entry
    that has ``derived_from`` must also have ``transform``.
    """
    if "layout" not in data:
        msg = "'layout' is required"
        raise ValueError(msg)

    layout = data["layout"]
    if not isinstance(layout, (list, tuple)):
        msg = "'layout' must be an array"
        raise TypeError(msg)

    if len(layout) < 1:
        msg = "'layout' must have at least one item"
        raise ValueError(msg)

    for i, entry in enumerate(layout):
        if not isinstance(entry, dict):
            msg = f"layout[{i}] must be an object"
            raise TypeError(msg)
        if "derived_from" in entry and "transform" not in entry:
            msg = f"layout[{i}] has 'derived_from' but is missing 'transform'"
            raise ValueError(msg)
    return data  # type: ignore[return-value]
