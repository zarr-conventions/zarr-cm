"""Backward-compatibility alias for the renamed ``proj`` convention package.

Upstream renamed ``geo-proj`` to ``proj``. Importing ``zarr_cm.geo_proj``
continues to work and exposes the latest ``proj`` revision's API.
"""

from __future__ import annotations

from zarr_cm.proj import (
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    GeoProjAttrs,
    GeoProjConventionAttrs,
    create,
    extract,
    insert,
    validate,
)

__all__ = [
    "CMO",
    "CONVENTION_KEYS",
    "SCHEMA_URL",
    "SPEC_URL",
    "UUID",
    "GeoProjAttrs",
    "GeoProjConventionAttrs",
    "create",
    "extract",
    "insert",
    "validate",
]
