from __future__ import annotations

import pytest

from zarr_cm import proj, spatial

# ---------------------------------------------------------------------------
# spatial — detection via _resolve_read_revision
# ---------------------------------------------------------------------------


def test_detect_resolves_r1_from_r1_url() -> None:
    """_resolve_read_revision picks "r1" when the stored schema_url is r1's URL."""
    data = spatial.create(dimensions=["z", "y", "x"], revision="r1")
    attrs = spatial.insert({}, data, revision="r1")
    assert spatial._resolve_read_revision(attrs, None) == "r1"


def test_detect_resolves_r2_from_r2_url() -> None:
    """_resolve_read_revision picks "r2" when the stored schema_url is r2's URL."""
    data = spatial.create(dimensions=["y", "x"], revision="r2")
    attrs = spatial.insert({}, data, revision="r2")
    assert spatial._resolve_read_revision(attrs, None) == "r2"


def test_unknown_url_falls_back_to_latest() -> None:
    """A schema_url that matches no known revision falls back to LATEST.

    This is NOT the same as r1's URL (refs/tags/v1) — it is a fabricated
    commit-pinned URL that will never match any entry in _SCHEMA_URL_BY_REVISION.
    """
    fabricated_url = (
        "https://raw.githubusercontent.com/zarr-conventions/spatial"
        "/0000000000000000000000000000000000000000/schema.json"
    )
    attrs = {
        "spatial:dimensions": ["y", "x"],
        "zarr_conventions": [
            {
                "uuid": spatial.UUID,
                "schema_url": fabricated_url,
            }
        ],
    }
    resolved = spatial._resolve_read_revision(attrs, None)
    assert resolved == spatial.LATEST
    # Confirm it differs from what a genuine r1 URL would resolve to.
    r1_attrs = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r1"), revision="r1"
    )
    assert spatial._resolve_read_revision(r1_attrs, None) == "r1"
    assert resolved != "r1"


def test_explicit_revision_overrides_detection() -> None:
    """An explicit revision= argument wins over the schema_url in the attrs."""
    data = spatial.create(dimensions=["y", "x"])  # latest-revision doc
    attrs = spatial.insert({}, data)
    # attrs contains the latest revision's schema_url, but we force r1
    assert spatial._resolve_read_revision(attrs, "r1") == "r1"


def test_validate_observably_differs_by_detected_revision() -> None:
    """3D data is valid under r1 but invalid under r2 — revision arg selects behavior.

    This test would fail if the two revisions behaved identically, proving that
    the revision argument (and by extension detection) actually controls dispatch.

    Note: bare validate() on the extracted dict (no zarr_conventions) falls back
    to LATEST (strict 2D), which correctly rejects 3D data; caller must pass
    revision="r1" explicitly when the CMO is absent.
    """
    data = spatial.create(dimensions=["z", "y", "x"], revision="r1")
    attrs = spatial.insert({}, data, revision="r1")
    _r, extracted = spatial.extract(attrs)  # auto-detects r1

    # r1 accepts 3D
    spatial.validate(dict(extracted), revision="r1")  # must not raise

    # r2 rejects 3D — confirms the two revisions genuinely differ
    with pytest.raises(ValueError, match="exactly 2 items"):
        spatial.validate(dict(extracted), revision="r2")


# ---------------------------------------------------------------------------
# spatial — round-trip tests (kept for integration coverage)
# ---------------------------------------------------------------------------


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


def test_spatial_extract_detects_latest() -> None:
    data = spatial.create(dimensions=["y", "x"])  # default = latest revision
    attrs = spatial.insert({}, data)
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data


def test_extract_revision_override_wins() -> None:
    # latest-revision doc but force-read as r1 via explicit revision.
    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))
    _remaining, extracted = spatial.extract(attrs, revision="r1")
    assert extracted == {"spatial:dimensions": ["y", "x"]}


# ---------------------------------------------------------------------------
# proj — detection via _resolve_read_revision
# ---------------------------------------------------------------------------


def test_proj_resolves_r1_from_r1_url() -> None:
    """_resolve_read_revision picks "r1" when the stored schema_url is proj r1's URL."""
    data = proj.create(code="EPSG:4326", revision="r1")
    attrs = proj.insert({}, data, revision="r1")
    assert proj._resolve_read_revision(attrs, None) == "r1"


def test_proj_resolves_r2_from_r2_url() -> None:
    """_resolve_read_revision picks "r2" when the stored schema_url is proj r2's URL."""
    data = proj.create(code="EPSG:4326")  # default LATEST = r2
    attrs = proj.insert({}, data)
    assert proj._resolve_read_revision(attrs, None) == "r2"


def test_proj_unknown_url_falls_back_to_latest() -> None:
    """A schema_url that matches no known proj revision falls back to LATEST (r2)."""
    fabricated_url = (
        "https://raw.githubusercontent.com/zarr-conventions/proj"
        "/0000000000000000000000000000000000000000/schema.json"
    )
    attrs = {
        "proj:code": "EPSG:4326",
        "zarr_conventions": [
            {
                "uuid": proj.UUID,  # f17cb550-5864-4468-aeb7-f3180cfb622f
                "schema_url": fabricated_url,
            }
        ],
    }
    resolved = proj._resolve_read_revision(attrs, None)
    assert resolved == proj.LATEST  # == "r2"
    # Confirm it differs from what a genuine r1 URL would resolve to.
    r1_attrs = proj.insert(
        {}, proj.create(code="EPSG:4326", revision="r1"), revision="r1"
    )
    assert proj._resolve_read_revision(r1_attrs, None) == "r1"
    assert resolved != "r1"


def test_proj_extract_autodetects_r1_url() -> None:
    data = proj.create(code="EPSG:4326", revision="r1")
    attrs = proj.insert({}, data, revision="r1")
    _remaining, extracted = proj.extract(attrs)
    assert extracted == data
