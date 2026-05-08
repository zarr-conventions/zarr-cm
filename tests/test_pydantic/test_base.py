from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from pydantic import Field

from zarr_cm import geo_proj
from zarr_cm.pydantic._base import ConventionModel

if TYPE_CHECKING:
    from zarr_cm._core import ConventionMetadataObject


class _ToyModel(ConventionModel):
    """Minimal subclass for testing ConventionModel plumbing."""

    code: str | None = Field(default=None, alias="proj:code")

    _CMO: ClassVar[ConventionMetadataObject] = geo_proj.CMO
    _MODULE: ClassVar[Any] = geo_proj


def test_to_attrs_uses_aliases_and_drops_none() -> None:
    m = _ToyModel(code="EPSG:4326")
    assert m.to_attrs() == {"proj:code": "EPSG:4326"}


def test_from_attrs_round_trips() -> None:
    m = _ToyModel.from_attrs({"proj:code": "EPSG:4326"})
    assert m.code == "EPSG:4326"


def test_extra_forbid() -> None:
    with pytest.raises(ValueError, match="Extra inputs"):
        _ToyModel(code="EPSG:4326", bogus=1)  # type: ignore[call-arg]


def test_insert_delegates_to_module() -> None:
    m = _ToyModel(code="EPSG:4326")
    attrs = m.insert({"foo": "bar"})
    assert attrs["foo"] == "bar"
    assert attrs["proj:code"] == "EPSG:4326"
    assert attrs["zarr_conventions"] == [geo_proj.CMO]


def test_extract_returns_none_when_absent() -> None:
    remaining, parsed = _ToyModel.extract({"foo": "bar"})
    assert remaining == {"foo": "bar"}
    assert parsed is None


def test_extract_round_trip() -> None:
    m = _ToyModel(code="EPSG:4326")
    attrs = m.insert({})
    remaining, parsed = _ToyModel.extract(attrs)
    assert remaining == {}
    assert parsed is not None
    assert parsed.code == "EPSG:4326"
