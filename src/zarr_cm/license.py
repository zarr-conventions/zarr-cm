"""license convention: https://github.com/clbarnes/zarr-convention-license"""

from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)


class LicenseAttrs(TypedDict):
    """License metadata for a Zarr node."""

    spdx: NotRequired[str]
    url: NotRequired[str]
    text: NotRequired[str]
    file: NotRequired[str]
    path: NotRequired[str]


class LicenseConventionAttrs(TypedDict):
    """Attributes dict containing license convention metadata."""

    zarr_conventions: list[ConventionMetadataObject]
    license: LicenseAttrs


UUID: Final = "b77365e5-2b0c-4141-b917-c03b7c68e935"
SCHEMA_URL: Final = "https://raw.githubusercontent.com/clbarnes/zarr-convention-license/refs/tags/v1/schema.json"
SPEC_URL: Final = (
    "https://github.com/clbarnes/zarr-convention-license/blob/v1/README.md"
)

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "license",
    "description": "License specifier for Zarr data",
}

CONVENTION_KEYS: Final = {"license"}


def create(
    *,
    spdx: str | None = None,
    url: str | None = None,
    text: str | None = None,
    file: str | None = None,
    path: str | None = None,
) -> LicenseAttrs:
    """Create a ``LicenseAttrs`` dict from keyword arguments."""
    result = LicenseAttrs()
    if spdx is not None:
        result["spdx"] = spdx
    if url is not None:
        result["url"] = url
    if text is not None:
        result["text"] = text
    if file is not None:
        result["file"] = file
    if path is not None:
        result["path"] = path
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: LicenseAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert license convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, {"license": dict(data)}, overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], LicenseAttrs]:
    """Extract license convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    if not convention_data:
        return remaining, LicenseAttrs()
    if "license" not in convention_data:
        msg = "Extracted convention data does not contain 'license' key"
        raise KeyError(msg)
    return remaining, LicenseAttrs(**convention_data["license"])  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> LicenseAttrs:
    """Validate license convention data.

    At least one of ``spdx``, ``url``, ``text``, ``file``, or ``path``
    must be present.
    """
    if not any(k in data for k in ("spdx", "url", "text", "file", "path")):
        msg = "At least one of 'spdx', 'url', 'text', 'file', or 'path' must be present"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
