from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)

GeoProjAttrs = TypedDict(
    "GeoProjAttrs",
    {
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[dict[str, Any]],
    },
)

GeoProjConventionAttrs = TypedDict(
    "GeoProjConventionAttrs",
    {
        "zarr_conventions": list[ConventionMetadataObject],
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[dict[str, Any]],
    },
)

UUID: Final = "f17cb550-5864-4468-aeb7-f3180cfb622f"
SCHEMA_URL: Final = "https://raw.githubusercontent.com/zarr-experimental/geo-proj/refs/tags/v1/schema.json"
SPEC_URL: Final = "https://github.com/zarr-experimental/geo-proj/blob/v1/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "proj:",
    "description": "Coordinate reference system information for geospatial data",
}

CONVENTION_KEYS: Final = {"proj:code", "proj:wkt2", "proj:projjson"}


def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: dict[str, Any] | None = None,
) -> GeoProjAttrs:
    """Create a ``GeoProjAttrs`` dict from keyword arguments."""
    result = GeoProjAttrs()
    if code is not None:
        result["proj:code"] = code
    if wkt2 is not None:
        result["proj:wkt2"] = wkt2
    if projjson is not None:
        result["proj:projjson"] = projjson
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: GeoProjAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert geo-proj convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, dict(data), overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], GeoProjAttrs]:
    """Extract geo-proj convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, GeoProjAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> GeoProjAttrs:
    """Validate geo-proj convention data.

    Exactly one of ``proj:code``, ``proj:wkt2``, or ``proj:projjson``
    must be present.
    """
    present = [k for k in ("proj:code", "proj:wkt2", "proj:projjson") if k in data]
    if len(present) != 1:
        msg = f"Exactly one of 'proj:code', 'proj:wkt2', 'proj:projjson' must be present, got: {present}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
