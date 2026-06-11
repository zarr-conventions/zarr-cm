"""proj convention, revision r2.

Snapshot of upstream main at commit d150edbde61b53e9d17520f6d107c9d3689e5910.
Corrects the schema/spec URLs to the zarr-conventions/proj repo and adds the
``proj:code`` authority pattern. The "exactly one of code/wkt2/projjson" rule
is unchanged from r1.
"""

from __future__ import annotations

import re
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

# UUID identifies the convention *family*, not the revision; it is shared with
# r1. Revisions are distinguished by the commit-pinned SCHEMA_URL below, which
# is what revision detection on read matches against.
UUID: Final = "f17cb550-5864-4468-aeb7-f3180cfb622f"
_COMMIT: Final = "d150edbde61b53e9d17520f6d107c9d3689e5910"
SCHEMA_URL: Final = (
    f"https://raw.githubusercontent.com/zarr-conventions/proj/{_COMMIT}/schema.json"
)
SPEC_URL: Final = f"https://github.com/zarr-conventions/proj/blob/{_COMMIT}/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "proj:",
    "description": "Coordinate reference system information for geospatial data",
}

CONVENTION_KEYS: Final = {"proj:code", "proj:wkt2", "proj:projjson"}

_CODE_PATTERN: Final = re.compile(r"^[A-Z]+:[0-9]+$")


def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: dict[str, Any] | None = None,
) -> GeoProjAttrs:
    """Create a ``GeoProjAttrs`` dict (r2) from keyword arguments."""
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
    """Insert proj (r2) convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, dict(data), overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], GeoProjAttrs]:
    """Extract proj (r2) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, GeoProjAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> GeoProjAttrs:
    """Validate proj (r2) data.

    Exactly one of ``proj:code``, ``proj:wkt2``, or ``proj:projjson`` must be
    present, and ``proj:code`` (if present) must match ``^[A-Z]+:[0-9]+$``.
    """
    present = [k for k in ("proj:code", "proj:wkt2", "proj:projjson") if k in data]
    if len(present) != 1:
        msg = f"Exactly one of 'proj:code', 'proj:wkt2', 'proj:projjson' must be present, got: {present}"
        raise ValueError(msg)
    if "proj:code" in data and not _CODE_PATTERN.match(data["proj:code"]):
        msg = f"'proj:code' must match {_CODE_PATTERN.pattern!r}, got {data['proj:code']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
