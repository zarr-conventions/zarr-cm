"""Static-typing contract tests for the public aggregate API.

These tests are primarily exercised by pyright (run over `tests` in strict mode);
they also run under pytest to confirm the runtime behavior matches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import zarr_cm

if TYPE_CHECKING:
    from collections.abc import Mapping

    from zarr_metadata import ZarrV3ArrayMetadataJSON, ZarrV3GroupMetadataJSON

from zarr_cm import (
    ArrayMetadata,
    ConventionName,
    GeoProjAttrs,
    GroupMetadata,
    JSONDict,
    JSONValue,
    Metadata,
    SpatialAttrs,
    SpatialConventionAttrs,
    create_many,
    insert_many,
    spatial,
)


def test_json_aliases_are_public() -> None:
    # (1) Referencing the public aliases must type-check (and resolve at runtime).
    d: JSONDict = {"a": 1}
    v: JSONValue = [1, "b", {"c": True}]
    assert d == {"a": 1}
    assert v == [1, "b", {"c": True}]


def test_create_many_accepts_convention_typeddicts() -> None:
    # (2) Passing a mapping of the package's own exported TypedDicts must
    # type-check with no cast and no suppression comment.
    spatial_attrs: SpatialAttrs = {"spatial:dimensions": ["x", "y"]}
    proj: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    conv: dict[ConventionName, SpatialAttrs | GeoProjAttrs] = {
        "spatial": spatial_attrs,
        "geo-proj": proj,
    }
    result = create_many(conv)
    assert "proj:code" in result


def test_insert_many_accepts_convention_typeddicts() -> None:
    # (3)
    proj: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    conv: dict[ConventionName, GeoProjAttrs] = {"geo-proj": proj}
    result = insert_many({}, conv)
    assert "proj:code" in result


def _group_doc() -> GroupMetadata[Mapping[str, JSONValue]]:
    """A group document at the wide type: attributes are just a JSON object."""
    attrs = spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0])
    return {"zarr_format": 3, "node_type": "group", "attributes": attrs}


def test_validation_narrows_the_attributes_type() -> None:
    """(4) Validating narrows `Metadata[Mapping]` to `Metadata[TheConvention]`.

    A signature can require a document validated against a specific convention,
    and the narrowed value keeps its field types -- `attributes` is the
    convention's own TypedDict rather than an untyped JSON object.

    The commented-out line is the point: the wide document does not satisfy the
    narrowed parameter, so a forgotten validation call is caught by pyright
    rather than reaching a writer. pyright runs over `tests` in strict mode,
    so uncommenting it fails `just typecheck`.
    """
    group_doc = _group_doc()

    def writes_spatial_group(
        node: Metadata[SpatialConventionAttrs],
    ) -> SpatialConventionAttrs:
        # Field access on the narrowed value is fully typed.
        return node["attributes"]

    # writes_spatial_group(group_doc)   # wide document: type error
    narrowed = spatial.validate_group_metadata(group_doc)
    attrs = writes_spatial_group(narrowed)
    assert attrs.get("spatial:bbox") == [0.0, 0.0, 1.0, 1.0]
    assert narrowed == group_doc
    assert narrowed is not group_doc  # validation returns normalized containers


def test_narrowed_documents_chain_and_widen() -> None:
    """(5) A narrowed document still satisfies the wide input forms.

    The `attributes` type parameter is covariant (the field is `ReadOnly`), so
    `Metadata[SpatialConventionAttrs]` is assignable to
    `Metadata[Mapping[str, JSONValue]]`, and validators chain.

    Narrowing does not accumulate: each single-convention validator returns its
    own convention's type, and there is no intersection type to combine two of
    them.
    """
    narrowed = spatial.validate_group_metadata(_group_doc())

    def takes_wide(node: Metadata[Mapping[str, JSONValue]]) -> None:
        assert node["node_type"] in {"array", "group"}

    takes_wide(narrowed)
    again = spatial.validate_group_metadata(narrowed)
    assert again == narrowed
    assert again is not narrowed


def test_jsonvalue_is_zarr_metadata_jsonvalue() -> None:
    """(6) One definition of "a JSON value" across both packages.

    `zarr_cm.JSONValue` *is* `zarr_metadata.JSONValue` -- the same
    `TypeAliasType` object re-exported, not a lookalike -- so the two packages'
    types unify instead of being structurally-similar strangers.
    """
    import zarr_metadata  # noqa: PLC0415

    assert zarr_cm.JSONValue is zarr_metadata.JSONValue


def test_unifies_with_zarr_metadata_documents() -> None:
    """(7) zarr-cm attributes flow into zarr-metadata documents without casts.

    zarr-cm used to define its own recursive JSON alias, which pyright would
    not unify with zarr-metadata's, so building a `ZarrV3GroupMetadataJSON`
    from a zarr-cm attributes dict needed a cast. With one shared `JSONValue`
    this must type-check bare.
    """
    attrs = spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0])
    doc: ZarrV3GroupMetadataJSON = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": attrs,
    }
    # ...and zarr-metadata documents flow into our validators.
    narrowed = spatial.validate_group_metadata(doc)
    assert narrowed == doc
    assert narrowed is not doc


def test_array_validation_preserves_base_metadata_types() -> None:
    attrs = spatial.create_convention_attrs(dimensions=["y", "x"])
    doc: ZarrV3ArrayMetadataJSON = {
        "zarr_format": 3,
        "node_type": "array",
        "data_type": "float64",
        "shape": (100, 200),
        "chunk_grid": {"name": "regular"},
        "chunk_key_encoding": {"name": "default"},
        "fill_value": 0.0,
        "codecs": ({"name": "bytes"},),
        "attributes": attrs,
    }

    validated = spatial.validate_array_metadata(doc, revision="r3")

    def consume(value: ArrayMetadata[SpatialConventionAttrs]) -> None:
        node_type: Literal["array"] = value["node_type"]
        shape: tuple[int, ...] = value["shape"]
        assert node_type == "array"
        assert shape == (100, 200)

    consume(validated)


def test_group_validation_preserves_node_discriminator() -> None:
    validated = spatial.validate_group_metadata(_group_doc(), revision="r3")

    def consume(value: GroupMetadata[SpatialConventionAttrs]) -> None:
        node_type: Literal["group"] = value["node_type"]
        assert node_type == "group"

    consume(validated)
