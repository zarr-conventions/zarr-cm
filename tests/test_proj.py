from __future__ import annotations

import pytest

from zarr_cm import proj
from zarr_cm.proj import r1 as proj_r1
from zarr_cm.proj import r2 as proj_r2


def test_r2_accepts_valid_code() -> None:
    result = proj_r2.validate({"proj:code": "EPSG:4326"})
    assert result == {"proj:code": "EPSG:4326"}


def test_r2_rejects_malformed_code() -> None:
    with pytest.raises(ValueError, match="proj:code"):
        proj_r2.validate({"proj:code": "epsg-4326"})


def test_r1_accepts_malformed_code() -> None:
    result = proj_r1.validate({"proj:code": "epsg-4326"})
    assert result == {"proj:code": "epsg-4326"}


def test_r2_still_enforces_exactly_one() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        proj_r2.validate({})


def test_r2_schema_url_corrected_and_pinned() -> None:
    assert "zarr-conventions/proj" in proj_r2.SCHEMA_URL
    assert "zarr-experimental" not in proj_r2.SCHEMA_URL
    assert "d150edbde61b53e9d17520f6d107c9d3689e5910" in proj_r2.SCHEMA_URL
    assert "refs/tags/v1" not in proj_r2.SCHEMA_URL


def test_r2_cmo_uses_corrected_url() -> None:
    assert proj_r2.CMO["schema_url"] == proj_r2.SCHEMA_URL
    assert proj_r2.CMO["uuid"] == "f17cb550-5864-4468-aeb7-f3180cfb622f"


# ---------------------------------------------------------------------------
# Package-level API (dispatches to LATEST = r2) and per-revision round-trips
# ---------------------------------------------------------------------------


def test_create_code() -> None:
    result = proj.create(code="EPSG:4326")
    assert result == {"proj:code": "EPSG:4326"}


def test_create_wkt2() -> None:
    result = proj.create(wkt2='GEOGCS["WGS 84"]')
    assert result == {"proj:wkt2": 'GEOGCS["WGS 84"]'}


def test_create_rejects_zero_keys() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        proj.create()


def test_create_rejects_malformed_code() -> None:
    with pytest.raises(ValueError, match="proj:code"):
        proj.create(code="epsg-4326")


def test_insert_and_extract_roundtrip() -> None:
    data = proj.create(code="EPSG:4326")
    inserted = proj.insert({"foo": "bar"}, data)
    assert inserted["proj:code"] == "EPSG:4326"
    assert proj_r2.CMO in inserted["zarr_conventions"]
    remaining, extracted = proj.extract(inserted)
    assert extracted == data
    assert remaining == {"foo": "bar"}


def test_insert_collision_raises() -> None:
    attrs = {"proj:code": "EPSG:3857"}
    data = proj.create(code="EPSG:4326")
    with pytest.raises(ValueError, match="overwritten"):
        proj.insert(attrs, data)


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, extracted = proj.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert extracted == {}


def test_r1_insert_uses_legacy_url() -> None:
    data: proj_r1.GeoProjAttrs = {"proj:code": "EPSG:4326"}
    result = proj_r1.insert({}, data)
    assert any(
        "zarr-experimental" in cmo.get("schema_url", "")
        for cmo in result["zarr_conventions"]
    )
