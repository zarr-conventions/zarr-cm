"""spatial convention: https://github.com/zarr-conventions/spatial

Exposes revisions of the spatial convention. The package-level functions
dispatch by a keyword-only `revision` argument and default to the latest
revision for writes / auto-detect for reads.

There is no `r1`. An earlier draft existed, but the only `schema_url` it could
carry -- upstream's `refs/tags/v1/schema.json` -- was never published. The
surviving revisions keep their `r2`/`r3` labels because those labels are local
to this package and never appear in emitted documents.
"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, TypeAlias

from zarr_cm._core import (
    ArrayMetadata,
    ArrayMetadataInput,
    GroupMetadata,
    GroupMetadataInput,
    JSONDict,
    JSONValue,
    Metadata,
    NodeMetadataInput,
    resolve_revision_label,
)
from zarr_cm._node import (
    NodeContext,
    node_type_of,
    prepare_node,
    resolve_attributes_revision,
    resolve_context_revision,
)

from . import _r2, _r3

if TYPE_CHECKING:
    from collections.abc import Mapping


# Re-export the latest revision's public types/constants at package level.
# Listed in __all__ so they count as explicit public re-exports without the
# `X as X` idiom.
from ._r3 import (
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    SpatialAttrs,
    SpatialConventionAttrs,
)

SpatialAttrsR2: TypeAlias = _r2.SpatialAttrs
SpatialAttrsR3: TypeAlias = _r3.SpatialAttrs
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
    "SpatialAttrsR2",
    "SpatialAttrsR3",
    "SpatialConventionAttrs",
    "SpatialConventionAttrsR2",
    "SpatialConventionAttrsR3",
    "create",
    "create_convention_attrs",
    "detect",
    "extract",
    "insert",
    "r2",
    "r3",
    "validate",
    "validate_array_metadata",
    "validate_group_metadata",
    "validate_node_metadata",
]


class _RevisionModule(NamedTuple):
    SCHEMA_URL: str
    create: typing.Callable[..., typing.Mapping[str, JSONValue]]
    insert: typing.Callable[..., JSONDict]
    validate: typing.Callable[..., typing.Mapping[str, JSONValue]]
    extract: typing.Callable[..., tuple[JSONDict, typing.Mapping[str, JSONValue]]]
    create_convention_attrs: typing.Callable[..., typing.Mapping[str, JSONValue]]
    validate_context: typing.Callable[[NodeContext], object]


_REVISIONS: Final[dict[str, _RevisionModule]] = {
    "r2": _RevisionModule(
        _r2.SCHEMA_URL,
        _r2.create,
        _r2.insert,
        _r2.validate,
        _r2.extract,
        _r2.create_convention_attrs,
        _r2._validate_context,  # pylint: disable=protected-access
    ),
    "r3": _RevisionModule(
        _r3.SCHEMA_URL,
        _r3.create,
        _r3.insert,
        _r3.validate,
        _r3.extract,
        _r3.create_convention_attrs,
        _r3._validate_context,  # pylint: disable=protected-access
    ),
}
LATEST: Final = "r3"

# public per-revision namespaces
r2 = _r2
r3 = _r3

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: Mapping[str, JSONValue], revision: str | None) -> str:
    return resolve_attributes_revision(
        attrs,
        uuid=UUID,
        schema_url_by_revision=_SCHEMA_URL_BY_REVISION,
        latest=LATEST,
        convention_name="spatial:",
        requested=revision,
    )


def detect(attrs: Mapping[str, JSONValue]) -> str | None:
    """Return the revision label this document claims for the spatial convention.

    Returns the label (e.g. `"r2"`/`"r3"`), or `None` if the convention is
    present but at an unrecognized revision. Raises `ValueError` if the spatial
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
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
) -> SpatialAttrsR3: ...


@typing.overload
def create(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r2"],
) -> SpatialAttrsR2: ...


@typing.overload
def create(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r3"],
) -> SpatialAttrsR3: ...


@typing.overload
def create(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: str,
) -> SpatialAttrsR2 | SpatialAttrsR3: ...


def create(*args: object, revision: str = LATEST, **kwargs: object) -> object:
    return dict(_revision(revision).create(*args, **kwargs))


@typing.overload
def insert(
    attrs: Mapping[str, JSONValue],
    data: SpatialAttrsR3,
    *,
    overwrite: bool = False,
) -> JSONDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JSONValue],
    data: SpatialAttrsR2,
    *,
    revision: Literal["r2"],
    overwrite: bool = False,
) -> JSONDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JSONValue],
    data: SpatialAttrsR3,
    *,
    revision: Literal["r3"],
    overwrite: bool = False,
) -> JSONDict: ...


@typing.overload
def insert(
    attrs: Mapping[str, JSONValue],
    data: Mapping[str, JSONValue],
    *,
    revision: str,
    overwrite: bool = False,
) -> JSONDict: ...


def insert(
    attrs: Mapping[str, JSONValue],
    data: Mapping[str, JSONValue],
    *,
    revision: str = LATEST,
    overwrite: bool = False,
) -> JSONDict:
    return _revision(revision).insert(attrs, data, overwrite=overwrite)


@typing.overload
def validate(
    data: Mapping[str, JSONValue], *, revision: Literal["r2"]
) -> SpatialAttrsR2: ...


@typing.overload
def validate(
    data: Mapping[str, JSONValue], *, revision: Literal["r3"]
) -> SpatialAttrsR3: ...


@typing.overload
def validate(
    data: Mapping[str, JSONValue], *, revision: str | None = None
) -> SpatialAttrsR2 | SpatialAttrsR3: ...


def validate(data: Mapping[str, JSONValue], *, revision: str | None = None) -> object:
    return dict(_revision(_resolve_read_revision(data, revision)).validate(data))


@typing.overload
def extract(
    attrs: Mapping[str, JSONValue], *, revision: Literal["r2"]
) -> tuple[JSONDict, SpatialAttrsR2]: ...


@typing.overload
def extract(
    attrs: Mapping[str, JSONValue], *, revision: Literal["r3"]
) -> tuple[JSONDict, SpatialAttrsR3]: ...


@typing.overload
def extract(
    attrs: Mapping[str, JSONValue],
    *,
    revision: str | None = None,
) -> tuple[JSONDict, SpatialAttrsR2 | SpatialAttrsR3]: ...


def extract(
    attrs: Mapping[str, JSONValue], *, revision: str | None = None
) -> tuple[JSONDict, object]:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)


@typing.overload
def validate_group_metadata(
    metadata: GroupMetadataInput, *, revision: Literal["r2"]
) -> GroupMetadata[SpatialConventionAttrsR2]: ...


@typing.overload
def validate_group_metadata(
    metadata: GroupMetadataInput, *, revision: Literal["r3"]
) -> GroupMetadata[SpatialConventionAttrsR3]: ...


@typing.overload
def validate_group_metadata(
    metadata: GroupMetadataInput, *, revision: str | None = None
) -> (
    GroupMetadata[SpatialConventionAttrsR2] | GroupMetadata[SpatialConventionAttrsR3]
): ...


def validate_group_metadata(
    metadata: GroupMetadataInput, *, revision: str | None = None
) -> object:
    """Validate a full v3 group metadata document against spatial.

    The revision is detected from the document's own `zarr_conventions` entry
    unless *revision* pins one. The document comes back with its `attributes`
    narrowed to the matched revision's convention type.
    """
    context = prepare_node(metadata, expected_node_type="group")
    selected = resolve_context_revision(
        context,
        uuid=UUID,
        schema_url_by_revision=_SCHEMA_URL_BY_REVISION,
        latest=LATEST,
        convention_name="spatial:",
        requested=revision,
    )
    _revision(selected).validate_context(context)
    return typing.cast(
        "GroupMetadata[SpatialConventionAttrsR2] | GroupMetadata[SpatialConventionAttrsR3]",
        context.metadata,
    )


@typing.overload
def validate_array_metadata(
    metadata: ArrayMetadataInput, *, revision: Literal["r2"]
) -> ArrayMetadata[SpatialConventionAttrsR2]: ...


@typing.overload
def validate_array_metadata(
    metadata: ArrayMetadataInput, *, revision: Literal["r3"]
) -> ArrayMetadata[SpatialConventionAttrsR3]: ...


@typing.overload
def validate_array_metadata(
    metadata: ArrayMetadataInput, *, revision: str | None = None
) -> (
    ArrayMetadata[SpatialConventionAttrsR2] | ArrayMetadata[SpatialConventionAttrsR3]
): ...


def validate_array_metadata(
    metadata: ArrayMetadataInput, *, revision: str | None = None
) -> object:
    """Validate a full v3 array metadata document against spatial.

    The revision is detected from the document's own `zarr_conventions` entry
    unless *revision* pins one. The document comes back with its `attributes`
    narrowed to the matched revision's convention type.
    """
    context = prepare_node(metadata, expected_node_type="array")
    selected = resolve_context_revision(
        context,
        uuid=UUID,
        schema_url_by_revision=_SCHEMA_URL_BY_REVISION,
        latest=LATEST,
        convention_name="spatial:",
        requested=revision,
    )
    _revision(selected).validate_context(context)
    return typing.cast(
        "ArrayMetadata[SpatialConventionAttrsR2] | ArrayMetadata[SpatialConventionAttrsR3]",
        context.metadata,
    )


def validate_node_metadata(
    metadata: NodeMetadataInput, *, revision: str | None = None
) -> Metadata[SpatialConventionAttrsR2] | Metadata[SpatialConventionAttrsR3]:
    """Validate a full v3 node metadata document against spatial.

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`.
    """
    if node_type_of(metadata) == "array":
        return validate_array_metadata(
            typing.cast("ArrayMetadataInput", metadata), revision=revision
        )
    return validate_group_metadata(
        typing.cast("GroupMetadataInput", metadata), revision=revision
    )


@typing.overload
def create_convention_attrs(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
) -> SpatialConventionAttrsR3: ...


@typing.overload
def create_convention_attrs(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r2"],
) -> SpatialConventionAttrsR2: ...


@typing.overload
def create_convention_attrs(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: Literal["r3"],
) -> SpatialConventionAttrsR3: ...


@typing.overload
def create_convention_attrs(
    *,
    dimensions: list[str] | tuple[str, ...] | None = None,
    bbox: list[float] | tuple[float, ...] | None = None,
    transform_type: str | None = None,
    transform: list[float] | tuple[float, ...] | None = None,
    shape: list[int] | tuple[int, ...] | None = None,
    registration: str | None = None,
    revision: str,
) -> SpatialConventionAttrsR2 | SpatialConventionAttrsR3: ...


def create_convention_attrs(
    *args: object, revision: str = LATEST, **kwargs: object
) -> object:
    """Create a stand-alone attributes dict carrying spatial and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return dict(_revision(revision).create_convention_attrs(*args, **kwargs))
