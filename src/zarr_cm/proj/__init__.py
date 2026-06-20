"""proj convention: https://github.com/zarr-conventions/proj

Formerly known as geo-proj. ``r1`` is the original draft kept verbatim with
its historical URLs so existing documents round-trip correctly. The
package-level functions dispatch by a keyword-only ``revision`` argument and
default to the latest revision for writes / auto-detect for reads.
"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, TypeAlias

from zarr_cm._core import JsonDict, JsonValue, detect_revision, resolve_revision_label

from . import _r1, _r2, _r3

if TYPE_CHECKING:
    from collections.abc import Mapping

# Re-export the latest revision's public types/constants at package level.
# Listed in __all__ so they count as explicit public re-exports without the
# ``X as X`` idiom.
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


class _RevisionModule(NamedTuple):
    SCHEMA_URL: str
    create: typing.Callable[..., typing.Mapping[str, JsonValue]]
    insert: typing.Callable[..., JsonDict]
    validate: typing.Callable[..., typing.Mapping[str, JsonValue]]
    extract: typing.Callable[..., tuple[JsonDict, typing.Mapping[str, JsonValue]]]


_REVISIONS: Final[dict[str, _RevisionModule]] = {
    "r1": _RevisionModule(
        _r1.SCHEMA_URL, _r1.create, _r1.insert, _r1.validate, _r1.extract
    ),
    "r2": _RevisionModule(
        _r2.SCHEMA_URL, _r2.create, _r2.insert, _r2.validate, _r2.extract
    ),
    "r3": _RevisionModule(
        _r3.SCHEMA_URL, _r3.create, _r3.insert, _r3.validate, _r3.extract
    ),
}
LATEST: Final = "r3"

# public per-revision namespaces
r1 = _r1
r2 = _r2
r3 = _r3

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: Mapping[str, JsonValue], revision: str | None) -> str:
    if revision is not None:
        return revision
    return detect_revision(attrs, UUID, _SCHEMA_URL_BY_REVISION) or LATEST


def detect(attrs: Mapping[str, JsonValue]) -> str | None:
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
    return dict(_revision(revision).create(*args, **kwargs))


@typing.overload
def insert(
    attrs: Mapping[str, JsonValue],
    data: GeoProjAttrsR3,
    *,
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JsonValue],
    data: GeoProjAttrsR1,
    *,
    revision: Literal["r1"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JsonValue],
    data: GeoProjAttrsR2,
    *,
    revision: Literal["r2"],
    overwrite: bool = False,
) -> JsonDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JsonValue],
    data: GeoProjAttrsR3,
    *,
    revision: Literal["r3"],
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


@typing.overload
def validate(
    data: Mapping[str, JsonValue], *, revision: Literal["r1"]
) -> GeoProjAttrsR1: ...


@typing.overload
def validate(
    data: Mapping[str, JsonValue], *, revision: Literal["r2"]
) -> GeoProjAttrsR2: ...


@typing.overload
def validate(
    data: Mapping[str, JsonValue], *, revision: Literal["r3"]
) -> GeoProjAttrsR3: ...


@typing.overload
def validate(
    data: Mapping[str, JsonValue], *, revision: str | None = None
) -> GeoProjAttrsR1 | GeoProjAttrsR2 | GeoProjAttrsR3: ...


def validate(data: Mapping[str, JsonValue], *, revision: str | None = None) -> object:
    return dict(_revision(_resolve_read_revision(data, revision)).validate(data))


@typing.overload
def extract(
    attrs: Mapping[str, JsonValue], *, revision: Literal["r1"]
) -> tuple[JsonDict, GeoProjAttrsR1]: ...


@typing.overload
def extract(
    attrs: Mapping[str, JsonValue], *, revision: Literal["r2"]
) -> tuple[JsonDict, GeoProjAttrsR2]: ...


@typing.overload
def extract(
    attrs: Mapping[str, JsonValue], *, revision: Literal["r3"]
) -> tuple[JsonDict, GeoProjAttrsR3]: ...


@typing.overload
def extract(
    attrs: Mapping[str, JsonValue],
    *,
    revision: str | None = None,
) -> tuple[JsonDict, GeoProjAttrsR1 | GeoProjAttrsR2 | GeoProjAttrsR3]: ...


def extract(
    attrs: Mapping[str, JsonValue], *, revision: str | None = None
) -> tuple[JsonDict, object]:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)
