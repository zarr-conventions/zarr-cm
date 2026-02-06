from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zarr_cm import geo_proj
from zarr_cm.geo_proj import CMO, GeoProjAttrs

from conftest import wrap_attrs

SCHEMA_PATH = Path(__file__).parent / "schemas" / "geo-proj.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def test_insert_geo_proj_code() -> None:
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    result = geo_proj.insert({}, data)
    assert result["proj:code"] == "EPSG:4326"
    assert result["zarr_conventions"] == [CMO]


def test_insert_geo_proj_wkt2() -> None:
    data: GeoProjAttrs = {"proj:wkt2": 'GEOGCS["WGS 84"]'}
    result = geo_proj.insert({}, data)
    assert result["proj:wkt2"] == 'GEOGCS["WGS 84"]'


def test_insert_preserves_existing_attrs() -> None:
    attrs = {"foo": "bar"}
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    result = geo_proj.insert(attrs, data)
    assert result["foo"] == "bar"
    assert result["proj:code"] == "EPSG:4326"


def test_insert_appends_to_existing_conventions() -> None:
    attrs = {"zarr_conventions": [{"uuid": "other-uuid"}]}
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    result = geo_proj.insert(attrs, data)
    assert len(result["zarr_conventions"]) == 2
    assert result["zarr_conventions"][0] == {"uuid": "other-uuid"}
    assert result["zarr_conventions"][1] == CMO


def test_extract_geo_proj() -> None:
    attrs = {
        "proj:code": "EPSG:4326",
        "foo": "bar",
        "zarr_conventions": [CMO],
    }
    remaining, data = geo_proj.extract(attrs)
    assert data == {"proj:code": "EPSG:4326"}
    assert remaining == {"foo": "bar"}
    assert "zarr_conventions" not in remaining
    assert "proj:code" not in remaining


def test_extract_preserves_other_conventions() -> None:
    other_cmo = {"uuid": "other-uuid"}
    attrs = {
        "proj:code": "EPSG:4326",
        "zarr_conventions": [other_cmo, CMO],
    }
    remaining, data = geo_proj.extract(attrs)
    assert remaining["zarr_conventions"] == [other_cmo]
    assert data == {"proj:code": "EPSG:4326"}


def test_roundtrip() -> None:
    original_attrs = {"foo": "bar"}
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    inserted = geo_proj.insert(original_attrs, data)
    remaining, extracted = geo_proj.extract(inserted)
    assert remaining == original_attrs
    assert extracted == data


def test_schema_validation_proj_code() -> None:
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    result = geo_proj.insert({}, data)
    node = wrap_attrs(result)
    jsonschema.validate(node, SCHEMA)


def test_schema_validation_proj_wkt2() -> None:
    data: GeoProjAttrs = {"proj:wkt2": 'GEOGCS["WGS 84"]'}
    result = geo_proj.insert({}, data)
    node = wrap_attrs(result)
    jsonschema.validate(node, SCHEMA)


def test_insert_idempotent() -> None:
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    once = geo_proj.insert({}, data)
    twice = geo_proj.insert(once, data, overwrite=True)
    assert once == twice


def test_validate_valid() -> None:
    result = geo_proj.validate({"proj:code": "EPSG:4326"})
    assert result == {"proj:code": "EPSG:4326"}


def test_validate_empty() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        geo_proj.validate({})  # type: ignore[typeddict-item]


def test_validate_multiple() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        geo_proj.validate({"proj:code": "EPSG:4326", "proj:wkt2": "..."})


def test_create_code() -> None:
    result = geo_proj.create(code="EPSG:4326")
    assert result == {"proj:code": "EPSG:4326"}


def test_create_wkt2() -> None:
    result = geo_proj.create(wkt2='GEOGCS["WGS 84"]')
    assert result == {"proj:wkt2": 'GEOGCS["WGS 84"]'}


def test_create_projjson() -> None:
    pj = {"type": "GeographicCRS"}
    result = geo_proj.create(projjson=pj)
    assert result == {"proj:projjson": pj}


def test_create_empty() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        geo_proj.create()


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, data = geo_proj.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert data == {}


def test_insert_collision_raises() -> None:
    attrs = {"proj:code": "EPSG:3857"}
    data: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    with pytest.raises(ValueError, match="overwritten"):
        geo_proj.insert(attrs, data)
