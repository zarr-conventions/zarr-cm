"""Example: the multiscales convention across revisions.

Run: ``python examples/multiscales.py``. Demonstrates create / read-unknown /
migrate. Multiscales is a revisioned convention (r1, and r2 at upstream v0.1);
the migrate workflow shows a real r1 -> r2 migration (same data shape, new
schema identity).
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
    """2. Read multiscales data written under an older/unrecognized revision."""
    old_doc = multiscales.insert(
        {}, multiscales.create(layout=[{"asset": "0"}], revision="r1"), revision="r1"
    )
    rev = multiscales.detect(old_doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = multiscales.extract(old_doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = multiscales.extract(old_doc, revision=rev)
        multiscales.validate(dict(data), revision=rev)
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_migrate() -> None:
    """3. Migrate multiscales data from r1 to r2 (same shape; new v0.1 identity)."""
    old_doc = multiscales.insert(
        {}, multiscales.create(layout=[{"asset": "0"}], revision="r1"), revision="r1"
    )
    src = multiscales.detect(old_doc)
    _, old = multiscales.extract(old_doc, revision=src)
    migrated = multiscales.insert({}, multiscales.create(layout=old["layout"]))
    before = [c.get("schema_url") for c in old_doc["zarr_conventions"]]
    after = [c.get("schema_url") for c in migrated["zarr_conventions"]]
    print(f"[migrate] {src} -> {multiscales.detect(migrated)}")
    print(f"    schema_url before: {before}")
    print(f"    schema_url after:  {after}")


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
