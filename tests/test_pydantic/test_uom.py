from __future__ import annotations

import pytest

from zarr_cm.pydantic import UCUMModel, UomModel


def test_construct() -> None:
    m = UomModel(ucum=UCUMModel(unit="m"))
    assert m.ucum.unit == "m"


def test_construct_from_dict_ucum() -> None:
    m = UomModel(ucum={"unit": "m"})
    assert m.ucum.unit == "m"


def test_construct_from_string_ucum() -> None:
    m = UomModel(ucum="m")
    assert isinstance(m.ucum, UCUMModel)
    assert m.ucum.unit == "m"
    assert m.ucum.version is None


def test_string_coercion_round_trips() -> None:
    m = UomModel(ucum="m", description="length")
    attrs = m.insert({})
    remaining, parsed = UomModel.extract(attrs)
    assert remaining == {}
    assert parsed == m
    assert parsed is not None
    assert parsed.ucum.unit == "m"


def test_existing_ucum_model_form_still_works() -> None:
    m = UomModel(ucum=UCUMModel(unit="m", version="2.1"))
    assert m.ucum.unit == "m"
    assert m.ucum.version == "2.1"


def test_to_attrs_wraps_under_uom_key() -> None:
    m = UomModel(ucum=UCUMModel(unit="m", version="2.1"))
    assert m.to_attrs() == {"uom": {"ucum": {"unit": "m", "version": "2.1"}}}


def test_ucum_required() -> None:
    with pytest.raises(ValueError, match="ucum"):
        UomModel()  # type: ignore[call-arg]


def test_round_trip() -> None:
    m = UomModel(ucum=UCUMModel(unit="m"), description="length")
    attrs = m.insert({})
    remaining, parsed = UomModel.extract(attrs)
    assert remaining == {}
    assert parsed == m


def test_extract_absent_returns_none() -> None:
    _remaining, parsed = UomModel.extract({"foo": "bar"})
    assert parsed is None


def test_from_attrs_accepts_inner_form() -> None:
    m = UomModel.from_attrs({"ucum": {"unit": "m"}})
    assert m.ucum.unit == "m"


def test_from_attrs_accepts_wrapped_form() -> None:
    m = UomModel.from_attrs({"uom": {"ucum": {"unit": "m"}}})
    assert m.ucum.unit == "m"
