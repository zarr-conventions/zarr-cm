"""proj convention: https://github.com/zarr-conventions/proj

Formerly known as geo-proj. ``r1`` is the original draft kept verbatim with
its historical URLs so existing documents round-trip correctly. The
package-level functions dispatch by a keyword-only ``revision`` argument and
default to the latest revision for writes / auto-detect for reads.
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
    GeoProjAttrs,
    GeoProjConventionAttrs,
)

GeoProjAttrsR1: TypeAlias = _r1.GeoProjAttrs
GeoProjAttrsR2: TypeAlias = _r2.GeoProjAttrs
GeoProjAttrsR3: TypeAlias = _r3.GeoProjAttrs
GeoProjConventionAttrsR1: TypeAlias = _r1.GeoProjConventionAttrs
GeoProjConventionAttrsR2: TypeAlias = _r2.GeoProjConventionAttrs
GeoProjConventionAttrsR3: TypeAlias = _r3.GeoProjConventionAttrs

__all__ = [
    "CMO",
    "CONVENTION_KEYS",
    "LATEST",
    "SCHEMA_URL",
    "SPEC_URL",
    "UUID",
    "GeoProjAttrs",
    "GeoProjAttrsR1",
    "GeoProjAttrsR2",
    "GeoProjAttrsR3",
    "GeoProjConventionAttrs",
    "GeoProjConventionAttrsR1",
    "GeoProjConventionAttrsR2",
    "GeoProjConventionAttrsR3",
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
    """Return the revision label this document claims for the proj convention.

    Returns the label (e.g. ``"r1"``/``"r2"``), or ``None`` if the convention is
    present but at an unrecognized revision. Raises ``ValueError`` if the proj
    convention is absent from *attrs*.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "geo-proj")


def _revision(label: str) -> _RevisionModule:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


@typing.overload
def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JsonDict | None = None,
) -> GeoProjAttrsR3: ...


@typing.overload
def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JsonDict | None = None,
    revision: Literal["r1"],
) -> GeoProjAttrsR1: ...


@typing.overload
def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JsonDict | None = None,
    revision: Literal["r2"],
) -> GeoProjAttrsR2: ...


@typing.overload
def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JsonDict | None = None,
    revision: Literal["r3"],
) -> GeoProjAttrsR3: ...


@typing.overload
def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: JsonDict | None = None,
    revision: str,
) -> GeoProjAttrsR1 | GeoProjAttrsR2 | GeoProjAttrsR3: ...


def create(*args: object, revision: str = LATEST, **kwargs: object) -> object:
    return dict(cast("JsonDict", _revision(revision).create(*args, **kwargs)))


@typing.overload
def insert(
    attrs: JsonDict,
    data: GeoProjAttrsR3,
    *,
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: GeoProjAttrsR1,
    *,
    revision: Literal["r1"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: GeoProjAttrsR2,
    *,
    revision: Literal["r2"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: JsonDict,
    data: GeoProjAttrsR3,
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
def validate(data: JsonDict, *, revision: Literal["r1"]) -> GeoProjAttrsR1: ...


@typing.overload
def validate(data: JsonDict, *, revision: Literal["r2"]) -> GeoProjAttrsR2: ...


@typing.overload
def validate(data: JsonDict, *, revision: Literal["r3"]) -> GeoProjAttrsR3: ...


@typing.overload
def validate(
    data: JsonDict, *, revision: str | None = None
) -> GeoProjAttrsR1 | GeoProjAttrsR2 | GeoProjAttrsR3: ...


def validate(data: JsonDict, *, revision: str | None = None) -> object:
    return dict(
        cast(
            "JsonDict", _revision(_resolve_read_revision(data, revision)).validate(data)
        )
    )


@typing.overload
def extract(
    attrs: JsonDict, *, revision: Literal["r1"]
) -> tuple[JsonDict, GeoProjAttrsR1]: ...


@typing.overload
def extract(
    attrs: JsonDict, *, revision: Literal["r2"]
) -> tuple[JsonDict, GeoProjAttrsR2]: ...


@typing.overload
def extract(
    attrs: JsonDict, *, revision: Literal["r3"]
) -> tuple[JsonDict, GeoProjAttrsR3]: ...


@typing.overload
def extract(
    attrs: JsonDict,
    *,
    revision: str | None = None,
) -> tuple[JsonDict, GeoProjAttrsR1 | GeoProjAttrsR2 | GeoProjAttrsR3]: ...


def extract(attrs: JsonDict, *, revision: str | None = None) -> tuple[JsonDict, object]:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)
