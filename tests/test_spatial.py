from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from conftest import as_sequence, wrap_attrs

from zarr_cm import spatial
from zarr_cm.spatial import CMO, SpatialAttrs
from zarr_cm.spatial import r1 as spatial_r1
from zarr_cm.spatial import r2 as spatial_r2
from zarr_cm.spatial import r3 as spatial_r3

SCHEMA_PATH = Path(__file__).parent / "schemas" / "spatial.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())

R2_SCHEMA_PATH = Path(__file__).parent / "schemas" / "spatial-r2.json"
R2_SCHEMA = json.loads(R2_SCHEMA_PATH.read_text())


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
    assert len(as_sequence(result["zarr_conventions"])) == 2


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
        spatial.validate({})


def test_validate_bad_dimensions_length() -> None:
    with pytest.raises(ValueError, match="exactly 2"):
        spatial.validate({"spatial:dimensions": ["x"]})


def test_validate_bad_bbox_length() -> None:
    with pytest.raises(ValueError, match="exactly 4"):
        spatial.validate({"spatial:dimensions": ["y", "x"], "spatial:bbox": [0.0, 1.0]})


def test_validate_bad_registration() -> None:
    with pytest.raises(ValueError, match="spatial:registration"):
        spatial.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:registration": "bad"}
        )


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
    assert result.get("spatial:bbox") == [0.0, 0.0, 1.0, 1.0]
    assert result.get("spatial:registration") == "pixel"


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


def test_r2_accepts_2d() -> None:
    result = spatial_r2.validate({"spatial:dimensions": ["y", "x"]})
    assert result == {"spatial:dimensions": ["y", "x"]}


def test_r2_rejects_3d_dimensions() -> None:
    with pytest.raises(ValueError, match="exactly 2"):
        spatial_r2.validate({"spatial:dimensions": ["z", "y", "x"]})


def test_r2_rejects_6_element_bbox() -> None:
    with pytest.raises(ValueError, match="exactly 4"):
        spatial_r2.validate(
            {
                "spatial:dimensions": ["y", "x"],
                "spatial:bbox": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            }
        )


def test_r2_rejects_nonpositive_shape_item() -> None:
    with pytest.raises(ValueError, match="positive"):
        spatial_r2.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:shape": [0, 10]}
        )


def test_r2_schema_url_pinned_to_commit() -> None:
    assert "f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a" in spatial_r2.SCHEMA_URL
    assert "refs/tags/v1" not in spatial_r2.SCHEMA_URL


def test_r1_still_accepts_3d() -> None:
    result = spatial_r1.validate({"spatial:dimensions": ["z", "y", "x"]})
    assert result == {"spatial:dimensions": ["z", "y", "x"]}


def test_r2_create_validates_against_vendored_schema() -> None:
    # This asserts our r2 output conforms to the r2 'spatial:' DATA shape (the
    # strict-2D field constraints). Note the vendored schema does not actually
    # constrain our CMO: it pins conventionMetadata fields to const v1 values
    # that our commit-pinned CMO does not match, but the schema's `attributes`
    # subschema carries a sibling `$ref` next to its `contains`, so under
    # draft-07 the convention-metadata check is effectively not enforced here.
    data = spatial_r2.create(
        dimensions=["y", "x"],
        bbox=[0.0, 0.0, 1.0, 1.0],
        transform=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        shape=[100, 200],
        registration="pixel",
    )
    node = wrap_attrs(spatial_r2.insert({}, data))
    jsonschema.validate(node, R2_SCHEMA)


def test_r3_schema_url_pinned_to_v0_1() -> None:
    assert "54d81b7ced0376e63ee10f34db31db7d08dcc28d" in spatial_r3.SCHEMA_URL
    assert "refs/tags/v1" not in spatial_r3.SCHEMA_URL
    assert "refs/tags/v0.1" not in spatial_r3.SCHEMA_URL  # we pin to the commit SHA


def test_r3_same_shape_as_r2() -> None:
    assert spatial_r3.validate({"spatial:dimensions": ["y", "x"]}) == {
        "spatial:dimensions": ["y", "x"]
    }
    with pytest.raises(ValueError, match="exactly 2"):
        spatial_r3.validate({"spatial:dimensions": ["z", "y", "x"]})


def test_spatial_latest_is_r3() -> None:
    assert spatial.LATEST == "r3"
    assert (
        spatial.detect(spatial.insert({}, spatial.create(dimensions=["y", "x"])))
        == "r3"
    )


R3_SCHEMA_PATH = Path(__file__).parent / "schemas" / "spatial-r3.json"
R3_SCHEMA = json.loads(R3_SCHEMA_PATH.read_text())


def test_r3_create_validates_against_vendored_schema() -> None:
    # As with the r2 fixture test: the vendored v0.1 schema does not actually
    # constrain our commit-pinned CMO (contains/$ref); this asserts the spatial:
    # DATA shape, which is unchanged at v0.1.
    data = spatial_r3.create(
        dimensions=["y", "x"],
        bbox=[0.0, 0.0, 1.0, 1.0],
        transform=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        shape=[100, 200],
        registration="pixel",
    )
    node = wrap_attrs(spatial_r3.insert({}, data))
    jsonschema.validate(node, R3_SCHEMA)


# ---------------------------------------------------------------------------
# validate() rejection paths, per revision (error-branch coverage)
# ---------------------------------------------------------------------------


def test_r1_validate_missing_dimensions() -> None:
    with pytest.raises(ValueError, match="'spatial:dimensions' is required"):
        spatial_r1.validate({})


def test_r1_validate_non_array_bbox() -> None:
    with pytest.raises(ValueError, match="must be an array"):
        spatial_r1.validate({"spatial:dimensions": ["y", "x"], "spatial:bbox": "nope"})


def test_r1_validate_wrong_length_dimensions() -> None:
    with pytest.raises(ValueError, match="must have 2 or 3 items"):
        spatial_r1.validate({"spatial:dimensions": ["w", "z", "y", "x"]})


def test_r1_validate_bad_registration() -> None:
    with pytest.raises(ValueError, match="spatial:registration"):
        spatial_r1.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:registration": "bad"}
        )


def test_r2_validate_missing_dimensions() -> None:
    with pytest.raises(ValueError, match="'spatial:dimensions' is required"):
        spatial_r2.validate({})


def test_r2_validate_non_array_bbox() -> None:
    with pytest.raises(ValueError, match="must be an array with exactly"):
        spatial_r2.validate({"spatial:dimensions": ["y", "x"], "spatial:bbox": "nope"})


def test_r2_validate_non_int_shape_item() -> None:
    with pytest.raises(TypeError, match="items must be integers"):
        spatial_r2.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:shape": [1.5, 2]}
        )


def test_r2_validate_non_array_shape() -> None:
    # spatial:shape passes the _VALID_LENGTHS loop (it is in the loop), so a
    # non-array value is rejected there before the dedicated shape block. Use a
    # value that is not a list/tuple to hit the ValueError in the loop.
    with pytest.raises(ValueError, match="must be an array with exactly"):
        spatial_r2.validate({"spatial:dimensions": ["y", "x"], "spatial:shape": 5})


def test_r2_validate_negative_shape_item() -> None:
    with pytest.raises(ValueError, match="positive"):
        spatial_r2.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:shape": (-1, 1)}
        )


def test_r2_validate_bad_registration() -> None:
    with pytest.raises(ValueError, match="spatial:registration"):
        spatial_r2.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:registration": "bad"}
        )


def test_r3_validate_non_array_bbox() -> None:
    with pytest.raises(ValueError, match="must be an array with exactly"):
        spatial_r3.validate({"spatial:dimensions": ["y", "x"], "spatial:bbox": "nope"})


def test_r3_validate_non_int_shape_item() -> None:
    with pytest.raises(TypeError, match="items must be integers"):
        spatial_r3.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:shape": [1.5, 2]}
        )


def test_r3_validate_negative_shape_item() -> None:
    with pytest.raises(ValueError, match="positive"):
        spatial_r3.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:shape": (-1, 1)}
        )


def test_r3_validate_bad_registration() -> None:
    with pytest.raises(ValueError, match="spatial:registration"):
        spatial_r3.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:registration": "bad"}
        )


def test_spatial_unknown_revision_label() -> None:
    with pytest.raises(ValueError, match="Unknown revision"):
        spatial.create(dimensions=["y", "x"], revision="bogus")
