from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zarr_cm import spatial
from zarr_cm.spatial import CMO, SpatialAttrs

from conftest import wrap_attrs

SCHEMA_PATH = Path(__file__).parent / "schemas" / "spatial.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def test_insert_spatial_2d() -> None:
    data: SpatialAttrs = {"spatial:dimensions": ["y", "x"]}
    result = spatial.insert({}, data)
    assert result["spatial:dimensions"] == ["y", "x"]
    assert result["zarr_conventions"] == [CMO]


def test_insert_spatial_3d_with_extras() -> None:
    data: SpatialAttrs = {
        "spatial:dimensions": ["z", "y", "x"],
        "spatial:bbox": [0.0, 0.0, 0.0, 100.0, 100.0, 50.0],
        "spatial:transform_type": "affine",
        "spatial:transform": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        "spatial:shape": [50, 100, 100],
        "spatial:registration": "pixel",
    }
    result = spatial.insert({}, data)
    assert result["spatial:dimensions"] == ["z", "y", "x"]
    assert result["spatial:registration"] == "pixel"


def test_insert_preserves_existing_attrs() -> None:
    attrs = {"foo": "bar"}
    data: SpatialAttrs = {"spatial:dimensions": ["y", "x"]}
    result = spatial.insert(attrs, data)
    assert result["foo"] == "bar"
    assert result["spatial:dimensions"] == ["y", "x"]


def test_insert_appends_to_existing_conventions() -> None:
    attrs = {"zarr_conventions": [{"uuid": "other-uuid"}]}
    data: SpatialAttrs = {"spatial:dimensions": ["y", "x"]}
    result = spatial.insert(attrs, data)
    assert len(result["zarr_conventions"]) == 2


def test_extract_spatial() -> None:
    attrs = {
        "spatial:dimensions": ["y", "x"],
        "spatial:bbox": [0.0, 0.0, 1.0, 1.0],
        "foo": "bar",
        "zarr_conventions": [CMO],
    }
    remaining, data = spatial.extract(attrs)
    assert data == {
        "spatial:dimensions": ["y", "x"],
        "spatial:bbox": [0.0, 0.0, 1.0, 1.0],
    }
    assert remaining == {"foo": "bar"}


def test_extract_preserves_other_conventions() -> None:
    other_cmo = {"uuid": "other-uuid"}
    attrs = {
        "spatial:dimensions": ["y", "x"],
        "zarr_conventions": [other_cmo, CMO],
    }
    remaining, _data = spatial.extract(attrs)
    assert remaining["zarr_conventions"] == [other_cmo]


def test_roundtrip() -> None:
    original_attrs = {"foo": "bar"}
    data: SpatialAttrs = {
        "spatial:dimensions": ["y", "x"],
        "spatial:bbox": [0.0, 0.0, 1.0, 1.0],
    }
    inserted = spatial.insert(original_attrs, data)
    remaining, extracted = spatial.extract(inserted)
    assert remaining == original_attrs
    assert extracted == data


def test_schema_validation_2d() -> None:
    data: SpatialAttrs = {
        "spatial:dimensions": ["y", "x"],
        "spatial:bbox": [0.0, 0.0, 1.0, 1.0],
        "spatial:transform": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        "spatial:shape": [100, 200],
        "spatial:registration": "pixel",
    }
    result = spatial.insert({}, data)
    node = wrap_attrs(result)
    jsonschema.validate(node, SCHEMA)


def test_schema_validation_minimal() -> None:
    data: SpatialAttrs = {"spatial:dimensions": ["y", "x"]}
    result = spatial.insert({}, data)
    node = wrap_attrs(result)
    jsonschema.validate(node, SCHEMA)


def test_validate_valid() -> None:
    result = spatial.validate({"spatial:dimensions": ["y", "x"]})
    assert result == {"spatial:dimensions": ["y", "x"]}


def test_validate_missing_dimensions() -> None:
    with pytest.raises(ValueError, match="spatial:dimensions"):
        spatial.validate({})  # type: ignore[typeddict-item]


def test_validate_bad_dimensions_length() -> None:
    with pytest.raises(ValueError, match="2 or 3"):
        spatial.validate({"spatial:dimensions": ["x"]})


def test_validate_bad_bbox_length() -> None:
    with pytest.raises(ValueError, match="4 or 6"):
        spatial.validate({"spatial:dimensions": ["y", "x"], "spatial:bbox": [0.0, 1.0]})


def test_validate_bad_registration() -> None:
    with pytest.raises(ValueError, match="spatial:registration"):
        spatial.validate({"spatial:dimensions": ["y", "x"], "spatial:registration": "bad"})


def test_create_minimal() -> None:
    result = spatial.create(dimensions=["y", "x"])
    assert result == {"spatial:dimensions": ["y", "x"]}


def test_create_full() -> None:
    result = spatial.create(
        dimensions=["y", "x"],
        bbox=[0.0, 0.0, 1.0, 1.0],
        transform_type="affine",
        transform=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        shape=[100, 200],
        registration="pixel",
    )
    assert result["spatial:dimensions"] == ["y", "x"]
    assert result["spatial:bbox"] == [0.0, 0.0, 1.0, 1.0]
    assert result["spatial:registration"] == "pixel"


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, data = spatial.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert data == {}


def test_insert_collision_raises() -> None:
    attrs = {"spatial:dimensions": ["z", "y", "x"]}
    data: SpatialAttrs = {"spatial:dimensions": ["y", "x"]}
    with pytest.raises(ValueError, match="overwritten"):
        spatial.insert(attrs, data)


def test_insert_idempotent() -> None:
    data: SpatialAttrs = {"spatial:dimensions": ["y", "x"]}
    once = spatial.insert({}, data)
    twice = spatial.insert(once, data, overwrite=True)
    assert once == twice
