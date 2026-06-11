from __future__ import annotations

import pytest

from zarr_cm.pydantic import LicenseModel


def test_construct_with_spdx() -> None:
    m = LicenseModel(spdx="MIT")
    assert m.spdx == "MIT"


def test_to_attrs_wraps_under_license_key() -> None:
    m = LicenseModel(spdx="MIT")
    assert m.to_attrs() == {"license": {"spdx": "MIT"}}


def test_at_least_one_field_required() -> None:
    with pytest.raises(ValueError, match="At least one"):
        LicenseModel()


def test_round_trip() -> None:
    m = LicenseModel(spdx="MIT", url="https://example.com/license")
    attrs = m.insert({"foo": "bar"})
    assert attrs["license"] == {"spdx": "MIT", "url": "https://example.com/license"}
    remaining, parsed = LicenseModel.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert parsed == m


def test_extract_absent_returns_none() -> None:
    remaining, parsed = LicenseModel.extract({"foo": "bar"})
    assert remaining == {"foo": "bar"}
    assert parsed is None


def test_from_attrs_accepts_inner_form() -> None:
    m = LicenseModel.from_attrs({"spdx": "MIT"})
    assert m.spdx == "MIT"


def test_from_attrs_accepts_wrapped_form() -> None:
    m = LicenseModel.from_attrs({"license": {"spdx": "MIT"}})
    assert m.spdx == "MIT"
