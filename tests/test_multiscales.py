from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from conftest import as_mapping, as_sequence, wrap_attrs

from zarr_cm import multiscales
from zarr_cm.multiscales import CMO, MultiscalesAttrs
from zarr_cm.multiscales import r1 as multiscales_r1
from zarr_cm.multiscales import r2 as multiscales_r2

SCHEMA_PATH = Path(__file__).parent / "schemas" / "multiscales.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def test_insert_multiscales_minimal() -> None:
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert({}, data)
    multiscales_data = as_mapping(result["multiscales"])
    assert multiscales_data["layout"] == [{"asset": "0"}]
    assert result["zarr_conventions"] == [CMO]


def test_insert_multiscales_with_derived() -> None:
    data: MultiscalesAttrs = {
        "layout": [
            {"asset": "0"},
            {
                "asset": "1",
                "derived_from": "0",
                "transform": {"scale": [2.0, 2.0]},
            },
        ],
    }
    result = multiscales.insert({}, data)
    multiscales_data = as_mapping(result["multiscales"])
    assert len(as_sequence(multiscales_data["layout"])) == 2


def test_insert_preserves_existing_attrs() -> None:
    attrs = {"foo": "bar"}
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert(attrs, data)
    assert result["foo"] == "bar"


def test_insert_appends_to_existing_conventions() -> None:
    attrs = {"zarr_conventions": [{"uuid": "other-uuid"}]}
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert(attrs, data)
    assert len(as_sequence(result["zarr_conventions"])) == 2


def test_extract_multiscales() -> None:
    attrs = {
        "multiscales": {"layout": [{"asset": "0"}]},
        "foo": "bar",
        "zarr_conventions": [CMO],
    }
    remaining, data = multiscales.extract(attrs)
    assert data == {"layout": [{"asset": "0"}]}
    assert remaining == {"foo": "bar"}


def test_extract_preserves_other_conventions() -> None:
    other_cmo = {"uuid": "other-uuid"}
    attrs = {
        "multiscales": {"layout": [{"asset": "0"}]},
        "zarr_conventions": [other_cmo, CMO],
    }
    remaining, _data = multiscales.extract(attrs)
    assert remaining["zarr_conventions"] == [other_cmo]


def test_roundtrip() -> None:
    original_attrs = {"foo": "bar"}
    data: MultiscalesAttrs = {
        "layout": [
            {"asset": "0"},
            {
                "asset": "1",
                "derived_from": "0",
                "transform": {"scale": [2.0, 2.0]},
            },
        ],
        "resampling_method": "nearest",
    }
    inserted = multiscales.insert(original_attrs, data)
    remaining, extracted = multiscales.extract(inserted)
    assert remaining == original_attrs
    assert extracted == data


R2_SCHEMA_PATH = Path(__file__).parent / "schemas" / "multiscales-r2.json"
R2_SCHEMA = json.loads(R2_SCHEMA_PATH.read_text())

# Note: the multiscales v0.1 schema ENFORCES conventionMetadata's schema_url as a
# `const` equal to the refs/tags/v0.1 tag URL (its `attributes` subschema has no
# sibling `$ref` escape, unlike spatial/proj). multiscales r2 therefore pins to
# that tag URL (not a commit SHA), so our emitted CMO validates against the
# official schema directly — no CMO substitution needed in these tests.


def test_schema_validation_minimal() -> None:
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert({}, data)
    node = wrap_attrs(result, node_type="group")
    jsonschema.validate(node, R2_SCHEMA)


def test_schema_validation_full() -> None:
    data: MultiscalesAttrs = {
        "layout": [
            {"asset": "0"},
            {
                "asset": "1",
                "derived_from": "0",
                "transform": {"scale": [2.0, 2.0], "translation": [0.5, 0.5]},
                "resampling_method": "nearest",
            },
            {
                "asset": "2",
                "derived_from": "1",
                "transform": {"scale": [2.0, 2.0], "translation": [0.5, 0.5]},
            },
        ],
        "resampling_method": "bilinear",
    }
    result = multiscales.insert({}, data)
    node = wrap_attrs(result, node_type="group")
    jsonschema.validate(node, R2_SCHEMA)


def test_validate_valid() -> None:
    result = multiscales.validate({"layout": [{"asset": "0"}]})
    assert result == {"layout": [{"asset": "0"}]}


def test_validate_missing_layout() -> None:
    with pytest.raises(ValueError, match="'layout' is required"):
        multiscales.validate({})


def test_validate_empty_layout() -> None:
    with pytest.raises(ValueError, match="at least one"):
        multiscales.validate({"layout": []})


def test_validate_derived_without_transform() -> None:
    with pytest.raises(ValueError, match="missing 'transform'"):
        multiscales.validate(
            {
                "layout": [
                    {"asset": "0"},
                    {"asset": "1", "derived_from": "0"},
                ],
            }
        )


def test_create_minimal() -> None:
    result = multiscales.create(layout=[{"asset": "0"}])
    assert result == {"layout": [{"asset": "0"}]}


def test_create_with_resampling() -> None:
    result = multiscales.create(layout=[{"asset": "0"}], resampling_method="nearest")
    assert result == {"layout": [{"asset": "0"}], "resampling_method": "nearest"}


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, data = multiscales.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert data == {"layout": []}


def test_insert_collision_raises() -> None:
    attrs = {"multiscales": {"layout": [{"asset": "old"}]}}
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    with pytest.raises(ValueError, match="overwritten"):
        multiscales.insert(attrs, data)


def test_insert_idempotent() -> None:
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    once = multiscales.insert({}, data)
    twice = multiscales.insert(once, data, overwrite=True)
    assert once == twice


def test_r2_schema_url_pinned_to_v0_1() -> None:
    # r2 pins to the refs/tags/v0.1 tag URL (the schema enforces it as a const).
    assert "refs/tags/v0.1" in multiscales_r2.SCHEMA_URL
    assert "refs/tags/v1/" not in multiscales_r2.SCHEMA_URL


def test_r1_keeps_legacy_url() -> None:
    assert "refs/tags/v1" in multiscales_r1.SCHEMA_URL


def test_r2_create_validates_against_vendored_schema() -> None:
    # r2's tag-pinned CMO matches the schema's conventionMetadata const, so our
    # actual emitted output validates against the official v0.1 schema directly.
    data = multiscales.create(layout=[{"asset": "0"}])
    node = wrap_attrs(multiscales.insert({}, data), node_type="group")
    jsonschema.validate(node, R2_SCHEMA)


def test_multiscales_revision_roundtrip() -> None:
    r1_doc = multiscales.insert(
        {}, multiscales.create(layout=[{"asset": "0"}], revision="r1"), revision="r1"
    )
    assert multiscales.detect(r1_doc) == "r1"
    _, data = multiscales.extract(r1_doc, revision="r1")
    assert data["layout"] == [{"asset": "0"}]


# ---------------------------------------------------------------------------
# Per-revision validate rejection paths, extract, unknown revision
# ---------------------------------------------------------------------------


def test_r1_validate_missing_layout() -> None:
    with pytest.raises(ValueError, match="'layout' is required"):
        multiscales_r1.validate({})


def test_r1_validate_non_array_layout() -> None:
    with pytest.raises(TypeError, match="'layout' must be an array"):
        multiscales_r1.validate({"layout": "nope"})


def test_r1_validate_empty_layout() -> None:
    with pytest.raises(ValueError, match="at least one"):
        multiscales_r1.validate({"layout": []})


def test_r1_validate_entry_not_object() -> None:
    with pytest.raises(TypeError, match=r"layout\[0\] must be an object"):
        multiscales_r1.validate({"layout": ["not-an-object"]})


def test_r1_validate_derived_without_transform() -> None:
    with pytest.raises(ValueError, match="missing 'transform'"):
        multiscales_r1.validate(
            {"layout": [{"asset": "0"}, {"asset": "1", "derived_from": "0"}]}
        )


def test_r1_extract_missing_convention_returns_empty_layout() -> None:
    remaining, data = multiscales_r1.extract({"foo": "bar"})
    assert remaining == {"foo": "bar"}
    assert data == {"layout": []}


def test_r1_extract_roundtrip() -> None:
    entry: multiscales_r1.LayoutObject = {"asset": "0"}
    data = multiscales_r1.create(layout=(entry,))
    inserted = multiscales_r1.insert({"foo": "bar"}, data)
    remaining, extracted = multiscales_r1.extract(inserted)
    assert extracted == {"layout": ({"asset": "0"},)}
    assert remaining == {"foo": "bar"}


def test_r2_validate_non_array_layout() -> None:
    with pytest.raises(TypeError, match="'layout' must be an array"):
        multiscales_r2.validate({"layout": "nope"})


def test_r2_validate_entry_not_object() -> None:
    with pytest.raises(TypeError, match=r"layout\[0\] must be an object"):
        multiscales_r2.validate({"layout": ["not-an-object"]})


def test_multiscales_unknown_revision_label() -> None:
    with pytest.raises(ValueError, match="Unknown revision"):
        multiscales.create(layout=[{"asset": "0"}], revision="bogus")
