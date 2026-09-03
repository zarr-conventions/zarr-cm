"""Example: the stac convention.

Run: `python examples/stac/stac.py`. Demonstrates create / read-unknown /
group-only enforcement. Stac has a single revision today (identity migrate
scaffold, like license/uom).
"""

from __future__ import annotations

from typing import Any

from zarr_cm import stac


def workflow_create_item() -> dict[str, Any]:
    """1. Create new stac data embedding a complete STAC Item (`stac:item`)."""
    item = {
        "type": "Feature",
        "stac_version": "1.1.0",
        "id": "example-item",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "bbox": [-1, -1, 1, 1],
        "properties": {"datetime": "2024-01-01T00:00:00Z"},
        "links": [],
        "assets": {"data": {"href": "data", "roles": ["data"]}},
    }
    attrs = stac.create_convention_attrs(item=item)
    print(f"[create] wrote stac:item data; revision = {stac.detect(attrs)}")
    return attrs


def workflow_create_link() -> dict[str, Any]:
    """2. Point at a canonical STAC object hosted elsewhere (`stac:link`)."""
    attrs = stac.create_convention_attrs(
        link={
            "rel": "self",
            "type": "application/geo+json",
            "href": "https://api.example.com/stac/items/example-item",
        }
    )
    print(f"[create] wrote stac:link data; revision = {stac.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """3. Read stac data, branching on the detected revision."""
    doc = stac.create_convention_attrs(key="stac.json")
    rev = stac.detect(doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = stac.extract(doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = stac.extract(doc)
        stac.validate(dict(data))
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_group_only() -> None:
    """4. stac is group-only: an array document is rejected, a group passes."""
    attrs = stac.create_convention_attrs(key="stac.json")
    group_doc: dict[str, Any] = {
        "zarr_format": 3,
        "node_type": "group",
        "attributes": attrs,
    }
    stac.validate_node_metadata(group_doc)
    print("[group-only] group document validates")

    array_doc: dict[str, Any] = {**group_doc, "node_type": "array"}
    try:
        stac.validate_node_metadata(array_doc)
    except ValueError as exc:
        print(f"[group-only] array document rejected: {exc}")


if __name__ == "__main__":
    workflow_create_item()
    workflow_create_link()
    workflow_read_unknown()
    workflow_group_only()
    print("OK")
