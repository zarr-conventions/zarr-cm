"""`create_convention_attrs`: one convention's data plus its declaration.

`create` returns convention keys alone, with no `zarr_conventions` entry, so
the data it returns does not yet declare itself. Getting a usable attributes
dict out of it used to mean `insert({}, create(...))` -- borrowing the
compose-into-existing-attributes operation to build something stand-alone.
"""

from __future__ import annotations

from typing import Any

import pytest

from zarr_cm import license as license_
from zarr_cm import multiscales, proj, spatial, uom
from zarr_cm._core import validate_json_object

# (module, kwargs) pairs covering every convention.
CASES: list[tuple[Any, dict[str, Any]]] = [
    (spatial, {"dimensions": ["y", "x"]}),
    (spatial, {"bbox": [0.0, 0.0, 1.0, 1.0]}),
    (proj, {"code": "EPSG:4326"}),
    (multiscales, {"layout": ({"asset": "0"},)}),
    (license_, {"spdx": "MIT"}),
    (uom, {"ucum": {"unit": "m"}}),
]


def test_matches_insert_into_empty_attrs() -> None:
    """The result equals the `insert({}, create(...))` it replaces, exactly."""
    for module, kwargs in CASES:
        assert module.create_convention_attrs(**kwargs) == module.insert(
            {}, module.create(**kwargs)
        )


def test_declares_exactly_one_convention() -> None:
    """A stand-alone dict carries its own CMO and no others."""
    for module, kwargs in CASES:
        attrs = module.create_convention_attrs(**kwargs)
        assert attrs["zarr_conventions"] == [module.CMO]


def test_round_trips_through_extract() -> None:
    for module, kwargs in CASES:
        attrs = module.create_convention_attrs(**kwargs)
        remaining, data = module.extract(attrs)
        assert remaining == {}
        assert data == module.create(**kwargs)


def test_validates_as_node_metadata() -> None:
    """The result is directly usable as a node's `attributes`."""
    for module, kwargs in CASES:
        attrs = module.create_convention_attrs(**kwargs)
        node: Any = {"zarr_format": 3, "node_type": "group", "attributes": attrs}
        expected = {**node, "attributes": validate_json_object(attrs)}
        validated = module.validate_group_metadata(node)
        assert validated == expected
        assert validated is not node


def test_revision_can_be_pinned() -> None:
    attrs = spatial.create_convention_attrs(dimensions=["y", "x"], revision="r2")
    assert attrs["zarr_conventions"] == [spatial.r2.CMO]
    assert spatial.detect(attrs) == "r2"


def test_invalid_data_rejected() -> None:
    """It validates on the way out, like `create` does."""
    with pytest.raises(ValueError, match="exactly 2"):
        spatial.create_convention_attrs(dimensions=["z", "y", "x"])


def test_missing_required_data_rejected() -> None:
    with pytest.raises(ValueError, match="At least one of"):
        license_.create_convention_attrs()


def test_unknown_revision_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown revision"):
        spatial.create_convention_attrs(dimensions=["y", "x"], revision="r99")
