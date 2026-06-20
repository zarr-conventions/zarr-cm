"""license convention: https://github.com/clbarnes/zarr-convention-license"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NotRequired

from typing_extensions import TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    JsonDict,
    JsonValue,
    extract_convention,
    insert_convention,
    resolve_revision_label,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


class LicenseAttrs(TypedDict, extra_items=JsonValue):
    """License metadata for a Zarr node."""

    spdx: NotRequired[str]
    url: NotRequired[str]
    text: NotRequired[str]
    file: NotRequired[str]
    path: NotRequired[str]


class LicenseConventionAttrs(TypedDict, extra_items=JsonValue):
    """Attributes dict containing license convention metadata."""

    zarr_conventions: tuple[ConventionMetadataObject, ...]
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

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {"v1": SCHEMA_URL}


def detect(attrs: Mapping[str, JsonValue]) -> str | None:
    """Return the revision label this document claims for the license convention.

    License has a single revision (``"v1"``); returns it when present with the
    known schema_url, ``None`` if present with an unrecognized schema_url, and
    raises ``ValueError`` if the convention is absent.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "license")


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
    validate(result)
    return result


def insert(
    attrs: Mapping[str, JsonValue], data: LicenseAttrs, *, overwrite: bool = False
) -> JsonDict:
    """Insert license convention metadata into an attributes dict."""
    return insert_convention(
        attrs,
        CMO,
        {"license": data},
        overwrite=overwrite,
    )


def extract(
    attrs: Mapping[str, JsonValue],
) -> tuple[JsonDict, LicenseAttrs]:
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


def validate(data: Mapping[str, JsonValue]) -> LicenseAttrs:
    """Validate license convention data.

    At least one of ``spdx``, ``url``, ``text``, ``file``, or ``path``
    must be present.
    """
    if not any(k in data for k in ("spdx", "url", "text", "file", "path")):
        msg = "At least one of 'spdx', 'url', 'text', 'file', or 'path' must be present"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
