from __future__ import annotations

import pytest

from zarr_cm.pydantic import LayoutObjectModel, MultiscalesModel, TransformModel


def test_construct() -> None:
    m = MultiscalesModel(
        layout=[LayoutObjectModel(asset="s0")],
    )
    assert m.layout[0].asset == "s0"


def test_layout_min_length() -> None:
    with pytest.raises(ValueError, match="layout"):
        MultiscalesModel(layout=[])


def test_derived_from_requires_transform() -> None:
    with pytest.raises(ValueError, match="derived_from"):
        LayoutObjectModel(asset="s1", derived_from="s0")


def test_derived_from_with_transform_ok() -> None:
    LayoutObjectModel(
        asset="s1",
        derived_from="s0",
        transform=TransformModel(scale=[2.0, 2.0]),
    )


def test_to_attrs_wraps_under_multiscales_key() -> None:
    m = MultiscalesModel(layout=[LayoutObjectModel(asset="s0")])
    assert m.to_attrs() == {"multiscales": {"layout": [{"asset": "s0"}]}}


def test_round_trip() -> None:
    m = MultiscalesModel(
        layout=[
            LayoutObjectModel(asset="s0"),
            LayoutObjectModel(
                asset="s1",
                derived_from="s0",
                transform=TransformModel(scale=[2.0, 2.0]),
            ),
        ],
        resampling_method="mean",
    )
    attrs = m.insert({})
    remaining, parsed = MultiscalesModel.extract(attrs)
    assert remaining == {}
    assert parsed == m


def test_extract_absent_returns_none() -> None:
    _remaining, parsed = MultiscalesModel.extract({"foo": "bar"})
    assert parsed is None


def test_from_attrs_accepts_inner_form() -> None:
    m = MultiscalesModel.from_attrs({"layout": [{"asset": "s0"}]})
    assert m.layout[0].asset == "s0"


def test_from_attrs_accepts_wrapped_form() -> None:
    m = MultiscalesModel.from_attrs({"multiscales": {"layout": [{"asset": "s0"}]}})
    assert m.layout[0].asset == "s0"
