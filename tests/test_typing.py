"""Static-typing contract tests for the public aggregate API.

These tests are primarily exercised by pyright (run over ``tests`` in strict mode);
they also run under pytest to confirm the runtime behavior matches.
"""

from __future__ import annotations

# (1) JsonValue / JsonDict must be importable from the public package, not _core.
from zarr_cm import (
    ConventionName,
    GeoProjAttrs,
    JsonDict,
    JsonValue,
    SpatialAttrs,
    create_many,
    insert_many,
)


def test_json_aliases_are_public() -> None:
    # Referencing the public aliases must type-check (and resolve at runtime).
    d: JsonDict = {"a": 1}
    v: JsonValue = [1, "b", {"c": True}]
    assert d == {"a": 1}
    assert v == [1, "b", {"c": True}]


def test_create_many_accepts_convention_typeddicts() -> None:
    # (2) Passing a mapping of the package's own exported TypedDicts must
    # type-check with no cast and no ``# type: ignore``.
    spatial: SpatialAttrs = {"spatial:dimensions": ["x", "y"]}
    proj: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    conv: dict[ConventionName, SpatialAttrs | GeoProjAttrs] = {
        "spatial": spatial,
        "geo-proj": proj,
    }
    result = create_many(conv)
    assert "proj:code" in result


def test_insert_many_accepts_convention_typeddicts() -> None:
    proj: GeoProjAttrs = {"proj:code": "EPSG:4326"}
    conv: dict[ConventionName, GeoProjAttrs] = {"geo-proj": proj}
    result = insert_many({}, conv)
    assert "proj:code" in result
