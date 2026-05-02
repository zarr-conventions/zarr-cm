from __future__ import annotations

import pytest

from zarr_cm.pydantic import UCUMModel, UomModel


def test_construct() -> None:
    m = UomModel(ucum=UCUMModel(unit="m"))
    assert m.ucum.unit == "m"


def test_construct_from_dict_ucum() -> None:
    m = UomModel(ucum={"unit": "m"})
    assert m.ucum.unit == "m"


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
