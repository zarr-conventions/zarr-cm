"""multiscales convention, revision r2 (v0.1).

Snapshot of upstream at commit 9b78efa75fef0fed302d9cf880037c569354d860.
Identical in shape to r1; pins the schema/spec URLs to the v0.1 release.
"""

from __future__ import annotations

from typing import Final, NotRequired, TypedDict, cast

from zarr_cm._core import (
    ConventionMetadataObject,
    JsonDict,
    extract_convention,
    insert_convention,
)


class Transform(TypedDict):
    """Coordinate transformation with scale and translation."""

    scale: NotRequired[list[float] | tuple[float, ...]]
    translation: NotRequired[list[float] | tuple[float, ...]]


class LayoutObject(TypedDict):
    """A single resolution level in a multiscale pyramid."""

    asset: str
    derived_from: NotRequired[str]
    transform: NotRequired[Transform]
    resampling_method: NotRequired[str]


class MultiscalesAttrs(TypedDict):
    """Multiscale pyramid layout and metadata."""

    layout: list[LayoutObject] | tuple[LayoutObject, ...]
    resampling_method: NotRequired[str]


class MultiscalesConventionAttrs(TypedDict):
    """Attributes dict containing multiscales convention metadata."""

    zarr_conventions: tuple[ConventionMetadataObject, ...]
    multiscales: MultiscalesAttrs


# UUID identifies the convention *family*, not the revision; it is shared with
# r1. Revisions are distinguished by the SCHEMA_URL below, which is what
# revision detection on read matches against.
#
# Unlike spatial/proj, the multiscales v0.1 schema ENFORCES schema_url as a
# `const` equal to the refs/tags/v0.1 tag URL (its conventionMetadata has no
# escape hatch), so a document we emit must carry that exact tag URL to validate
# against the official schema. We therefore pin to the tag here rather than the
# commit SHA. The snapshot is still taken at commit _COMMIT (vendored under that
# name); _TAG is the published tag at that commit.
UUID: Final = "d35379db-88df-4056-af3a-620245f8e347"
_COMMIT: Final = "9b78efa75fef0fed302d9cf880037c569354d860"
_TAG: Final = "v0.1"
SCHEMA_URL: Final = f"https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/{_TAG}/schema.json"
SPEC_URL: Final = (
    f"https://github.com/zarr-conventions/multiscales/blob/{_TAG}/README.md"
)

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
    validate(dict(cast("JsonDict", result)))
    return result


def insert(
    attrs: JsonDict, data: MultiscalesAttrs, *, overwrite: bool = False
) -> JsonDict:
    """Insert multiscales convention metadata into an attributes dict."""
    return insert_convention(
        attrs,
        CMO,
        {"multiscales": dict(cast("JsonDict", data))},
        overwrite=overwrite,
    )


def extract(
    attrs: JsonDict,
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


def validate(data: JsonDict) -> MultiscalesAttrs:
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
