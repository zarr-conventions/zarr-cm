from __future__ import annotations

import pytest

from zarr_cm import geo_proj as _module
from zarr_cm.pydantic import GeoProjModel


def test_construct_with_code() -> None:
    m = GeoProjModel(code="EPSG:4326")
    assert m.code == "EPSG:4326"
    assert m.wkt2 is None
    assert m.projjson is None


def test_construct_by_alias() -> None:
    m = GeoProjModel(**{"proj:code": "EPSG:4326"})
    assert m.code == "EPSG:4326"


def test_to_attrs_uses_alias() -> None:
    m = GeoProjModel(code="EPSG:4326")
    assert m.to_attrs() == {"proj:code": "EPSG:4326"}


def test_validate_exactly_one_required() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        GeoProjModel()
    with pytest.raises(ValueError, match="Exactly one"):
        GeoProjModel(code="EPSG:4326", wkt2='GEOGCS["WGS 84"]')


def test_construct_with_wkt2() -> None:
    m = GeoProjModel(wkt2='GEOGCS["WGS 84"]')
    assert m.to_attrs() == {"proj:wkt2": 'GEOGCS["WGS 84"]'}


def test_construct_with_projjson() -> None:
    pj = {"type": "GeographicCRS"}
    m = GeoProjModel(projjson=pj)
    assert m.to_attrs() == {"proj:projjson": pj}


def test_round_trip_through_module() -> None:
    m = GeoProjModel(code="EPSG:4326")
    attrs = m.insert({"foo": "bar"})
    # Cross-checks the flat-key insertion path
    assert attrs["proj:code"] == "EPSG:4326"
    assert _module.CMO in attrs["zarr_conventions"]
    remaining, parsed = GeoProjModel.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert parsed == m


def test_extract_absent_returns_none() -> None:
    remaining, parsed = GeoProjModel.extract({"foo": "bar"})
    assert remaining == {"foo": "bar"}
    assert parsed is None
