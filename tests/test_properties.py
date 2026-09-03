"""Invariants that hold for every revision of every convention.

Each test draws a revision (see `strategies.REVISIONS`) and valid data for it,
then checks a property of the public API that must not depend on *which*
convention or revision it is. The point tests elsewhere show that a specific
input behaves; these show that a *class* of inputs does, and that no revision
is quietly exempt.
"""

from __future__ import annotations

import json
from typing import Any

import jsonschema
import pytest
from conftest import as_sequence, wrap_attrs
from hypothesis import given, settings
from hypothesis import strategies as st
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7
from strategies import (
    REVISIONS,
    Revision,
    foreign_attrs,
    foreign_declarations,
    revision_pairs,
    revision_selections,
    revisions,
)

import zarr_cm
from zarr_cm import CanonicalConventionName, ConventionName

# Every property runs the whole registry, so a modest example budget per
# property still covers each revision many times over.
settings.register_profile("zarr_cm", max_examples=60, deadline=None)
settings.load_profile("zarr_cm")


# The proj schemas `$ref` PROJ's own PROJJSON schema by URL, and the stac
# schema `$ref`s STAC's own item/collection schemas as a `oneOf` between their
# v1.0.0 and v1.1.0 versions. zarr-cm does not validate PROJJSON or STAC
# Item/Collection structure itself (any JSON object passes), so resolve those
# references to stubs rather than fetch them -- but `oneOf` requires exactly
# one match, so the stac pair can't both be accept-anything (`{}`) or every
# instance would match both and `oneOf` would always fail. Stub each pair's
# v1.0.0 member as accept-anything and its v1.1.0 member as reject-everything:
# which one "wins" is arbitrary, only that exactly one does.
_STUBS: list[tuple[str, dict[str, Any]]] = [
    ("https://proj.org/schemas/v0.7/projjson.schema.json", {}),
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


def conforms(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = jsonschema.Draft7Validator(schema, registry=_EXTERNAL)
    validator.validate(instance)  # type: ignore[reportUnknownMemberType]


def declared(attrs: dict[str, Any], uuid: str) -> list[dict[str, Any]]:
    """The `zarr_conventions` entries claiming *uuid*."""
    return [c for c in attrs["zarr_conventions"] if c.get("uuid") == uuid]


def roundtrip(value: Any) -> Any:
    return json.loads(json.dumps(value))


# --- create / validate --------------------------------------------------------


@given(revisions, st.data())
def test_create_output_validates_under_its_own_revision(
    rev: Revision, data: st.DataObject
) -> None:
    created = rev.module.create(**data.draw(rev.kwargs))
    assert rev.module.validate(created) == created
    if rev.label is not None:
        assert rev.package.validate(created, revision=rev.label) == created


@given(revisions, st.data())
def test_generated_data_matches_the_upstream_schema(
    rev: Revision, data: st.DataObject
) -> None:
    """The generators are honest: what they produce is valid per upstream too."""
    attrs = rev.module.create_convention_attrs(**data.draw(rev.kwargs))
    conforms(wrap_attrs(attrs, node_type=rev.node_type), rev.schema)


@given(revisions, st.data())
def test_create_convention_attrs_is_insert_into_nothing(
    rev: Revision, data: st.DataObject
) -> None:
    kwargs = data.draw(rev.kwargs)
    assert rev.module.create_convention_attrs(**kwargs) == rev.module.insert(
        {}, rev.module.create(**kwargs)
    )


# --- detect / validate / extract on what we wrote ---------------------------------


@given(revisions, st.data(), foreign_attrs)
def test_insert_then_extract_is_identity(
    rev: Revision, data: st.DataObject, foreign: dict[str, Any]
) -> None:
    created = rev.module.create(**data.draw(rev.kwargs))
    inserted = rev.module.insert(foreign, created)
    remaining, extracted = rev.module.extract(inserted)
    assert extracted == created
    assert remaining == foreign
    assert inserted["zarr_conventions"] == [rev.module.CMO]
    assert "zarr_conventions" not in foreign  # the input was not mutated


@given(revisions, st.data(), foreign_attrs)
def test_written_documents_are_read_back_at_the_same_revision(
    rev: Revision, data: st.DataObject, foreign: dict[str, Any]
) -> None:
    created = rev.module.create(**data.draw(rev.kwargs))
    attrs = rev.module.insert(foreign, created)
    if rev.label is not None:
        # auto-detect agrees with the pin, and both agree with what was written
        assert rev.package.detect(attrs) == rev.label
        assert rev.package.extract(attrs) == rev.package.extract(
            attrs, revision=rev.label
        )
        assert rev.package.extract(attrs)[1] == created
    assert zarr_cm.validate_many(attrs, [rev.convention]) is attrs
    assert zarr_cm.detect_revisions(attrs) == (
        {rev.convention: rev.label}
        if rev.label is not None
        else {rev.convention: rev.package.detect(attrs)}
    )
    assert zarr_cm.validate_all(attrs) is attrs
    remaining, extracted = zarr_cm.extract_all(attrs)
    assert remaining == foreign
    assert extracted == {rev.convention: created}


@given(revisions, st.data(), foreign_attrs)
def test_json_round_trip_preserves_everything(
    rev: Revision, data: st.DataObject, foreign: dict[str, Any]
) -> None:
    """What we write survives serialization: the on-disk form reads identically."""
    created = rev.module.create(**data.draw(rev.kwargs))
    attrs = rev.module.insert(foreign, created)
    reloaded = roundtrip(attrs)
    assert reloaded == attrs
    assert rev.module.extract(reloaded) == (foreign, created)
    if rev.label is not None:
        assert rev.package.detect(reloaded) == rev.label


@given(revisions, st.data(), foreign_attrs)
def test_node_level_validation_accepts_what_we_write(
    rev: Revision, data: st.DataObject, foreign: dict[str, Any]
) -> None:
    created = rev.module.create(**data.draw(rev.kwargs))
    attrs = rev.module.insert(foreign, created)
    node = wrap_attrs(attrs, node_type=rev.node_type)
    validated = rev.module.validate_node_metadata(node)  # type: ignore[arg-type]
    assert validated["attributes"] == attrs
    if rev.label is not None:
        assert rev.package.validate_node_metadata(node)["attributes"] == attrs
        assert (
            rev.package.validate_node_metadata(node, revision=rev.label)["attributes"]
            == attrs
        )


# --- declarations: aliases, schema_url-only, merging -----------------------------------


@given(revisions, st.data())
def test_every_recognized_schema_url_reads_as_this_revision(
    rev: Revision, data: st.DataObject
) -> None:
    """Canonical or alias, uuid or not: each recognized URL selects this revision."""
    attrs = rev.module.create_convention_attrs(**data.draw(rev.kwargs))
    url = data.draw(st.sampled_from(sorted(rev.module.RECOGNIZED_SCHEMA_URLS)))
    with_uuid = data.draw(st.booleans())
    declaration = {"schema_url": url} | ({"uuid": rev.module.UUID} if with_uuid else {})
    attrs["zarr_conventions"] = [declaration]
    node = wrap_attrs(attrs, node_type=rev.node_type)

    if rev.label is not None:
        assert rev.package.detect(attrs) == rev.label
        assert rev.package.extract(attrs) == rev.package.extract(
            attrs, revision=rev.label
        )
        assert (
            rev.package.validate_node_metadata(node, revision=rev.label)["attributes"]
            == attrs
        )
    else:
        assert rev.package.detect(attrs) is not None
    rev.module.validate_node_metadata(node)  # type: ignore[arg-type]
    assert zarr_cm.detect_revisions(attrs) == {
        rev.convention: rev.package.detect(attrs)
    }
    zarr_cm.validate_all(attrs)
    remaining, extracted = zarr_cm.extract_all(attrs)
    assert remaining == {}
    assert set(extracted) == {rev.convention}


@given(revisions, st.data(), foreign_attrs, foreign_declarations)
def test_insert_keeps_every_foreign_declaration_and_declares_itself_once(
    rev: Revision,
    data: st.DataObject,
    foreign: dict[str, Any],
    others: list[dict[str, str]],
) -> None:
    kwargs = data.draw(rev.kwargs)
    created = rev.module.create(**kwargs)
    start = {**foreign, "zarr_conventions": list(others)}
    # ...whether the data comes bare or as a stand-alone attributes dict.
    payload = (
        created
        if data.draw(st.booleans())
        else rev.module.create_convention_attrs(**kwargs)
    )
    result = rev.module.insert(start, payload)  # type: ignore[arg-type]

    assert result["zarr_conventions"][: len(others)] == others
    assert declared(result, rev.module.UUID) == [rev.module.CMO]
    assert len(result["zarr_conventions"]) == len(others) + 1
    if rev.label is not None:
        assert rev.package.detect(result) == rev.label


@given(revision_pairs(), st.data(), foreign_declarations)
def test_reinserting_at_another_revision_supersedes_the_declaration(
    pair: tuple[Revision, Revision], data: st.DataObject, others: list[dict[str, str]]
) -> None:
    first, second = pair
    start = {"zarr_conventions": list(others)}
    once = first.module.insert(start, first.module.create(**data.draw(first.kwargs)))
    twice = second.module.insert(
        once, second.module.create(**data.draw(second.kwargs)), overwrite=True
    )

    assert declared(twice, second.module.UUID) == [second.module.CMO]
    assert twice["zarr_conventions"][: len(others)] == others
    assert len(twice["zarr_conventions"]) == len(others) + 1
    assert second.package.detect(twice) == second.label
    # and the position of the declaration is stable across the swap
    assert [c.get("uuid") for c in once["zarr_conventions"]] == [
        c.get("uuid") for c in twice["zarr_conventions"]
    ]


# --- many conventions at once ---------------------------------------------------------


@given(revision_selections(), st.data(), foreign_attrs)
def test_create_many_composes_and_decomposes(
    selection: dict[CanonicalConventionName, Revision],
    data: st.DataObject,
    foreign: dict[str, Any],
) -> None:
    payload: dict[ConventionName, Any] = {
        name: rev.module.create(**data.draw(rev.kwargs))
        for name, rev in selection.items()
    }
    pins: dict[ConventionName, str] = {
        name: rev.label for name, rev in selection.items() if rev.label is not None
    }

    attrs = zarr_cm.insert_many(foreign, payload, revisions=pins)
    assert zarr_cm.create_many(payload, revisions=pins) == zarr_cm.insert_many(
        {}, payload, revisions=pins
    )

    # every chosen convention is declared exactly once, at the chosen revision
    assert [c["uuid"] for c in as_sequence(attrs["zarr_conventions"])] == [  # type: ignore[index]
        rev.module.UUID for rev in selection.values()
    ]
    assert zarr_cm.detect_revisions(attrs) == {
        name: (rev.label if rev.label is not None else rev.package.detect(attrs))
        for name, rev in selection.items()
    }
    assert zarr_cm.validate_all(attrs) is attrs
    assert zarr_cm.validate_many(attrs, list(selection), revisions=pins) is attrs  # type: ignore[arg-type]

    remaining, extracted = zarr_cm.extract_all(attrs)
    assert remaining == foreign
    assert extracted == payload
    assert zarr_cm.extract_many(attrs, list(selection)) == (foreign, payload)  # type: ignore[arg-type]

    # ...and the on-disk form says the same
    assert zarr_cm.extract_all(roundtrip(attrs)) == (foreign, payload)


@pytest.mark.parametrize("rev", REVISIONS, ids=repr)
def test_registry_covers_every_revision(rev: Revision) -> None:
    """The strategy registry and the package's own registry agree."""
    assert rev.convention in zarr_cm.CONVENTION_NAMES
    if rev.label is None:
        assert rev.convention not in zarr_cm.latest_revisions()
    else:
        assert rev.label in rev.package.REVISION_BY_SCHEMA_URL.values()
        assert (
            zarr_cm.convention_metadata(rev.convention, revision=rev.label)
            == rev.module.CMO
        )


@pytest.mark.parametrize("rev", REVISIONS, ids=repr)
def test_upstream_schema_id_is_a_recognized_url(rev: Revision) -> None:
    """A revision recognizes the URL upstream publishes as its schema's identity.

    The `$id` of the vendored schema is the URL the spec's own README tells
    writers to declare, so a document that follows upstream to the letter must
    read as this revision -- whether the `$id` is our canonical URL or an alias.
    """
    schema_id = rev.schema.get("$id")
    if schema_id is None:
        pytest.skip("upstream schema declares no $id")
    assert schema_id in rev.module.RECOGNIZED_SCHEMA_URLS
    if rev.label is None:
        # Unrevisioned conventions (license, uom, stac) expose no `revision=`
        # kwarg, so there is no public label to compare against -- just
        # confirm the schema's own $id is one this module recognizes as itself.
        assert schema_id in rev.package.REVISION_BY_SCHEMA_URL
    else:
        assert rev.package.REVISION_BY_SCHEMA_URL.get(schema_id) == rev.label
