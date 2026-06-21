from __future__ import annotations

import pytest

from zarr_cm import proj, spatial

# ---------------------------------------------------------------------------
# spatial — detection via _resolve_read_revision
# ---------------------------------------------------------------------------


def test_detect_resolves_r2_from_r2_url() -> None:
    """_resolve_read_revision picks "r2" when the stored schema_url is r2's URL."""
    data = spatial.create(dimensions=["y", "x"], revision="r2")
    attrs = spatial.insert({}, data, revision="r2")
    assert spatial._resolve_read_revision(attrs, None) == "r2"


def test_detect_resolves_r3_from_r3_url() -> None:
    """_resolve_read_revision picks "r3" when the stored schema_url is r3's URL."""
    data = spatial.create(dimensions=["y", "x"], revision="r3")
    attrs = spatial.insert({}, data, revision="r3")
    assert spatial._resolve_read_revision(attrs, None) == "r3"


def test_unknown_url_falls_back_to_latest() -> None:
    """A schema_url that matches no known revision falls back to LATEST.

    The fabricated commit-pinned URL will never match any entry in
    _SCHEMA_URL_BY_REVISION, so detection yields LATEST.
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
    # Confirm a genuine r2 URL resolves to r2, distinct from the fallback path.
    r2_attrs = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r2"), revision="r2"
    )
    assert spatial._resolve_read_revision(r2_attrs, None) == "r2"


def test_explicit_revision_overrides_detection() -> None:
    """An explicit revision= argument wins over the schema_url in the attrs."""
    data = spatial.create(dimensions=["y", "x"])  # latest-revision (r3) doc
    attrs = spatial.insert({}, data)
    # attrs contains r3's schema_url, but we force r2
    assert spatial._resolve_read_revision(attrs, "r2") == "r2"


# ---------------------------------------------------------------------------
# spatial — round-trip tests (kept for integration coverage)
# ---------------------------------------------------------------------------


def test_spatial_extract_autodetects_r2() -> None:
    # Write with r2, read back with no revision arg -> must detect r2.
    data = spatial.create(dimensions=["y", "x"], revision="r2")
    attrs = spatial.insert({}, data, revision="r2")
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data


def test_spatial_extract_detects_latest() -> None:
    data = spatial.create(dimensions=["y", "x"])  # default = latest revision
    attrs = spatial.insert({}, data)
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data


def test_extract_revision_override_wins() -> None:
    # latest-revision (r3) doc but force-read as r2 via explicit revision.
    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))
    _remaining, extracted = spatial.extract(attrs, revision="r2")
    assert extracted == {"spatial:dimensions": ["y", "x"]}


# ---------------------------------------------------------------------------
# proj — detection via _resolve_read_revision
# ---------------------------------------------------------------------------


def test_proj_resolves_r2_from_r2_url() -> None:
    """_resolve_read_revision picks "r2" when the stored schema_url is proj r2's URL."""
    data = proj.create(code="EPSG:4326", revision="r2")
    attrs = proj.insert({}, data, revision="r2")
    assert proj._resolve_read_revision(attrs, None) == "r2"


def test_proj_resolves_r3_from_r3_url() -> None:
    """_resolve_read_revision picks "r3" when the stored schema_url is proj r3's URL."""
    data = proj.create(code="EPSG:4326", revision="r3")
    attrs = proj.insert({}, data, revision="r3")
    assert proj._resolve_read_revision(attrs, None) == "r3"


def test_proj_unknown_url_falls_back_to_latest() -> None:
    """A schema_url that matches no known proj revision falls back to LATEST (r3)."""
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
    assert resolved == proj.LATEST  # == "r3"
    # Confirm a genuine r2 URL resolves to r2, distinct from the fallback path.
    r2_attrs = proj.insert(
        {}, proj.create(code="EPSG:4326", revision="r2"), revision="r2"
    )
    assert proj._resolve_read_revision(r2_attrs, None) == "r2"


def test_proj_extract_autodetects_r2_url() -> None:
    data = proj.create(code="EPSG:4326", revision="r2")
    attrs = proj.insert({}, data, revision="r2")
    _remaining, extracted = proj.extract(attrs)
    assert extracted == data


def test_proj_validate_observably_differs_by_revision() -> None:
    """r2 requires code to match ``^[A-Z]+:[0-9]+$``; r3 relaxes to ``^[^:]+:[^:]+$``.

    A code like ``urn:ogc`` matches r3's relaxed pattern but not r2's strict one,
    so the revision argument observably controls dispatch.
    """
    data = {"proj:code": "urn:ogc"}
    # r3 accepts the relaxed code
    proj.validate(data, revision="r3")  # must not raise
    # r2 rejects it
    with pytest.raises(ValueError, match="proj:code"):
        proj.validate(data, revision="r2")
