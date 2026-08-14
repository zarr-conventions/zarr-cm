"""Node-level validation: whole `zarr.json` documents, not bare attributes.

These entry points see `node_type`, so they can enforce the rules that a bare
`validate` cannot -- `multiscales` is group-only, and `spatial:dimensions`
is required on arrays but not on groups.
"""

from __future__ import annotations

from typing import Any

import pytest

from zarr_cm import license as license_
from zarr_cm import multiscales, proj, spatial, uom
from zarr_cm._core import validate_json_object

# The v3 array fields below zarr-cm never inspects; a realistic stub keeps the
# documents honest without pulling zarr-python in as a test dependency.
_ARRAY_SHELL: dict[str, Any] = {
    "zarr_format": 3,
    "node_type": "array",
    "data_type": "float64",
    "shape": [100, 200],
    "chunk_grid": {"name": "regular", "configuration": {"chunk_shape": [10, 20]}},
    "chunk_key_encoding": {"name": "default"},
    "fill_value": 0.0,
    "codecs": [{"name": "bytes"}],
}


def array_node(attrs: Any) -> Any:
    return {**_ARRAY_SHELL, "attributes": attrs}


def group_node(attrs: Any) -> Any:
    return {"zarr_format": 3, "node_type": "group", "attributes": attrs}


def _spatial_grid() -> Any:
    return spatial.create_convention_attrs(dimensions=["y", "x"])


def _spatial_footprint() -> Any:
    return spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0])


def _multiscales_attrs() -> Any:
    return multiscales.create_convention_attrs(layout=({"asset": "0"},))


def test_valid_documents_pass() -> None:
    """Reasonable node/convention combinations validate, at every layer."""
    cases: list[tuple[Any, Any]] = [
        # spatial: dimensions on an array, a bare footprint on a group
        (spatial, array_node(_spatial_grid())),
        (spatial, group_node(_spatial_grid())),
        (spatial, group_node(_spatial_footprint())),
        # proj, license and uom apply to both node types
        (proj, array_node(proj.create_convention_attrs(code="EPSG:4326"))),
        (proj, group_node(proj.create_convention_attrs(code="EPSG:4326"))),
        (license_, array_node(license_.create_convention_attrs(spdx="MIT"))),
        (license_, group_node(license_.create_convention_attrs(spdx="MIT"))),
        (uom, array_node(uom.create_convention_attrs(ucum={"unit": "m"}))),
        # multiscales is group-only
        (multiscales, group_node(_multiscales_attrs())),
    ]
    for module, node in cases:
        expected = {**node, "attributes": validate_json_object(node["attributes"])}
        assert module.validate_node_metadata(node) == expected
        if node["node_type"] == "array":
            assert module.validate_array_metadata(node) == expected
        else:
            assert module.validate_group_metadata(node) == expected


def test_spatial_array_requires_dimensions() -> None:
    node = array_node(_spatial_footprint())
    with pytest.raises(ValueError, match="required on array nodes"):
        spatial.validate_array_metadata(node)
    with pytest.raises(ValueError, match="required on array nodes"):
        spatial.validate_node_metadata(node)


def test_spatial_group_allows_missing_dimensions() -> None:
    # The regression this whole feature exists to pin: a group footprint is fine.
    node = group_node(_spatial_footprint())
    assert spatial.validate_group_metadata(node) == node


def test_multiscales_rejects_array_nodes() -> None:
    node = array_node(_multiscales_attrs())
    with pytest.raises(ValueError, match="does not apply to array nodes"):
        multiscales.validate_array_metadata(node)


def test_node_type_mismatch_rejected() -> None:
    with pytest.raises(ValueError, match="expected a 'group' metadata document"):
        spatial.validate_group_metadata(array_node(_spatial_grid()))
    with pytest.raises(ValueError, match="expected a 'array' metadata document"):
        spatial.validate_array_metadata(group_node(_spatial_grid()))


def test_undeclared_convention_rejected() -> None:
    # The message carries the convention's spec name, from its CMO ("spatial:").
    node = group_node(license_.insert({}, license_.create(spdx="MIT")))
    with pytest.raises(ValueError, match="'spatial:' convention is not declared"):
        spatial.validate_group_metadata(node)


def test_unknown_node_type_rejected() -> None:
    node: Any = {
        "zarr_format": 3,
        "node_type": "chunk",
        "attributes": _spatial_footprint(),
    }
    with pytest.raises(ValueError, match="'node_type' must be one of"):
        spatial.validate_node_metadata(node)


def test_non_v3_document_rejected() -> None:
    node: Any = {
        "zarr_format": 2,
        "node_type": "group",
        "attributes": _spatial_footprint(),
    }
    with pytest.raises(ValueError, match="zarr_format 3"):
        spatial.validate_node_metadata(node)


def test_non_object_attributes_rejected() -> None:
    # The message names the field: a document holds many objects, and the
    # generic "expected a JSON object" would not say which one was wrong.
    node: Any = {"zarr_format": 3, "node_type": "group", "attributes": []}
    with pytest.raises(TypeError, match="'attributes' must be a JSON object, got list"):
        spatial.validate_node_metadata(node)


def test_invalid_convention_data_still_rejected() -> None:
    """The node layer runs the ordinary attribute-level rules too."""
    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))
    attrs["spatial:bbox"] = [0.0, 1.0]
    with pytest.raises(ValueError, match="exactly 4"):
        spatial.validate_array_metadata(array_node(attrs))


def test_revision_can_be_pinned() -> None:
    node = group_node(
        spatial.create_convention_attrs(dimensions=["y", "x"], revision="r2")
    )
    assert spatial.validate_group_metadata(node, revision="r2") == node


def test_explicit_unknown_revision_is_rejected() -> None:
    attrs = spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0])
    attrs["zarr_conventions"] = [
        {**spatial.CMO, "schema_url": "https://example.com/unknown-schema.json"}
    ]
    with pytest.raises(ValueError, match="unsupported schema_url"):
        spatial.validate_group_metadata(group_node(attrs))


def test_narrowing_rejects_wrong_field_types() -> None:
    attrs = _spatial_grid()
    attrs["spatial:dimensions"] = [1, 2]
    with pytest.raises(TypeError, match="items must be strings"):
        spatial.validate_array_metadata(array_node(attrs))


def test_license_narrowing_rejects_wrong_field_type() -> None:
    attrs: Any = license_.create_convention_attrs(spdx="MIT")
    attrs["license"]["spdx"] = 1
    with pytest.raises(TypeError, match="'spdx' must be a string"):
        license_.validate_group_metadata(group_node(attrs))


def test_uom_narrowing_rejects_wrong_nested_field_type() -> None:
    attrs: Any = uom.create_convention_attrs(ucum={"unit": "m"})
    attrs["uom"]["ucum"]["unit"] = 1
    with pytest.raises(TypeError, match=r"'ucum\.unit' must be a string"):
        uom.validate_array_metadata(array_node(attrs))


def test_proj_narrowing_rejects_wrong_field_type() -> None:
    attrs: Any = proj.create_convention_attrs(wkt2="GEOGCRS[]")
    attrs["proj:wkt2"] = 1
    with pytest.raises(TypeError, match="'proj:wkt2' must be a string"):
        proj.validate_group_metadata(group_node(attrs))


def test_multiscales_narrowing_rejects_invalid_asset() -> None:
    attrs = multiscales.create_convention_attrs(layout=({"asset": "0"},))
    attrs["multiscales"]["layout"][0]["asset"] = "/absolute"  # type: ignore[index]
    with pytest.raises(ValueError, match="asset must be a valid relative path"):
        multiscales.validate_group_metadata(group_node(attrs))


def test_revisioned_validation_prepares_node_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original = spatial.prepare_node

    def counted(*args: Any, **kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(spatial, "prepare_node", counted)
    node = group_node(_spatial_footprint())
    assert spatial.validate_group_metadata(node) == node
    assert calls == 1
