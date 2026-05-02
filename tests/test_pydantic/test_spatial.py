from __future__ import annotations

import pytest

from zarr_cm.pydantic import SpatialModel


def test_construct_minimal() -> None:
    m = SpatialModel(dimensions=["x", "y"])
    assert m.dimensions == ["x", "y"]
    assert m.bbox is None


def test_to_attrs_uses_aliases() -> None:
    m = SpatialModel(dimensions=["x", "y"], bbox=[0.0, 0.0, 1.0, 1.0])
    assert m.to_attrs() == {
        "spatial:dimensions": ["x", "y"],
        "spatial:bbox": [0.0, 0.0, 1.0, 1.0],
    }


def test_dimensions_required() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        SpatialModel()  # type: ignore[call-arg]


def test_bbox_length_must_be_4_or_6() -> None:
    with pytest.raises(ValueError, match="bbox"):
        SpatialModel(dimensions=["x", "y"], bbox=[0.0, 0.0, 1.0])


def test_dimensions_length_must_be_2_or_3() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        SpatialModel(dimensions=["x"])
    with pytest.raises(ValueError, match="dimensions"):
        SpatialModel(dimensions=["x", "y", "z", "t"])


def test_registration_must_be_node_or_pixel() -> None:
    with pytest.raises(ValueError, match="registration"):
        SpatialModel(dimensions=["x", "y"], registration="invalid")
    SpatialModel(dimensions=["x", "y"], registration="node")
    SpatialModel(dimensions=["x", "y"], registration="pixel")


def test_round_trip() -> None:
    m = SpatialModel(
        dimensions=["x", "y"],
        bbox=[0.0, 0.0, 1.0, 1.0],
        registration="pixel",
    )
    attrs = m.insert({})
    remaining, parsed = SpatialModel.extract(attrs)
    assert remaining == {}
    assert parsed == m


def test_extract_absent_returns_none() -> None:
    remaining, parsed = SpatialModel.extract({"foo": "bar"})
    assert remaining == {"foo": "bar"}
    assert parsed is None
