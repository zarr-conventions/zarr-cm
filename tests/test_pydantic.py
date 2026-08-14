"""Downstream pydantic integration regression test for issue #18.

A pydantic model that embeds one of zarr-cm's convention `TypedDict`s (which
use `JSONValue` as PEP 728 `extra_items`) used to raise `RecursionError`
in `model_rebuild()`, because `JSONValue` was an implicit recursive union
(`X = ... "X" ...`) rather than a real `TypeAliasType`. pydantic can only
resolve a recursive alias when it is a `TypeAliasType` (the PEP 695 `type`
form, or its `typing_extensions` equivalent).

These tests use `from __future__ import annotations` deliberately: that turns
every annotation into a string, which is exactly the configuration that triggers
the bug and is extremely common in real downstream code. They run under the full
CI Python matrix (3.11 / 3.14 / pypy-3.11), so both the native `type` alias
(3.12+) and the `TypeAliasType` fallback (3.11) are exercised.
"""

from __future__ import annotations

import pytest

# Imported at runtime (not under TYPE_CHECKING): pydantic resolves these as live
# field annotations during model_rebuild(), which is the whole point here.
import zarr_cm
from zarr_cm import ConventionMetadataObject, SpatialAttrs

pydantic = pytest.importorskip("pydantic")
BaseModel = pydantic.BaseModel


def test_model_with_cmo_tuple_rebuilds() -> None:
    """The minimal repro from issue #18: a model field of CMO objects."""

    class M(BaseModel):
        convs: tuple[ConventionMetadataObject, ...]

    M.model_rebuild()  # used to raise RecursionError
    m = M(convs=({"uuid": "abc"},))
    assert m.convs[0].get("uuid") == "abc"


def test_model_with_cmo_validates_nested_extra_items() -> None:
    """`extra_items=JSONValue` keys must validate as recursive JSON values."""

    class M(BaseModel):
        convs: tuple[ConventionMetadataObject, ...]

    M.model_rebuild()
    m = M(convs=({"uuid": "abc", "extra": {"a": [1, "x", {"b": None}]}},))
    assert m.convs[0].get("extra") == {"a": [1, "x", {"b": None}]}


def test_model_with_convention_attrs_typeddict_rebuilds() -> None:
    """A real convention attrs TypedDict embedded in a model must also rebuild."""

    class Node(BaseModel):
        attributes: SpatialAttrs

    Node.model_rebuild()  # used to raise RecursionError
    node = Node(attributes={"spatial:dimensions": ["y", "x"]})
    assert node.attributes.get("spatial:dimensions") == ["y", "x"]


# Every public TypedDict, by module -- except generic `Metadata`: pydantic
# accepts it but emits a
# UserWarning for their `ReadOnly` field, which this suite's
# `filterwarnings = error` would turn into a failure. A class-form TypedDict under
# `from __future__ import annotations` stores its annotations as strings, so
# every name they mention has to be importable at RUNTIME from the defining
# module -- pydantic evaluates them in that module's namespace. Parking one of
# them behind `if TYPE_CHECKING:` type-checks fine and then fails downstream,
# which is what this test is here to catch.
_TYPED_DICTS = [
    (zarr_cm, "ConventionMetadataObject"),
    (zarr_cm, "ConventionAttrs"),
    (zarr_cm, "MultiConventionAttrs"),
    (zarr_cm, "SpatialAttrs"),
    (zarr_cm, "SpatialConventionAttrs"),
    (zarr_cm, "SpatialAttrsR2"),
    (zarr_cm, "SpatialConventionAttrsR2"),
    (zarr_cm, "SpatialAttrsR3"),
    (zarr_cm, "SpatialConventionAttrsR3"),
    (zarr_cm, "GeoProjAttrs"),
    (zarr_cm, "GeoProjConventionAttrs"),
    (zarr_cm, "GeoProjAttrsR2"),
    (zarr_cm, "GeoProjConventionAttrsR2"),
    (zarr_cm, "GeoProjAttrsR3"),
    (zarr_cm, "GeoProjConventionAttrsR3"),
    (zarr_cm, "Transform"),
    (zarr_cm, "LayoutObject"),
    (zarr_cm, "MultiscalesAttrs"),
    (zarr_cm, "MultiscalesConventionAttrs"),
    (zarr_cm, "LicenseAttrs"),
    (zarr_cm, "LicenseConventionAttrs"),
    (zarr_cm, "UCUM"),
    (zarr_cm, "UomAttrs"),
    (zarr_cm, "UomConventionAttrs"),
]


@pytest.mark.parametrize("name", [name for _mod, name in _TYPED_DICTS])
def test_every_public_typeddict_rebuilds(name: str) -> None:
    """Every exported TypedDict must be usable as a pydantic model field."""
    typed_dict = getattr(zarr_cm, name)

    class M(BaseModel):
        attributes: typed_dict  # type: ignore[valid-type]

    M.model_rebuild()
