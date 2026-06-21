"""multiscales convention: https://github.com/zarr-conventions/multiscales

Exposes revisions of the multiscales convention. The package-level functions
dispatch by a keyword-only ``revision`` argument and default to the latest
revision for writes / auto-detect for reads.

.. note::
    There is no ``r1``. An earlier draft existed (upstream commit 1c20751), but
    its schema ``const``-requires ``schema_url == refs/tags/v1/schema.json``,
    and that tag was never published upstream (the multiscales repo's only tag
    is ``v0.1``, which is what ``r2`` uses). So there is no ``schema_url`` value
    that both resolves and satisfies the schema's ``const`` -- the revision is
    unshippable, so it was dropped. The surviving revision keeps its ``r2``
    label (labels are package-local and never appear in emitted documents, so
    renumbering would only churn the public type names). See the project README
    for details.
"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Final, NamedTuple, TypeAlias

from zarr_cm._core import JsonDict, JsonValue, detect_revision, resolve_revision_label

from . import _r2

if TYPE_CHECKING:
    from collections.abc import Mapping

# Re-export the latest revision's public types/constants at package level.
# Listed in __all__ so they count as explicit public re-exports without the
# ``X as X`` idiom.
from ._r2 import (
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    LayoutObject,
    MultiscalesAttrs,
    MultiscalesConventionAttrs,
    Transform,
)

TransformR2: TypeAlias = _r2.Transform
LayoutObjectR2: TypeAlias = _r2.LayoutObject
MultiscalesAttrsR2: TypeAlias = _r2.MultiscalesAttrs
MultiscalesConventionAttrsR2: TypeAlias = _r2.MultiscalesConventionAttrs

__all__ = [
    "CMO",
    "CONVENTION_KEYS",
    "LATEST",
    "SCHEMA_URL",
    "SPEC_URL",
    "UUID",
    "LayoutObject",
    "LayoutObjectR2",
    "MultiscalesAttrs",
    "MultiscalesAttrsR2",
    "MultiscalesConventionAttrs",
    "MultiscalesConventionAttrsR2",
    "Transform",
    "TransformR2",
    "create",
    "detect",
    "extract",
    "insert",
    "r2",
    "validate",
]


class _RevisionModule(NamedTuple):
    SCHEMA_URL: str
    create: typing.Callable[..., typing.Mapping[str, JsonValue]]
    insert: typing.Callable[..., JsonDict]
    validate: typing.Callable[..., typing.Mapping[str, JsonValue]]
    extract: typing.Callable[..., tuple[JsonDict, typing.Mapping[str, JsonValue]]]


_REVISIONS: Final[dict[str, _RevisionModule]] = {
    "r2": _RevisionModule(
        _r2.SCHEMA_URL, _r2.create, _r2.insert, _r2.validate, _r2.extract
    ),
}
LATEST: Final = "r2"

# public per-revision namespaces
r2 = _r2

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: Mapping[str, JsonValue], revision: str | None) -> str:
    if revision is not None:
        return revision
    return detect_revision(attrs, UUID, _SCHEMA_URL_BY_REVISION) or LATEST


def detect(attrs: Mapping[str, JsonValue]) -> str | None:
    """Return the revision label this document claims for the multiscales convention.

    Returns the label (``"r2"``), or ``None`` if the convention is
    present but at an unrecognized revision. Raises ``ValueError`` if the multiscales
    convention is absent from *attrs*.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "multiscales")


def _revision(label: str) -> _RevisionModule:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


@typing.overload
def create(
    *,
    layout: list[LayoutObjectR2] | tuple[LayoutObjectR2, ...],
    resampling_method: str | None = None,
) -> MultiscalesAttrsR2: ...


@typing.overload
def create(
    *,
    layout: list[LayoutObjectR2] | tuple[LayoutObjectR2, ...],
    resampling_method: str | None = None,
    revision: str,
) -> MultiscalesAttrsR2: ...


def create(*args: object, revision: str = LATEST, **kwargs: object) -> object:
    return dict(_revision(revision).create(*args, **kwargs))


@typing.overload
def insert(
    attrs: Mapping[str, JsonValue],
    data: MultiscalesAttrsR2,
    *,
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JsonValue],
    data: Mapping[str, JsonValue],
    *,
    revision: str,
    overwrite: bool = False,
) -> JsonDict: ...


def insert(
    attrs: Mapping[str, JsonValue],
    data: Mapping[str, JsonValue],
    *,
    revision: str = LATEST,
    overwrite: bool = False,
) -> JsonDict:
    return _revision(revision).insert(attrs, data, overwrite=overwrite)


def validate(
    data: Mapping[str, JsonValue], *, revision: str | None = None
) -> MultiscalesAttrsR2:
    return typing.cast(
        "MultiscalesAttrsR2",
        dict(_revision(_resolve_read_revision(data, revision)).validate(data)),
    )


def extract(
    attrs: Mapping[str, JsonValue], *, revision: str | None = None
) -> tuple[JsonDict, MultiscalesAttrsR2]:
    return typing.cast(
        "tuple[JsonDict, MultiscalesAttrsR2]",
        _revision(_resolve_read_revision(attrs, revision)).extract(attrs),
    )
