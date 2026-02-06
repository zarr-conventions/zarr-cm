from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from zarr_cm import uom
from zarr_cm.uom import CMO, UomAttrs

from conftest import wrap_attrs

SCHEMA_PATH = Path(__file__).parent / "schemas" / "uom.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def test_insert_uom_with_unit() -> None:
    data: UomAttrs = {"ucum": {"unit": "kg", "version": "2.2"}}
    result = uom.insert({}, data)
    assert result["uom"]["ucum"]["unit"] == "kg"
    assert result["zarr_conventions"] == [CMO]


def test_insert_uom_minimal() -> None:
    data: UomAttrs = {"ucum": {}}
    result = uom.insert({}, data)
    assert result["uom"]["ucum"] == {}


def test_insert_uom_with_description() -> None:
    data: UomAttrs = {"ucum": {"unit": "m/s2"}, "description": "Acceleration"}
    result = uom.insert({}, data)
    assert result["uom"]["description"] == "Acceleration"


def test_insert_preserves_existing_attrs() -> None:
    attrs = {"foo": "bar"}
    data: UomAttrs = {"ucum": {"unit": "kg"}}
    result = uom.insert(attrs, data)
    assert result["foo"] == "bar"


def test_insert_appends_to_existing_conventions() -> None:
    attrs = {"zarr_conventions": [{"uuid": "other-uuid"}]}
    data: UomAttrs = {"ucum": {"unit": "kg"}}
    result = uom.insert(attrs, data)
    assert len(result["zarr_conventions"]) == 2


def test_extract_uom() -> None:
    attrs = {
        "uom": {"ucum": {"unit": "kg"}, "description": "Mass"},
        "foo": "bar",
        "zarr_conventions": [CMO],
    }
    remaining, data = uom.extract(attrs)
    assert data == {"ucum": {"unit": "kg"}, "description": "Mass"}
    assert remaining == {"foo": "bar"}


def test_extract_preserves_other_conventions() -> None:
    other_cmo = {"uuid": "other-uuid"}
    attrs = {
        "uom": {"ucum": {"unit": "kg"}},
        "zarr_conventions": [other_cmo, CMO],
    }
    remaining, _data = uom.extract(attrs)
    assert remaining["zarr_conventions"] == [other_cmo]


def test_roundtrip() -> None:
    original_attrs = {"foo": "bar"}
    data: UomAttrs = {"ucum": {"unit": "m/s2"}, "description": "Acceleration"}
    inserted = uom.insert(original_attrs, data)
    remaining, extracted = uom.extract(inserted)
    assert remaining == original_attrs
    assert extracted == data


def test_schema_validation_full() -> None:
    data: UomAttrs = {"ucum": {"unit": "kg", "version": "2.2"}, "description": "Mass"}
    result = uom.insert({}, data)
    node = wrap_attrs(result)
    jsonschema.validate(node, SCHEMA)


def test_schema_validation_minimal() -> None:
    data: UomAttrs = {"ucum": {}}
    result = uom.insert({}, data)
    node = wrap_attrs(result)
    jsonschema.validate(node, SCHEMA)


def test_create_minimal() -> None:
    result = uom.create(ucum={})
    assert result == {"ucum": {}}


def test_create_with_description() -> None:
    result = uom.create(ucum={"unit": "kg"}, description="Mass")
    assert result == {"ucum": {"unit": "kg"}, "description": "Mass"}


def test_validate_valid() -> None:
    result = uom.validate({"ucum": {"unit": "kg"}})
    assert result == {"ucum": {"unit": "kg"}}


def test_validate_missing_ucum() -> None:
    with pytest.raises(ValueError, match="'ucum' is required"):
        uom.validate({})


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, data = uom.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert data == {"ucum": {}}


def test_insert_collision_raises() -> None:
    attrs = {"uom": {"ucum": {"unit": "lb"}}}
    data: UomAttrs = {"ucum": {"unit": "kg"}}
    with pytest.raises(ValueError, match="overwritten"):
        uom.insert(attrs, data)


def test_insert_idempotent() -> None:
    data: UomAttrs = {"ucum": {"unit": "kg"}}
    once = uom.insert({}, data)
    twice = uom.insert(once, data, overwrite=True)
    assert once == twice
