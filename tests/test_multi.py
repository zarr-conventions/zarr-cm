from __future__ import annotations

from typing import Any, get_args

import pytest

import zarr_cm
from zarr_cm import (
    ALL_CONVENTION_KEYS,
    CONVENTION_NAMES,
    ConventionName,
    create_many,
    extract_all,
    extract_many,
    insert_many,
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
    assert len(result["zarr_conventions"]) == 1


def test_create_many_mixed() -> None:
    result = create_many(
        {
            "geo-proj": {"proj:code": "EPSG:4326"},
            "license": {"spdx": "MIT"},
        }
    )
    assert result["proj:code"] == "EPSG:4326"
    assert result["license"] == {"spdx": "MIT"}
    assert len(result["zarr_conventions"]) == 2


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
    assert len(result["zarr_conventions"]) == 5
    assert result["proj:code"] == "EPSG:4326"
    assert result["spatial:dimensions"] == ["y", "x"]
    assert result["multiscales"]["layout"] == [{"asset": "0"}]
    assert result["license"] == {"spdx": "MIT"}
    assert result["uom"]["ucum"]["unit"] == "kg"


def test_create_many_invalid_name() -> None:
    with pytest.raises(ValueError, match="Unknown convention"):
        create_many({"not-a-convention": {}})  # type: ignore[dict-item]


def test_create_many_invalid_data() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
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
