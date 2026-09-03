from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from conftest import as_sequence, wrap_attrs
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

from zarr_cm import JSONDict, StacLink, stac

# The stac schema's stac:item/stac:collection fields are a `oneOf` between the
# v1.0.0 and v1.1.0 STAC item/collection schemas. zarr-cm does not validate
# STAC Item/Collection structure itself (any JSON object passes), so resolve
# those references to stubs rather than fetch them -- but `oneOf` requires
# exactly one match, so the pair can't both be accept-anything (`{}`) or every
# instance would match both and `oneOf` would always fail. Stub v1.0.0 as
# accept-anything and v1.1.0 as reject-everything: which one "wins" is
# arbitrary, only that exactly one does.
_STUBS: list[tuple[str, dict[str, object]]] = [
    ("https://schemas.stacspec.org/v1.0.0/item-spec/json-schema/item.json", {}),
    (
        "https://schemas.stacspec.org/v1.1.0/item-spec/json-schema/item.json",
        {"not": {}},
    ),
    (
        "https://schemas.stacspec.org/v1.0.0/collection-spec/json-schema/collection.json",
        {},
    ),
    (
        "https://schemas.stacspec.org/v1.1.0/collection-spec/json-schema/collection.json",
        {"not": {}},
    ),
]
_EXTERNAL: Registry[Any] = Registry().with_resources(  # type: ignore[assignment]
    (url, Resource.from_contents(schema, default_specification=DRAFT7))
    for url, schema in _STUBS
)


def test_create_item() -> None:
    item: JSONDict = {"type": "Feature", "id": "example"}
    result = stac.create(item=item)
    assert result == {"stac:item": item}


def test_create_collection() -> None:
    collection: JSONDict = {"type": "Collection", "id": "example"}
    result = stac.create(collection=collection)
    assert result == {"stac:collection": collection}


def test_create_key() -> None:
    result = stac.create(key="stac.json")
    assert result == {"stac:key": "stac.json"}


def test_create_link() -> None:
    link: StacLink = {"href": "https://example.com/item.json"}
    result = stac.create(link=link)
    assert result == {"stac:link": link}


def test_create_rejects_zero_fields() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        stac.create()


def test_create_rejects_multiple_fields() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        stac.create(key="stac.json", link={"href": "https://example.com/item.json"})


def test_validate_link_missing_href() -> None:
    with pytest.raises(ValueError, match="missing required key 'href'"):
        stac.validate({"stac:link": {"rel": "self"}})


def test_validate_link_wrong_href_type() -> None:
    with pytest.raises(TypeError, match=r"'stac:link\.href' must be a string"):
        stac.validate({"stac:link": {"href": 1}})


def test_validate_item_wrong_type() -> None:
    with pytest.raises(TypeError, match="'stac:item' must be a JSON object"):
        stac.validate({"stac:item": "not-an-object"})


def test_validate_key_wrong_type() -> None:
    with pytest.raises(TypeError, match="'stac:key' must be a string"):
        stac.validate({"stac:key": 1})


def test_insert_and_extract_roundtrip() -> None:
    data = stac.create(key="stac.json")
    inserted = stac.insert({"foo": "bar"}, data)
    assert inserted["stac:key"] == "stac.json"
    assert stac.CMO in as_sequence(inserted["zarr_conventions"])
    remaining, extracted = stac.extract(inserted)
    assert extracted == data
    assert remaining == {"foo": "bar"}


def test_insert_collision_raises() -> None:
    attrs = {"stac:key": "other.json"}
    data = stac.create(key="stac.json")
    with pytest.raises(ValueError, match="overwritten"):
        stac.insert(attrs, data)


def test_extract_missing_convention() -> None:
    attrs = {"foo": "bar"}
    remaining, extracted = stac.extract(attrs)
    assert remaining == {"foo": "bar"}
    assert extracted == {}


def test_detect_known_revision() -> None:
    attrs = stac.insert({}, stac.create(key="stac.json"))
    assert stac.detect(attrs) == "v0.1"


def test_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="stac"):
        stac.detect({})


def test_group_only_group_metadata_validates() -> None:
    attrs = stac.create_convention_attrs(key="stac.json")
    node: Any = wrap_attrs(attrs, node_type="group")
    assert stac.validate_group_metadata(node) == node


def test_group_only_array_metadata_rejected() -> None:
    attrs = stac.create_convention_attrs(key="stac.json")
    node: Any = wrap_attrs(attrs, node_type="array")
    with pytest.raises(ValueError, match="does not apply to array nodes"):
        stac.validate_array_metadata(node)


def test_group_only_node_metadata_rejects_array() -> None:
    attrs = stac.create_convention_attrs(key="stac.json")
    node: Any = wrap_attrs(attrs, node_type="array")
    with pytest.raises(ValueError, match="does not apply to array nodes"):
        stac.validate_node_metadata(node)


# ---------------------------------------------------------------------------
# Vendored schema fixture test
# ---------------------------------------------------------------------------

SCHEMA_PATH = Path(__file__).parent / "schemas" / "stac.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text())


def _conforms(node: dict[str, object]) -> None:
    validator = jsonschema.Draft7Validator(SCHEMA, registry=_EXTERNAL)
    validator.validate(node)  # type: ignore[reportUnknownMemberType]


def test_create_item_validates_against_vendored_schema() -> None:
    data = stac.create(item={"type": "Feature", "id": "example"})
    node = wrap_attrs(stac.insert({}, data), node_type="group")
    _conforms(node)


def test_create_key_validates_against_vendored_schema() -> None:
    data = stac.create(key="stac.json")
    node = wrap_attrs(stac.insert({}, data), node_type="group")
    _conforms(node)


def test_create_link_validates_against_vendored_schema() -> None:
    data = stac.create(link={"href": "https://example.com/item.json"})
    node = wrap_attrs(stac.insert({}, data), node_type="group")
    _conforms(node)
