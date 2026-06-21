"""Downstream pydantic integration regression test for issue #18.

A pydantic model that embeds one of zarr-cm's convention ``TypedDict``s (which
use ``JsonValue`` as PEP 728 ``extra_items``) used to raise ``RecursionError``
in ``model_rebuild()``, because ``JsonValue`` was an implicit recursive union
(``X = ... "X" ...``) rather than a real ``TypeAliasType``. pydantic can only
resolve a recursive alias when it is a ``TypeAliasType`` (the PEP 695 ``type``
form, or its ``typing_extensions`` equivalent).

These tests use ``from __future__ import annotations`` deliberately: that turns
every annotation into a string, which is exactly the configuration that triggers
the bug and is extremely common in real downstream code. They run under the full
CI Python matrix (3.11 / 3.14 / pypy-3.11), so both the native ``type`` alias
(3.12+) and the ``TypeAliasType`` fallback (3.11) are exercised.
"""

from __future__ import annotations

import pytest

# Imported at runtime (not under TYPE_CHECKING): pydantic resolves these as live
# field annotations during model_rebuild(), which is the whole point here.
from zarr_cm import ConventionMetadataObject, SpatialAttrs  # noqa: TC001

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
    """``extra_items=JsonValue`` keys must validate as recursive JSON values."""

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
    assert node.attributes["spatial:dimensions"] == ["y", "x"]
