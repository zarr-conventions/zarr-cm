"""Boundary contracts that casts and ordinary dict fixtures cannot prove."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Protocol, get_type_hints

import pytest

import zarr_cm
import zarr_cm._core as core
from zarr_cm import multiscales, proj, spatial, uom
from zarr_cm._core import JSONValue, validate_json_object

if TYPE_CHECKING:
    from collections.abc import Mapping

    from zarr_metadata import ZarrV3GroupMetadataJSON


class _RevisionedModule(Protocol):
    def validate(self, data: Mapping[str, JSONValue]) -> object: ...

    def extract(self, attrs: Mapping[str, JSONValue]) -> object: ...


def test_public_validator_annotations_resolve_at_runtime() -> None:
    """Public aliases and signatures remain usable by runtime frameworks."""
    assert not isinstance(zarr_cm.ArrayMetadataInput, str)
    assert not isinstance(zarr_cm.GroupMetadataInput, str)
    assert not isinstance(zarr_cm.NodeMetadataInput, str)

    for module in (spatial, proj, multiscales, zarr_cm.license_, uom):
        for name in (
            "validate_group_metadata",
            "validate_array_metadata",
            "validate_node_metadata",
        ):
            assert get_type_hints(getattr(module, name))


def test_mapping_attributes_are_normalized_without_mutating_input() -> None:
    attrs: Mapping[str, JSONValue] = MappingProxyType(
        validate_json_object(spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0]))
    )
    node: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": attrs,
    }

    validated = spatial.validate_group_metadata(node)

    assert validated == node
    assert validated is not node
    assert isinstance(validated["attributes"], dict)
    assert isinstance(node["attributes"], MappingProxyType)


def test_nested_uom_mappings_are_normalized_in_returned_document() -> None:
    ucum: Mapping[str, JSONValue] = MappingProxyType({"unit": "m"})
    uom_data: Mapping[str, JSONValue] = MappingProxyType({"ucum": ucum})
    attrs: Mapping[str, JSONValue] = MappingProxyType(
        {"zarr_conventions": [uom.CMO], "uom": uom_data}
    )
    node: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": attrs,
    }

    validated = uom.validate_group_metadata(node)

    assert isinstance(validated["attributes"]["uom"], dict)
    assert isinstance(validated["attributes"]["uom"]["ucum"], dict)
    assert isinstance(ucum, MappingProxyType)


def test_nested_multiscales_mappings_are_normalized_in_returned_document() -> None:
    layout: Mapping[str, JSONValue] = MappingProxyType({"asset": "0"})
    data: Mapping[str, JSONValue] = MappingProxyType({"layout": [layout]})
    attrs: Mapping[str, JSONValue] = MappingProxyType(
        {"zarr_conventions": [multiscales.CMO], "multiscales": data}
    )
    node: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": attrs,
    }

    validated = multiscales.validate_group_metadata(node)

    entry = validated["attributes"]["multiscales"]["layout"][0]
    assert isinstance(entry, dict)
    assert isinstance(layout, MappingProxyType)


def _with_unknown_schema(attrs: Mapping[str, JSONValue]) -> core.JSONDict:
    result = validate_json_object(attrs)
    conventions = result["zarr_conventions"]
    assert isinstance(conventions, list)
    declaration = conventions[0]
    assert isinstance(declaration, dict)
    normalized_declaration = validate_json_object(declaration)
    normalized_declaration["schema_url"] = "https://example.com/future-schema.json"
    result["zarr_conventions"] = [normalized_declaration]
    return result


@pytest.mark.parametrize(
    ("module", "attrs"),
    [
        (spatial, spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0])),
        (proj, proj.create_convention_attrs(code="EPSG:4326")),
        (multiscales, multiscales.create_convention_attrs(layout=({"asset": "0"},))),
    ],
)
def test_unknown_declared_revision_is_never_treated_as_latest(
    module: _RevisionedModule, attrs: Mapping[str, JSONValue]
) -> None:
    unknown = _with_unknown_schema(attrs)

    with pytest.raises(ValueError, match="unsupported schema_url"):
        module.validate(unknown)
    with pytest.raises(ValueError, match="unsupported schema_url"):
        module.extract(unknown)
    with pytest.raises(ValueError, match="unsupported schema_url"):
        zarr_cm.validate_all(unknown)


def test_core_documentation_exports_only_supported_names() -> None:
    assert "NodeContext" not in core.__all__
    assert "prepare_node" not in core.__all__
    assert "node_convention_data" not in core.__all__
    assert "resolve_context_revision" not in core.__all__


def test_docstrings_use_markdown_code_spans() -> None:
    project_root = Path(__file__).parents[1]
    source_roots = (project_root / "src" / "zarr_cm", project_root / "examples")
    rst_code_span = "`" * 2
    offenders: list[str] = []
    for source_root in source_roots:
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef):
                    continue
                docstring = ast.get_docstring(node, clean=False)
                if docstring is not None and rst_code_span in docstring:
                    lineno = 1 if isinstance(node, ast.Module) else node.lineno
                    offenders.append(f"{path.relative_to(project_root)}:{lineno}")
    assert offenders == []


def test_public_core_aliases_have_runtime_metadata() -> None:
    assert inspect.isclass(zarr_cm.ArrayMetadata)
    assert inspect.isclass(zarr_cm.GroupMetadata)
    assert hasattr(zarr_cm.Metadata, "__type_params__")
