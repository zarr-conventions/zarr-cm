from __future__ import annotations

from typing import Any, get_args

import pytest
from conftest import as_mapping, as_sequence

import zarr_cm
from zarr_cm import (
    ALL_CONVENTION_KEYS,
    CONVENTION_NAMES,
    ConventionName,
    create_many,
    extract_all,
    extract_many,
    insert_many,
    proj,
    spatial,
    validate_all,
    validate_many,
)


def test_convention_names_constant() -> None:
    assert (
        frozenset({"geo-proj", "spatial", "multiscales", "license", "uom"})
        == CONVENTION_NAMES
    )


def test_all_convention_keys_constant() -> None:
    assert (
        frozenset(
            {
                "proj:code",
                "proj:wkt2",
                "proj:projjson",
                "spatial:dimensions",
                "spatial:bbox",
                "spatial:transform_type",
                "spatial:transform",
                "spatial:shape",
                "spatial:registration",
                "multiscales",
                "license",
                "uom",
            }
        )
        == ALL_CONVENTION_KEYS
    )


def test_create_many_single() -> None:
    result = create_many({"geo-proj": {"proj:code": "EPSG:4326"}})
    assert result["proj:code"] == "EPSG:4326"
    assert len(as_sequence(result["zarr_conventions"])) == 1


def test_create_many_mixed() -> None:
    result = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        }
    )
    assert result["proj:code"] == "EPSG:4326"
    assert result["license"] == {"spdx": "MIT"}
    assert len(as_sequence(result["zarr_conventions"])) == 2


def test_create_many_all() -> None:
    result = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "spatial": {"spatial:dimensions": ["y", "x"]},
            "multiscales": {"layout": [{"asset": "0"}]},
            "license": {"spdx": "MIT"},
            "uom": {"ucum": {"unit": "kg"}},
        }
    )
    assert len(as_sequence(result["zarr_conventions"])) == 5
    assert result["proj:code"] == "EPSG:4326"
    assert result["spatial:dimensions"] == ["y", "x"]
    multiscales_data = as_mapping(result["multiscales"])
    assert multiscales_data["layout"] == [{"asset": "0"}]
    assert result["license"] == {"spdx": "MIT"}
    uom_data = as_mapping(result["uom"])
    ucum = as_mapping(uom_data["ucum"])
    assert ucum["unit"] == "kg"


def test_create_many_invalid_name() -> None:
    with pytest.raises(ValueError, match="Unknown convention"):
        create_many({"not-a-convention": {}})  # type: ignore[dict-item]


def test_create_many_invalid_data() -> None:
    # geo-proj resolves to the latest proj revision (r3, anyOf): empty data fails.
    with pytest.raises(ValueError, match="At least one"):
        create_many({"geo-proj": {}})


def test_validate_many() -> None:
    attrs = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        }
    )
    result = validate_many(attrs, ["geo-proj", "license"])
    assert result is attrs


def test_validate_many_subset() -> None:
    attrs = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        }
    )
    result = validate_many(attrs, ["geo-proj"])
    assert result is attrs


def test_validate_many_invalid() -> None:
    attrs = create_many({"license": {"spdx": "MIT"}})
    # Corrupt the license data
    attrs["license"] = {}
    with pytest.raises(ValueError, match="At least one"):
        validate_many(attrs, ["license"])


def test_validate_all() -> None:
    attrs = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
            "uom": {"ucum": {"unit": "kg"}},
        }
    )
    result = validate_all(attrs)
    assert result is attrs


def test_insert_many_empty_attrs() -> None:
    result = insert_many(
        {},
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        },
    )
    assert result["proj:code"] == "EPSG:4326"
    assert result["license"] == {"spdx": "MIT"}


def test_insert_many_preserves_attrs() -> None:
    result = insert_many(
        {"foo": "bar"},
        {"geo-proj": {"proj:code": "EPSG:4326"}},
    )
    assert result["foo"] == "bar"
    assert result["proj:code"] == "EPSG:4326"


def test_insert_many_collision_raises() -> None:
    attrs = {"proj:code": "EPSG:3857"}
    with pytest.raises(ValueError, match="overwritten"):
        insert_many(attrs, {"geo-proj": {"proj:code": "EPSG:4326"}})


def test_insert_many_overwrite() -> None:
    attrs = {"proj:code": "EPSG:3857"}
    result = insert_many(
        attrs,
        {"geo-proj": {"proj:code": "EPSG:4326"}},
        overwrite=True,
    )
    assert result["proj:code"] == "EPSG:4326"


def test_extract_many() -> None:
    attrs = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        }
    )
    remaining, extracted = extract_many(attrs, ["geo-proj", "license"])
    assert remaining == {}
    assert extracted["geo-proj"] == {"proj:code": "EPSG:4326"}
    assert extracted["license"] == {"spdx": "MIT"}


def test_extract_many_subset() -> None:
    attrs = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        }
    )
    remaining, extracted = extract_many(attrs, ["geo-proj"])
    assert "geo-proj" in extracted
    assert "license" not in extracted
    # license data stays in remaining
    assert remaining["license"] == {"spdx": "MIT"}


def test_extract_many_preserves_remaining() -> None:
    attrs = create_many({"geo-proj": {"proj:code": "EPSG:4326"}})
    attrs["foo"] = "bar"
    remaining, extracted = extract_many(attrs, ["geo-proj"])
    assert remaining == {"foo": "bar"}
    assert extracted["geo-proj"] == {"proj:code": "EPSG:4326"}


def test_extract_all() -> None:
    conventions: dict[ConventionName, dict[str, Any]] = {
        "geo-proj": {"proj:code": "EPSG:4326"},
        "license": {"spdx": "MIT"},
    }
    attrs = create_many(conventions)
    remaining, extracted = extract_all(attrs)
    assert remaining == {}
    assert extracted["geo-proj"] == {"proj:code": "EPSG:4326"}
    assert extracted["license"] == {"spdx": "MIT"}


def test_convention_name_literal_matches_registry() -> None:
    for name in get_args(ConventionName):
        assert hasattr(zarr_cm, name.replace("-", "_")), (
            f"{name!r} is not a module in zarr_cm"
        )


def test_roundtrip() -> None:
    conventions: dict[ConventionName, dict[str, Any]] = {
        "geo-proj": {"proj:code": "EPSG:4326"},
        "spatial": {"spatial:dimensions": ["y", "x"]},
        "license": {"spdx": "MIT"},
    }
    attrs = create_many(conventions)
    remaining, extracted = extract_many(attrs, conventions.keys())
    assert remaining == {}
    assert extracted == conventions


def test_create_many_revision_override() -> None:
    # Force spatial r2 instead of the default LATEST (r3) and confirm the emitted
    # CMO carries r2's commit-pinned schema_url, not r3's.
    result = create_many(
        {"spatial": {"spatial:dimensions": ["y", "x"]}},
        revisions={"spatial": "r2"},
    )
    assert result["spatial:dimensions"] == ["y", "x"]
    conventions = [as_mapping(cmo) for cmo in as_sequence(result["zarr_conventions"])]
    urls = [str(c.get("schema_url", "")) for c in conventions]
    assert any(u == spatial.r2.SCHEMA_URL for u in urls)
    assert all(u != spatial.r3.SCHEMA_URL for u in urls)


def test_extract_all_autodetects_mixed_revisions() -> None:
    attrs = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r2"), revision="r2"
    )
    attrs = proj.insert(attrs, proj.create(code="EPSG:4326"))  # proj latest = r3
    _remaining, extracted = extract_all(attrs)
    assert extracted["spatial"]["spatial:dimensions"] == ["y", "x"]
    assert extracted["geo-proj"]["proj:code"] == "EPSG:4326"


def test_extract_many_revision_override() -> None:
    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))  # r3 (latest)
    _remaining, extracted = extract_many(
        attrs, ["spatial"], revisions={"spatial": "r2"}
    )
    assert extracted["spatial"] == {"spatial:dimensions": ["y", "x"]}


def test_validate_many_revision_override_changes_outcome() -> None:
    # proj r2 enforces ^[A-Z]+:[0-9]+$ on proj:code; r3 relaxes to ^[^:]+:[^:]+$.
    # A doc tagged r3 with a relaxed code passes under r3 but fails under r2, so
    # the revisions= override genuinely selects which revision validate_many uses.
    attrs = proj.insert({}, proj.create(code="urn:ogc", revision="r3"), revision="r3")
    validate_many(attrs, ["geo-proj"], revisions={"geo-proj": "r3"})  # passes
    with pytest.raises(ValueError, match="proj:code"):
        validate_many(attrs, ["geo-proj"], revisions={"geo-proj": "r2"})


def test_validate_all_autodetects_revision_no_args() -> None:
    # A doc carrying a recognized schema_url must round-trip through validate_all
    # with NO revisions= argument: detection resolves the revision from the
    # schema_url and the same revision is threaded to both extract and validate.
    # (proj's surviving revisions are nested -- r2's accepted set is a subset of
    # r3's -- so the pass/fail outcome cannot distinguish detected-vs-LATEST here;
    # this is a smoke test of the no-args read path. The detected label itself is
    # pinned in test_detect.py, and a detected non-LATEST revision driving a
    # rejection is exercised by test_validate_all_still_rejects_genuine_r2_violation.)
    attrs = proj.insert({}, proj.create(code="urn:ogc", revision="r3"), revision="r3")
    validate_all(attrs)  # must NOT raise -- r3 detected, r3 accepts relaxed code


def test_validate_all_still_rejects_genuine_r2_violation() -> None:
    # Negative control: a doc tagged as spatial r2 (a non-latest revision;
    # LATEST is r3) but carrying 3D dimensions must still be rejected under
    # r2's strict-2D rules -- i.e. the detected revision is used for validation.
    bad: dict[str, Any] = {
        "spatial:dimensions": ["z", "y", "x"],
        "zarr_conventions": [dict(spatial.r2.CMO)],
    }
    with pytest.raises(ValueError, match="exactly 2"):
        validate_all(bad)
