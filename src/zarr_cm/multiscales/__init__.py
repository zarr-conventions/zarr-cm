"""multiscales convention: https://github.com/zarr-conventions/multiscales

Exposes revisions of the multiscales convention. The package-level functions
dispatch by a keyword-only `revision` argument and default to the latest
revision for writes / auto-detect for reads.

There is no `r1`. Its schema required an unpublished schema URL, so there was
no value that both resolved and satisfied the schema. The surviving revision
keeps its `r2` label because revision labels are local to this package.
"""

from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Final, NamedTuple, Never, TypeAlias

from zarr_cm._core import (
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

from . import _r2

if TYPE_CHECKING:
    from collections.abc import Mapping


# Re-export the latest revision's public types/constants at package level.
# Listed in __all__ so they count as explicit public re-exports without the
# `X as X` idiom.
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
    "create_convention_attrs",
    "detect",
    "extract",
    "insert",
    "r2",
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
}
LATEST: Final = "r2"

# public per-revision namespaces
r2 = _r2

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: Mapping[str, JSONValue], revision: str | None) -> str:
    return resolve_attributes_revision(
        attrs,
        uuid=UUID,
        schema_url_by_revision=_SCHEMA_URL_BY_REVISION,
        latest=LATEST,
        convention_name="multiscales",
        requested=revision,
    )


def detect(attrs: Mapping[str, JSONValue]) -> str | None:
    """Return the revision label this document claims for the multiscales convention.

    Returns the label (`"r2"`), or `None` if the convention is
    present but at an unrecognized revision. Raises `ValueError` if the multiscales
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
    attrs: Mapping[str, JSONValue],
    data: MultiscalesAttrsR2,
    *,
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


def validate(
    data: Mapping[str, JSONValue], *, revision: str | None = None
) -> MultiscalesAttrsR2:
    return typing.cast(
        "MultiscalesAttrsR2",
        dict(_revision(_resolve_read_revision(data, revision)).validate(data)),
    )


def extract(
    attrs: Mapping[str, JSONValue], *, revision: str | None = None
) -> tuple[JSONDict, MultiscalesAttrsR2]:
    return typing.cast(
        "tuple[JSONDict, MultiscalesAttrsR2]",
        _revision(_resolve_read_revision(attrs, revision)).extract(attrs),
    )


def validate_group_metadata(
    metadata: GroupMetadataInput, *, revision: str | None = None
) -> GroupMetadata[MultiscalesConventionAttrsR2]:
    """Validate a full v3 group metadata document against multiscales.

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
        convention_name="multiscales",
        requested=revision,
    )
    _revision(selected).validate_context(context)
    return typing.cast("GroupMetadata[MultiscalesConventionAttrsR2]", context.metadata)


def validate_array_metadata(
    metadata: ArrayMetadataInput, *, revision: str | None = None
) -> Never:
    """Reject a v3 array metadata document: multiscales is a group-only convention.

    Every revision restricts `node_type` to `"group"`, so this always raises.
    """
    context = prepare_node(metadata, expected_node_type="array")
    selected = resolve_context_revision(
        context,
        uuid=UUID,
        schema_url_by_revision=_SCHEMA_URL_BY_REVISION,
        latest=LATEST,
        convention_name="multiscales",
        requested=revision,
    )
    _revision(selected).validate_context(context)
    msg = "unreachable: every multiscales revision rejects array nodes"
    raise AssertionError(msg)


def validate_node_metadata(
    metadata: NodeMetadataInput, *, revision: str | None = None
) -> Metadata[MultiscalesConventionAttrsR2]:
    """Validate a full v3 node metadata document against multiscales.

    Dispatches on the document's `node_type` to
    `validate_array_metadata()` or `validate_group_metadata()`. Only the
    group arm can return: multiscales has no valid array form.
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
    layout: list[LayoutObjectR2] | tuple[LayoutObjectR2, ...],
    resampling_method: str | None = None,
) -> MultiscalesConventionAttrsR2: ...


@typing.overload
def create_convention_attrs(
    *,
    layout: list[LayoutObjectR2] | tuple[LayoutObjectR2, ...],
    resampling_method: str | None = None,
    revision: str,
) -> MultiscalesConventionAttrsR2: ...


def create_convention_attrs(
    *args: object, revision: str = LATEST, **kwargs: object
) -> object:
    """Create a stand-alone attributes dict carrying multiscales and nothing else.

    The result is a complete `attributes` value: the convention data from
    `create()` plus the `zarr_conventions` entry that declares it. Use
    `insert()` instead to add this convention to attributes that already
    exist -- that is what `insert` is for.
    """
    return dict(_revision(revision).create_convention_attrs(*args, **kwargs))
