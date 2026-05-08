from __future__ import annotations

from typing import cast, get_args

import pytest

from zarr_cm import ConventionName
from zarr_cm.pydantic import (
    GeoProjModel,
    LayoutObjectModel,
    LicenseModel,
    MultiscalesModel,
    SpatialModel,
    UCUMModel,
    UomModel,
    build_attrs,
    parse_attrs,
)


def test_build_attrs_single() -> None:
    attrs = build_attrs(GeoProjModel(code="EPSG:4326"))
    assert attrs["proj:code"] == "EPSG:4326"
    assert len(attrs["zarr_conventions"]) == 1


def test_build_attrs_multiple() -> None:
    attrs = build_attrs(
        GeoProjModel(code="EPSG:4326"),
        LicenseModel(spdx="MIT"),
        base={"foo": "bar"},
    )
    assert attrs["foo"] == "bar"
    assert attrs["proj:code"] == "EPSG:4326"
    assert attrs["license"] == {"spdx": "MIT"}
    assert len(attrs["zarr_conventions"]) == 2


def test_build_attrs_overwrite_true_allows_collision() -> None:
    attrs = build_attrs(
        GeoProjModel(code="EPSG:4326"),
        base={"proj:code": "EPSG:3857"},
        overwrite=True,
    )
    assert attrs["proj:code"] == "EPSG:4326"


def test_build_attrs_default_collision_raises() -> None:
    with pytest.raises(ValueError, match="overwritten"):
        build_attrs(
            GeoProjModel(code="EPSG:4326"),
            base={"proj:code": "EPSG:3857"},
        )


def test_parse_attrs_returns_models_keyed_by_convention_name() -> None:
    attrs = build_attrs(
        GeoProjModel(code="EPSG:4326"),
        MultiscalesModel(layout=[LayoutObjectModel(asset="s0")]),
    )
    remaining, models = parse_attrs(attrs)
    assert remaining == {}
    assert "geo-proj" in models
    assert "multiscales" in models
    assert isinstance(models["geo-proj"], GeoProjModel)
    assert isinstance(models["multiscales"], MultiscalesModel)


def test_parse_attrs_keys_subset_of_convention_name_literal() -> None:
    valid_names = set(get_args(ConventionName))
    attrs = build_attrs(
        GeoProjModel(code="EPSG:4326"),
        LicenseModel(spdx="MIT"),
    )
    _remaining, models = parse_attrs(attrs)
    assert set(models).issubset(valid_names)


def test_parse_attrs_ignores_unknown_uuids_by_default() -> None:
    attrs = {
        "foo": "bar",
        "zarr_conventions": [{"uuid": "00000000-0000-0000-0000-000000000000"}],
    }
    remaining, models = parse_attrs(attrs)
    # Unknown UUIDs are silently ignored; remaining keeps the unknown CMO.
    assert remaining["zarr_conventions"] == [
        {"uuid": "00000000-0000-0000-0000-000000000000"}
    ]
    assert models == {}


def test_parse_attrs_strict_raises_on_unknown_uuid() -> None:
    attrs = {
        "zarr_conventions": [{"uuid": "00000000-0000-0000-0000-000000000000"}],
    }
    with pytest.raises(ValueError, match="Unknown convention UUID"):
        parse_attrs(attrs, strict=True)


def test_round_trip_full_set() -> None:
    base = {"foo": "bar"}
    models = [
        GeoProjModel(code="EPSG:4326"),
        SpatialModel(dimensions=["x", "y"]),
        MultiscalesModel(layout=[LayoutObjectModel(asset="s0")]),
        LicenseModel(spdx="MIT"),
        UomModel(ucum=UCUMModel(unit="m")),
    ]
    attrs = build_attrs(*models, base=base)
    remaining, parsed = parse_attrs(attrs)
    assert remaining == base
    assert len(parsed) == len(models)
    expected = {
        "geo-proj": models[0],
        "spatial": models[1],
        "multiscales": models[2],
        "license": models[3],
        "uom": models[4],
    }
    for name, model in expected.items():
        assert parsed[cast("ConventionName", name)] == model
