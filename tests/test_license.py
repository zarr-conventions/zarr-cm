from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from conftest import wrap_attrs

from zarr_cm import license
from zarr_cm.license import CMO, LicenseAttrs

SCHEMA_PATH = Path(__file__).parent / "schemas" / "license.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def test_insert_license_spdx() -> None:
    data: LicenseAttrs = {"spdx": "MIT"}
    result = license.insert({}, data)
    assert result["license"] == {"spdx": "MIT"}
    assert result["zarr_conventions"] == [CMO]


def test_insert_license_url() -> None:
    data: LicenseAttrs = {"url": "https://example.com/license"}
    result = license.insert({}, data)
    assert result["license"]["url"] == "https://example.com/license"


def test_insert_preserves_existing_attrs() -> None:
    attrs = {"foo": "bar"}
    data: LicenseAttrs = {"spdx": "MIT"}
    result = license.insert(attrs, data)
    assert result["foo"] == "bar"


def test_insert_appends_to_existing_conventions() -> None:
    attrs = {"zarr_conventions": [{"uuid": "other-uuid"}]}
    data: LicenseAttrs = {"spdx": "MIT"}
    result = license.insert(attrs, data)
    assert len(result["zarr_conventions"]) == 2


def test_extract_license() -> None:
    attrs = {
        "license": {"spdx": "MIT"},
        "foo": "bar",
        "zarr_conventions": [CMO],
    }
    remaining, data = license.extract(attrs)
    assert data == {"spdx": "MIT"}
    assert remaining == {"foo": "bar"}


def test_extract_preserves_other_conventions() -> None:
    other_cmo = {"uuid": "other-uuid"}
    attrs = {
        "license": {"spdx": "MIT"},
        "zarr_conventions": [other_cmo, CMO],
    }
    remaining, _data = license.extract(attrs)
    assert remaining["zarr_conventions"] == [other_cmo]


def test_roundtrip() -> None:
    original_attrs = {"foo": "bar"}
    data: LicenseAttrs = {"spdx": "Apache-2.0"}
    inserted = license.insert(original_attrs, data)
    remaining, extracted = license.extract(inserted)
    assert remaining == original_attrs
    assert extracted == data


def test_schema_validation_spdx() -> None:
    data: LicenseAttrs = {"spdx": "CC0-1.0"}
    result = license.insert({}, data)
    node = wrap_attrs(result, node_type="group")
    jsonschema.validate(node, SCHEMA)


def test_schema_validation_url() -> None:
    data: LicenseAttrs = {"url": "https://creativecommons.org/licenses/by/4.0/"}
    result = license.insert({}, data)
    node = wrap_attrs(result, node_type="group")
    jsonschema.validate(node, SCHEMA)


def test_validate_valid() -> None:
    result = license.validate({"spdx": "MIT"})
    assert result == {"spdx": "MIT"}


def test_validate_empty() -> None:
    with pytest.raises(ValueError, match="At least one"):
        license.validate({})


def test_create_spdx() -> None:
    result = license.create(spdx="MIT")
    assert result == {"spdx": "MIT"}


def test_create_multiple() -> None:
    result = license.create(spdx="MIT", url="https://example.com/license")
    assert result == {"spdx": "MIT", "url": "https://example.com/license"}


def test_create_empty() -> None:
    with pytest.raises(ValueError, match="At least one"):
        license.create()


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, data = license.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert data == {}


def test_insert_collision_raises() -> None:
    attrs = {"license": {"spdx": "GPL-3.0"}}
    data: LicenseAttrs = {"spdx": "MIT"}
    with pytest.raises(ValueError, match="overwritten"):
        license.insert(attrs, data)


def test_insert_idempotent() -> None:
    data: LicenseAttrs = {"spdx": "MIT"}
    once = license.insert({}, data)
    twice = license.insert(once, data, overwrite=True)
    assert once == twice
