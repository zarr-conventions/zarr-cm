from __future__ import annotations

import pytest

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
