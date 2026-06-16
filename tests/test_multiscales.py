from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from conftest import wrap_attrs

from zarr_cm import multiscales
from zarr_cm.multiscales import CMO, MultiscalesAttrs
from zarr_cm.multiscales import r1 as multiscales_r1
from zarr_cm.multiscales import r2 as multiscales_r2

SCHEMA_PATH = Path(__file__).parent / "schemas" / "multiscales.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def test_insert_multiscales_minimal() -> None:
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert({}, data)
    assert result["multiscales"]["layout"] == [{"asset": "0"}]
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
    assert len(result["multiscales"]["layout"]) == 2


def test_insert_preserves_existing_attrs() -> None:
    attrs = {"foo": "bar"}
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert(attrs, data)
    assert result["foo"] == "bar"


def test_insert_appends_to_existing_conventions() -> None:
    attrs = {"zarr_conventions": [{"uuid": "other-uuid"}]}
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert(attrs, data)
    assert len(result["zarr_conventions"]) == 2


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

# The vendored v0.1 schema pins conventionMetadata's schema_url/spec_url to the
# `refs/tags/v0.1` release URLs via `const`, and (unlike the spatial schema) its
# `attributes` subschema has no sibling `$ref`, so the `zarr_conventions` ->
# conventionMetadata check IS enforced. Our r2 CMO deliberately commit-pins those
# URLs (so detection round-trips), so it does not match the tag-pinned const.
# These schema-conformance tests target the multiscales DATA shape, so we swap in
# the tag-form CMO the schema expects; the commit-pinned form is asserted by
# test_r2_schema_url_pinned_to_v0_1 below.
_R2_TAG_CMO = {
    **CMO,
    "schema_url": "https://raw.githubusercontent.com/zarr-conventions/multiscales/refs/tags/v0.1/schema.json",
    "spec_url": "https://github.com/zarr-conventions/multiscales/blob/v0.1/README.md",
}


def _with_tag_cmo(result: dict[str, object]) -> dict[str, object]:
    return {**result, "zarr_conventions": [_R2_TAG_CMO]}


def test_schema_validation_minimal() -> None:
    data: MultiscalesAttrs = {"layout": [{"asset": "0"}]}
    result = multiscales.insert({}, data)
    node = wrap_attrs(_with_tag_cmo(result), node_type="group")
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
    node = wrap_attrs(_with_tag_cmo(result), node_type="group")
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
    assert "9b78efa75fef0fed302d9cf880037c569354d860" in multiscales_r2.SCHEMA_URL
    assert "refs/tags/v1" not in multiscales_r2.SCHEMA_URL


def test_r1_keeps_legacy_url() -> None:
    assert "refs/tags/v1" in multiscales_r1.SCHEMA_URL


def test_r2_create_validates_against_vendored_schema() -> None:
    # Asserts our r2 output conforms to the v0.1 multiscales DATA shape. The
    # vendored schema enforces conventionMetadata's tag-pinned const, which our
    # commit-pinned CMO does not match, so we swap in the tag-form CMO (see
    # _with_tag_cmo); the commit-pinned form is covered by
    # test_r2_schema_url_pinned_to_v0_1.
    data = multiscales.create(layout=[{"asset": "0"}])
    node = wrap_attrs(_with_tag_cmo(multiscales.insert({}, data)), node_type="group")
    jsonschema.validate(node, R2_SCHEMA)


def test_multiscales_revision_roundtrip() -> None:
    r1_doc = multiscales.insert(
        {}, multiscales.create(layout=[{"asset": "0"}], revision="r1"), revision="r1"
    )
    assert multiscales.detect(r1_doc) == "r1"
    _, data = multiscales.extract(r1_doc, revision="r1")
    assert data["layout"] == [{"asset": "0"}]
