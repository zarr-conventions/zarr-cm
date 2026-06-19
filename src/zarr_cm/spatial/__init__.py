"""spatial convention: https://github.com/zarr-conventions/spatial

Exposes revisions of the spatial convention. ``r1`` is the original
2D-or-3D draft; later revisions track upstream changes. The package-level
functions dispatch by a keyword-only ``revision`` argument and default to
the latest revision for writes / auto-detect for reads.
"""

from __future__ import annotations

import typing
from typing import Final, Literal, Protocol, TypeAlias, cast

from zarr_cm._core import JsonDict, detect_revision, resolve_revision_label

from . import _r1, _r2, _r3

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

SpatialAttrsR1: TypeAlias = _r1.SpatialAttrs
SpatialAttrsR2: TypeAlias = _r2.SpatialAttrs
SpatialAttrsR3: TypeAlias = _r3.SpatialAttrs
SpatialConventionAttrsR1: TypeAlias = _r1.SpatialConventionAttrs
SpatialConventionAttrsR2: TypeAlias = _r2.SpatialConventionAttrs
SpatialConventionAttrsR3: TypeAlias = _r3.SpatialConventionAttrs

__all__ = [
    "CMO",
    "CONVENTION_KEYS",
    "LATEST",
    "SCHEMA_URL",
    "SPEC_URL",
    "UUID",
    "SpatialAttrs",
    "SpatialAttrsR1",
    "SpatialAttrsR2",
    "SpatialAttrsR3",
    "SpatialConventionAttrs",
    "SpatialConventionAttrsR1",
    "SpatialConventionAttrsR2",
    "SpatialConventionAttrsR3",
    "create",
    "detect",
    "extract",
    "insert",
    "r1",
    "r2",
    "r3",
    "validate",
]


class _RevisionModule(Protocol):
    SCHEMA_URL: str
    create: typing.Callable[..., object]
    insert: typing.Callable[..., JsonDict]
    validate: typing.Callable[..., object]
    extract: typing.Callable[..., tuple[JsonDict, object]]


_REVISIONS: Final[dict[str, _RevisionModule]] = {
    "r1": cast("_RevisionModule", _r1),
    "r2": cast("_RevisionModule", _r2),
    "r3": cast("_RevisionModule", _r3),
}
LATEST: Final = "r3"

# public per-revision namespaces
r1 = _r1
r2 = _r2
r3 = _r3

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: JsonDict, revision: str | None) -> str:
    if revision is not None:
        return revision
    return detect_revision(attrs, UUID, _SCHEMA_URL_BY_REVISION) or LATEST


def detect(attrs: JsonDict) -> str | None:
    """Return the revision label this document claims for the spatial convention.

    Returns the label (e.g. ``"r1"``/``"r2"``), or ``None`` if the convention is
    present but at an unrecognized revision. Raises ``ValueError`` if the spatial
    convention is absent from *attrs*.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "spatial")


def _revision(label: str) -> _RevisionModule:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


@typing.overload
def create(
    *,
    dimensions: tuple[str, ...],
    bbox: tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: tuple[float, ...] | None = None,
    shape: tuple[int, ...] | None = None,
    registration: str | None = None,
) -> SpatialAttrsR3: ...


@typing.overload
def create(
    *,
    dimensions: tuple[str, ...],
    bbox: tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: tuple[float, ...] | None = None,
    shape: tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r1"],
) -> SpatialAttrsR1: ...


@typing.overload
def create(
    *,
    dimensions: tuple[str, ...],
    bbox: tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: tuple[float, ...] | None = None,
    shape: tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r2"],
) -> SpatialAttrsR2: ...


@typing.overload
def create(
    *,
    dimensions: tuple[str, ...],
    bbox: tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: tuple[float, ...] | None = None,
    shape: tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r3"],
) -> SpatialAttrsR3: ...


@typing.overload
def create(
    *,
    dimensions: tuple[str, ...],
    bbox: tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: tuple[float, ...] | None = None,
    shape: tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: str,
) -> SpatialAttrsR1 | SpatialAttrsR2 | SpatialAttrsR3: ...


def create(*args: object, revision: str = LATEST, **kwargs: object) -> object:
    return dict(cast("JsonDict", _revision(revision).create(*args, **kwargs)))


@typing.overload
def insert(
    attrs: JsonDict,
    data: SpatialAttrsR3,
    *,
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: SpatialAttrsR1,
    *,
    revision: Literal["r1"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: SpatialAttrsR2,
    *,
    revision: Literal["r2"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: SpatialAttrsR3,
    *,
    revision: Literal["r3"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: JsonDict,
    *,
    revision: str,
    overwrite: bool = False,
) -> JsonDict: ...


def insert(
    attrs: JsonDict, data: object, *, revision: str = LATEST, overwrite: bool = False
) -> JsonDict:
    return _revision(revision).insert(
        attrs, cast("JsonDict", data), overwrite=overwrite
    )


@typing.overload
def validate(data: JsonDict, *, revision: Literal["r1"]) -> SpatialAttrsR1: ...


@typing.overload
def validate(data: JsonDict, *, revision: Literal["r2"]) -> SpatialAttrsR2: ...


@typing.overload
def validate(data: JsonDict, *, revision: Literal["r3"]) -> SpatialAttrsR3: ...


@typing.overload
def validate(
    data: JsonDict, *, revision: str | None = None
) -> SpatialAttrsR1 | SpatialAttrsR2 | SpatialAttrsR3: ...


def validate(data: JsonDict, *, revision: str | None = None) -> object:
    return dict(
        cast(
            "JsonDict", _revision(_resolve_read_revision(data, revision)).validate(data)
        )
    )


@typing.overload
def extract(
    attrs: JsonDict, *, revision: Literal["r1"]
) -> tuple[JsonDict, SpatialAttrsR1]: ...


@typing.overload
def extract(
    attrs: JsonDict, *, revision: Literal["r2"]
) -> tuple[JsonDict, SpatialAttrsR2]: ...


@typing.overload
def extract(
    attrs: JsonDict, *, revision: Literal["r3"]
) -> tuple[JsonDict, SpatialAttrsR3]: ...


@typing.overload
def extract(
    attrs: JsonDict,
    *,
    revision: str | None = None,
) -> tuple[JsonDict, SpatialAttrsR1 | SpatialAttrsR2 | SpatialAttrsR3]: ...


def extract(attrs: JsonDict, *, revision: str | None = None) -> tuple[JsonDict, object]:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)
