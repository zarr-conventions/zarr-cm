"""Internal orchestration for validating convention-bearing Zarr nodes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import NamedTuple, cast

from ._core import (
    NODE_TYPES,
    ConventionMetadataObject,
    JSONDict,
    JSONValue,
    NodeType,
    validate_convention_metadata_objects,
    validate_json_object,
)


def node_attributes(metadata: Mapping[str, object]) -> JSONDict:
    """Normalize the `attributes` object of a Zarr v3 metadata document."""
    attributes = metadata.get("attributes", {})
    if not isinstance(attributes, Mapping):
        msg = f"'attributes' must be a JSON object, got {type(attributes).__name__}"
        raise TypeError(msg)
    return validate_json_object(cast("Mapping[object, object]", attributes))


def node_type_of(
    metadata: Mapping[str, object],
    *,
    expected: NodeType | None = None,
) -> NodeType:
    """Validate and return a Zarr v3 document's `node_type`."""
    zarr_format = metadata.get("zarr_format")
    if zarr_format != 3:
        msg = f"conventions are defined for zarr_format 3, got {zarr_format!r}"
        raise ValueError(msg)

    node_type = metadata.get("node_type")
    if node_type not in NODE_TYPES:
        msg = f"'node_type' must be one of {sorted(NODE_TYPES)}, got {node_type!r}"
        raise ValueError(msg)

    if expected is not None and node_type != expected:
        msg = f"expected a {expected!r} metadata document, got node_type {node_type!r}"
        raise ValueError(msg)

    return "array" if node_type == "array" else "group"


class NodeContext(NamedTuple):
    """Convention-relevant node data, normalized and parsed once."""

    node_type: NodeType
    metadata: dict[str, object]
    attributes: JSONDict
    declarations: tuple[ConventionMetadataObject, ...]


def prepare_node(
    metadata: Mapping[str, object],
    *,
    expected_node_type: NodeType | None = None,
) -> NodeContext:
    """Normalize and parse the convention-bearing parts of a Zarr v3 document."""
    node_type = node_type_of(metadata, expected=expected_node_type)
    attributes = node_attributes(metadata)
    declarations = tuple(
        validate_convention_metadata_objects(attributes.get("zarr_conventions"))
    )
    normalized_metadata = dict(metadata)
    normalized_metadata["attributes"] = attributes
    return NodeContext(node_type, normalized_metadata, attributes, declarations)


def node_convention_data(
    context: NodeContext,
    cmo: ConventionMetadataObject,
    convention_keys: set[str],
) -> JSONDict:
    """Extract a declared convention's keys from a prepared node context."""
    uuid = cmo.get("uuid")
    declaration = next(
        (item for item in context.declarations if item.get("uuid") == uuid), None
    )
    if uuid is None or declaration is None:
        name = cmo.get("name") or uuid or "<unnamed>"
        msg = f"the {name!r} convention is not declared in this document's 'zarr_conventions'"
        raise ValueError(msg)
    declared_schema_url = declaration.get("schema_url")
    expected_schema_url = cmo.get("schema_url")
    if (
        declared_schema_url is not None
        and expected_schema_url is not None
        and declared_schema_url != expected_schema_url
    ):
        name = cmo.get("name") or uuid
        msg = (
            f"the {name!r} convention declares schema_url "
            f"{declared_schema_url!r}, not {expected_schema_url!r}"
        )
        raise ValueError(msg)
    return {
        key: value
        for key, value in context.attributes.items()
        if key in convention_keys
    }


def _select_revision(
    declaration: ConventionMetadataObject | None,
    *,
    schema_url_by_revision: Mapping[str, str],
    latest: str,
    convention_name: str,
    requested: str | None,
    declaration_required: bool,
) -> str:
    if declaration is None:
        if declaration_required:
            msg = (
                f"the {convention_name!r} convention is not declared in this "
                "document's 'zarr_conventions'"
            )
            raise ValueError(msg)
        return latest if requested is None else requested

    schema_url = declaration.get("schema_url")
    if requested is not None:
        expected_url = schema_url_by_revision.get(requested)
        if (
            schema_url is not None
            and expected_url is not None
            and schema_url != expected_url
        ):
            msg = (
                f"the {convention_name!r} convention declares schema_url "
                f"{schema_url!r}, which does not match revision {requested!r}"
            )
            raise ValueError(msg)
        return requested
    if schema_url is None:
        return latest
    by_url = {url: label for label, url in schema_url_by_revision.items()}
    try:
        return by_url[schema_url]
    except KeyError:
        msg = (
            f"the {convention_name!r} convention declares an unsupported "
            f"schema_url: {schema_url!r}"
        )
        raise ValueError(msg) from None


def resolve_attributes_revision(
    attrs: Mapping[str, JSONValue],
    *,
    uuid: str,
    schema_url_by_revision: Mapping[str, str],
    latest: str,
    convention_name: str,
    requested: str | None = None,
) -> str:
    """Resolve a revision for convention data or a complete attributes object."""
    if requested is not None:
        # Attribute-level APIs deliberately allow callers to interpret or migrate
        # data under an explicitly selected revision. Full-node validation uses
        # resolve_context_revision, which checks the declaration for consistency.
        return requested
    declaration = next(
        (
            item
            for item in validate_convention_metadata_objects(
                attrs.get("zarr_conventions")
            )
            if item.get("uuid") == uuid
        ),
        None,
    )
    return _select_revision(
        declaration,
        schema_url_by_revision=schema_url_by_revision,
        latest=latest,
        convention_name=convention_name,
        requested=requested,
        declaration_required=False,
    )


def resolve_context_revision(
    context: NodeContext,
    *,
    uuid: str,
    schema_url_by_revision: Mapping[str, str],
    latest: str,
    convention_name: str,
    requested: str | None = None,
) -> str:
    """Resolve the declared convention revision for a prepared node."""
    declaration = next(
        (item for item in context.declarations if item.get("uuid") == uuid), None
    )
    return _select_revision(
        declaration,
        schema_url_by_revision=schema_url_by_revision,
        latest=latest,
        convention_name=convention_name,
        requested=requested,
        declaration_required=True,
    )
