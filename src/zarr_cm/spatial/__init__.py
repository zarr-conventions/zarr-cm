"""spatial convention: https://github.com/zarr-conventions/spatial

Exposes revisions of the spatial convention. ``r1`` is the original
2D-or-3D draft; later revisions track upstream changes. The package-level
functions dispatch by a keyword-only ``revision`` argument and default to
the latest revision for writes / auto-detect for reads.
"""

from __future__ import annotations

import typing
from typing import Any, Final, cast

from zarr_cm._core import detect_revision, resolve_revision_label

from . import _r1, _r2, _r3

if typing.TYPE_CHECKING:
    import types

# Re-export the latest revision's public types/constants at package level.
# Listed in __all__ so they count as explicit re-exports under mypy's
# --no-implicit-reexport (strict mode) without the ``X as X`` idiom.
from ._r3 import (
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    SpatialAttrs,
    SpatialConventionAttrs,
)

__all__ = [
    "CMO",
    "CONVENTION_KEYS",
    "LATEST",
    "SCHEMA_URL",
    "SPEC_URL",
    "UUID",
    "SpatialAttrs",
    "SpatialConventionAttrs",
    "create",
    "detect",
    "extract",
    "insert",
    "r1",
    "r2",
    "r3",
    "validate",
]

_REVISIONS: Final[dict[str, types.ModuleType]] = {"r1": _r1, "r2": _r2, "r3": _r3}
LATEST: Final = "r3"

# public per-revision namespaces
r1 = _r1
r2 = _r2
r3 = _r3

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: dict[str, Any], revision: str | None) -> str:
    if revision is not None:
        return revision
    return detect_revision(attrs, UUID, _SCHEMA_URL_BY_REVISION) or LATEST


def detect(attrs: dict[str, Any]) -> str | None:
    """Return the revision label this document claims for the spatial convention.

    Returns the label (e.g. ``"r1"``/``"r2"``), or ``None`` if the convention is
    present but at an unrecognized revision. Raises ``ValueError`` if the spatial
    convention is absent from *attrs*.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "spatial")


def _revision(label: str) -> Any:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


def create(*args: Any, revision: str = LATEST, **kwargs: Any) -> Any:
    return _revision(revision).create(*args, **kwargs)


def insert(
    attrs: dict[str, Any], data: Any, *, revision: str = LATEST, overwrite: bool = False
) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", _revision(revision).insert(attrs, data, overwrite=overwrite)
    )


def validate(data: dict[str, Any], *, revision: str | None = None) -> Any:
    return _revision(_resolve_read_revision(data, revision)).validate(data)


def extract(attrs: dict[str, Any], *, revision: str | None = None) -> Any:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)
