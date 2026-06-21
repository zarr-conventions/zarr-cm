"""Example: the multiscales convention.

Run: ``python examples/multiscales.py``. Demonstrates create / read-unknown /
round-trip. Multiscales currently ships a single revision (r2, at upstream
v0.1), so there is no cross-revision migration to show; the read workflow
illustrates how an unrecognized schema_url is handled defensively.
"""

from __future__ import annotations

from typing import Any

from zarr_cm import multiscales


def workflow_create() -> dict[str, Any]:
    """1. Create new multiscales data."""
    data = multiscales.create(layout=[{"asset": "0"}, {"asset": "1"}])
    attrs = multiscales.insert({}, data)
    print(f"[create] wrote multiscales data; revision = {multiscales.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """2. Read multiscales data carrying an unrecognized schema_url.

    A document whose convention metadata points at a schema_url we do not know
    detects as ``None``; we then extract raw fields only and do NOT assume the
    latest revision validates the data.
    """
    unknown_doc = {
        "multiscales": {"layout": [{"asset": "0"}]},
        "zarr_conventions": [
            {
                "uuid": multiscales.UUID,
                "schema_url": "https://example.invalid/multiscales/unknown.json",
            }
        ],
    }
    rev = multiscales.detect(unknown_doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = multiscales.extract(unknown_doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = multiscales.extract(unknown_doc, revision=rev)
        multiscales.validate(dict(data), revision=rev)
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_roundtrip() -> None:
    """3. Round-trip multiscales data through the latest revision."""
    doc = multiscales.insert({}, multiscales.create(layout=[{"asset": "0"}]))
    rev = multiscales.detect(doc)
    _, data = multiscales.extract(doc, revision=rev)
    urls = [c.get("schema_url") for c in doc["zarr_conventions"]]
    print(f"[roundtrip] revision {rev}; layout = {data['layout']}")
    print(f"    schema_url: {urls}")


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_roundtrip()
    print("OK")
