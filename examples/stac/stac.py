"""Example: the stac convention.

Run: `python examples/stac/stac.py`. Demonstrates create / defensive read of an
unrecognized `schema_url` / group-only enforcement.
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


def workflow_read_known() -> None:
    """3. Read stac data written at the known, recognized schema_url."""
    doc = stac.create_convention_attrs(key="stac.json")
    rev = stac.detect(doc)
    print(f"[read] detected revision {rev!r}")
    _, data = stac.extract(doc)
    stac.validate(dict(data))
    print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_read_unknown() -> None:
    """4. Read stac data declaring an unrecognized `schema_url` defensively.

    A document may carry a `schema_url` this revision of `zarr-cm` doesn't
    recognize (a future release, or a foreign writer). `detect` reports that
    as `None` rather than guessing, so a defensive reader can still fall back
    to the raw fields instead of failing outright.
    """
    doc: dict[str, Any] = {
        "zarr_conventions": [
            {
                "uuid": stac.UUID,
                "name": "stac:",
                "schema_url": "https://example.com/stac/v9/schema.json",
            }
        ],
        "stac:key": "stac.json",
    }
    rev = stac.detect(doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = stac.extract(doc)
        print(f"[read] unrecognized schema_url; raw fields: {dict(data)}")
    else:
        _, data = stac.extract(doc)
        stac.validate(dict(data))
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_group_only() -> None:
    """5. stac is group-only: an array document is rejected, a group passes."""
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
    workflow_read_known()
    workflow_read_unknown()
    workflow_group_only()
    print("OK")
