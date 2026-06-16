from __future__ import annotations

import pytest

import zarr_cm
from zarr_cm import license as license_
from zarr_cm import multiscales, proj, spatial, uom


def test_spatial_detect_known_revisions() -> None:
    r1 = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    r2 = spatial.insert({}, spatial.create(dimensions=["y", "x"]))  # latest = r2
    assert spatial.detect(r1) == "r1"
    assert spatial.detect(r2) == "r2"


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
    r1 = proj.insert({}, proj.create(code="EPSG:4326", revision="r1"), revision="r1")
    r2 = proj.insert({}, proj.create(code="EPSG:4326"))
    assert proj.detect(r1) == "r1"
    assert proj.detect(r2) == "r2"


def test_detect_revisions_aggregate() -> None:
    attrs = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    attrs = proj.insert(attrs, proj.create(code="EPSG:4326"))  # r2
    result = zarr_cm.detect_revisions(attrs)
    assert result == {"spatial": "r1", "geo-proj": "r2"}


def test_detect_revisions_empty() -> None:
    assert zarr_cm.detect_revisions({"foo": "bar"}) == {}


def test_flat_detect_present_returns_v1() -> None:
    ms = multiscales.insert({}, multiscales.create(layout=[{"asset": "0"}]))
    assert multiscales.detect(ms) == "v1"
    li = license_.insert({}, license_.create(spdx="MIT"))
    assert license_.detect(li) == "v1"
    um = uom.insert({}, uom.create(ucum={"unit": "m"}))
    assert uom.detect(um) == "v1"


def test_flat_detect_unknown_url_returns_none() -> None:
    doc = {
        "multiscales": {"layout": [{"asset": "0"}]},
        "zarr_conventions": [
            {"uuid": multiscales.UUID, "schema_url": "https://example/other.json"}
        ],
    }
    assert multiscales.detect(doc) is None


def test_flat_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="multiscales"):
        multiscales.detect({"foo": "bar"})
