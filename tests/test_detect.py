from __future__ import annotations

import pytest

import zarr_cm
from zarr_cm import license as license_
from zarr_cm import multiscales, proj, spatial, uom


def test_spatial_detect_known_revisions() -> None:
    r2 = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r2"), revision="r2"
    )
    r3 = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r3"), revision="r3"
    )
    assert spatial.detect(r2) == "r2"
    assert spatial.detect(r3) == "r3"


def test_spatial_detect_unknown_revision_returns_none() -> None:
    doc = {
        "spatial:dimensions": ["y", "x"],
        "zarr_conventions": [
            {
                "uuid": spatial.UUID,
                "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/0000000000000000000000000000000000000000/schema.json",
            }
        ],
    }
    assert spatial.detect(doc) is None


def test_spatial_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="spatial"):
        spatial.detect({"foo": "bar"})


def test_proj_detect_known_revisions() -> None:
    r2 = proj.insert({}, proj.create(code="EPSG:4326", revision="r2"), revision="r2")
    r3 = proj.insert({}, proj.create(code="EPSG:4326", revision="r3"), revision="r3")
    assert proj.detect(r2) == "r2"
    assert proj.detect(r3) == "r3"


def test_proj_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="geo-proj"):
        proj.detect({"foo": "bar"})


def test_detect_revisions_aggregate() -> None:
    attrs = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r3"), revision="r3"
    )
    attrs = proj.insert(
        attrs, proj.create(code="EPSG:4326", revision="r2"), revision="r2"
    )
    attrs = multiscales.insert(attrs, multiscales.create(layout=[{"asset": "0"}]))
    result = zarr_cm.detect_revisions(attrs)
    assert result == {"spatial": "r3", "geo-proj": "r2", "multiscales": "r2"}


def test_detect_revisions_empty() -> None:
    assert zarr_cm.detect_revisions({"foo": "bar"}) == {}


def test_multiscales_detect_latest_returns_r2() -> None:
    ms = multiscales.insert({}, multiscales.create(layout=[{"asset": "0"}]))
    assert multiscales.detect(ms) == "r2"


def test_multiscales_detect_unknown_url_returns_none() -> None:
    other = "https://example/other.json"
    ms = {
        "multiscales": {"layout": [{"asset": "0"}]},
        "zarr_conventions": [{"uuid": multiscales.UUID, "schema_url": other}],
    }
    assert multiscales.detect(ms) is None


def test_multiscales_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="multiscales"):
        multiscales.detect({"foo": "bar"})


def test_flat_detect_present_returns_v1() -> None:
    li = license_.insert({}, license_.create(spdx="MIT"))
    assert license_.detect(li) == "v1"
    um = uom.insert({}, uom.create(ucum={"unit": "m"}))
    assert uom.detect(um) == "v1"


def test_flat_detect_unknown_url_returns_none() -> None:
    other = "https://example/other.json"
    li = {
        "license": {"spdx": "MIT"},
        "zarr_conventions": [{"uuid": license_.UUID, "schema_url": other}],
    }
    assert license_.detect(li) is None
    um = {
        "uom": {"ucum": {"unit": "m"}},
        "zarr_conventions": [{"uuid": uom.UUID, "schema_url": other}],
    }
    assert uom.detect(um) is None


def test_flat_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="license"):
        license_.detect({"foo": "bar"})
