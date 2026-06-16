from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from conftest import wrap_attrs

from zarr_cm import proj
from zarr_cm.proj import r1 as proj_r1
from zarr_cm.proj import r2 as proj_r2
from zarr_cm.proj import r3 as proj_r3


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
# Package-level API (dispatches to LATEST = r3) and per-revision round-trips
# ---------------------------------------------------------------------------


def test_create_code() -> None:
    result = proj.create(code="EPSG:4326")
    assert result == {"proj:code": "EPSG:4326"}


def test_create_wkt2() -> None:
    result = proj.create(wkt2='GEOGCS["WGS 84"]')
    assert result == {"proj:wkt2": 'GEOGCS["WGS 84"]'}


def test_create_rejects_zero_keys() -> None:
    # Default facade is LATEST = r3, whose anyOf rule requires at least one key.
    with pytest.raises(ValueError, match="At least one"):
        proj.create()


def test_create_rejects_malformed_code() -> None:
    with pytest.raises(ValueError, match="proj:code"):
        proj.create(code="epsg-4326")


def test_insert_and_extract_roundtrip() -> None:
    data = proj.create(code="EPSG:4326")
    inserted = proj.insert({"foo": "bar"}, data)
    assert inserted["proj:code"] == "EPSG:4326"
    assert proj_r3.CMO in inserted["zarr_conventions"]
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


# ---------------------------------------------------------------------------
# r3 (v0.1): relaxed proj:code pattern + anyOf CRS rule
# ---------------------------------------------------------------------------


def test_r3_accepts_relaxed_code() -> None:
    # r3's pattern is ^[^:]+:[^:]+$ (matches upstream v0.1), which accepts a
    # lowercase authority that r2's stricter ^[A-Z]+:[0-9]+$ rejects.
    assert proj_r3.validate({"proj:code": "epsg:4326"}) == {"proj:code": "epsg:4326"}
    with pytest.raises(ValueError, match="proj:code"):
        proj_r2.validate({"proj:code": "epsg:4326"})


def test_r3_allows_multiple_crs_keys() -> None:
    result = proj_r3.validate({"proj:code": "EPSG:4326", "proj:wkt2": "GEOGCS[...]"})
    assert result == {"proj:code": "EPSG:4326", "proj:wkt2": "GEOGCS[...]"}
    with pytest.raises(ValueError, match="Exactly one"):
        proj_r2.validate({"proj:code": "EPSG:4326", "proj:wkt2": "GEOGCS[...]"})


def test_r3_rejects_zero_keys() -> None:
    with pytest.raises(ValueError, match="At least one"):
        proj_r3.validate({})


def test_r3_schema_url_pinned_to_v0_1() -> None:
    assert "5ca5b2f92e5c7245f957d9128b289ee535f0720d" in proj_r3.SCHEMA_URL
    assert "refs/tags/v1" not in proj_r3.SCHEMA_URL


def test_proj_latest_is_r3() -> None:
    assert proj.LATEST == "r3"


# ---------------------------------------------------------------------------
# Vendored schema fixture test
# ---------------------------------------------------------------------------

R2_SCHEMA_PATH = Path(__file__).parent / "schemas" / "proj-r2.json"
R2_SCHEMA = json.loads(R2_SCHEMA_PATH.read_text())


def test_r2_create_validates_against_vendored_schema() -> None:
    # This asserts our r2 output conforms to the r2 'proj:' DATA shape. Note the
    # vendored schema does not actually constrain our CMO: it pins
    # conventionMetadata fields to const v1 values that our commit-pinned CMO
    # does not match, but the schema's `attributes` subschema carries a sibling
    # `$ref` next to its `contains`, so under draft-07 the convention-metadata
    # check is effectively not enforced here.
    data = proj_r2.create(code="EPSG:4326")
    node = wrap_attrs(proj_r2.insert({}, data))
    jsonschema.validate(node, R2_SCHEMA)
