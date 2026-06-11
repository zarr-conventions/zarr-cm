from __future__ import annotations

from zarr_cm import proj, spatial


def test_spatial_extract_autodetects_r1_3d() -> None:
    # Write with r1 (3D), read back with no revision arg -> must detect r1.
    data = spatial.create(dimensions=["z", "y", "x"], revision="r1")
    attrs = spatial.insert({}, data, revision="r1")
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data  # round-trips; r2 would have rejected 3D


def test_spatial_validate_autodetects_r1() -> None:
    attrs = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    # extract auto-detects r1 (allows 3D); validating the extracted data with the
    # detected revision must not raise.
    _r, extracted = spatial.extract(attrs)
    spatial.validate(dict(extracted), revision="r1")  # r1 allows 3D


def test_spatial_extract_detects_r2() -> None:
    data = spatial.create(dimensions=["y", "x"])  # default latest = r2
    attrs = spatial.insert({}, data)
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data


def test_spatial_extract_unknown_url_falls_back_to_latest() -> None:
    # Legacy doc: spatial UUID but dangling tags/v1 url -> falls back to LATEST (r2).
    attrs = {
        "spatial:dimensions": ["y", "x"],
        "zarr_conventions": [
            {
                "uuid": "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4",
                "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json",
            }
        ],
    }
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == {"spatial:dimensions": ["y", "x"]}


def test_extract_revision_override_wins() -> None:
    # r2 doc but force-read as r1 via explicit revision.
    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))
    _remaining, extracted = spatial.extract(attrs, revision="r1")
    assert extracted == {"spatial:dimensions": ["y", "x"]}


def test_proj_extract_autodetects_r1_url() -> None:
    data = proj.create(code="EPSG:4326", revision="r1")
    attrs = proj.insert({}, data, revision="r1")
    _remaining, extracted = proj.extract(attrs)
    assert extracted == data
