"""Error-path tests for the JSON-shape validators in :mod:`zarr_cm._core`.

These functions narrow arbitrary ``object`` inputs to the package's JSON types
and raise ``TypeError`` on anything that is not JSON-shaped; the happy paths are
exercised throughout the convention tests, so here we pin the rejection paths.
"""

from __future__ import annotations

import pytest

from zarr_cm._core import (
    validate_convention_metadata_objects,
    validate_json_object,
    validate_json_value,
)


def test_validate_json_value_accepts_nested() -> None:
    value = {"a": 1, "b": [True, "x", {"c": None}]}
    assert validate_json_value(value) == value


def test_validate_json_value_rejects_non_json() -> None:
    with pytest.raises(TypeError, match="expected a JSON value, got object"):
        validate_json_value(object())


def test_validate_json_object_rejects_non_mapping() -> None:
    with pytest.raises(TypeError, match="expected a JSON object, got list"):
        validate_json_object([1, 2, 3])


def test_validate_json_object_rejects_non_str_key() -> None:
    with pytest.raises(TypeError, match="keys to be str, got int"):
        validate_json_object({1: "value"})


def test_validate_cmos_none_is_empty() -> None:
    assert validate_convention_metadata_objects(None) == []


def test_validate_cmos_rejects_non_sequence() -> None:
    with pytest.raises(TypeError, match="zarr_conventions must be an array"):
        validate_convention_metadata_objects({"not": "an array"})


def test_validate_cmos_rejects_non_str_field() -> None:
    with pytest.raises(TypeError, match="field 'uuid' must be a string"):
        validate_convention_metadata_objects([{"uuid": 123}])
