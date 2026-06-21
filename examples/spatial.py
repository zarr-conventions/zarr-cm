"""Example: the spatial convention across revisions.

Run: ``python examples/spatial.py``. Demonstrates three workflows:
1. create new data at the latest revision,
2. read data written under an unknown/older revision,
3. migrate data from an old revision to a new one (hand-written).
"""

from __future__ import annotations

from typing import Any

from zarr_cm import spatial


def workflow_create() -> dict[str, Any]:
    """1. Create new data complying with the latest spatial revision (r3, 2D)."""
    data = spatial.create(dimensions=["y", "x"], bbox=[0.0, 0.0, 1.0, 1.0])
    attrs = spatial.insert({}, data)
    print("[create] wrote latest-revision spatial data:")
    print(f"    dimensions = {attrs['spatial:dimensions']}")
    print(f"    revision   = {spatial.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """2. Read data written under an older or unrecognized revision."""
    old_doc = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r2"), revision="r2"
    )
    rev = spatial.detect(old_doc)
    print(f"[read] detected revision {rev!r} for the stored document")
    if rev is None:
        # Unknown revision: extract with no revision (best-effort raw fields).
        # Do NOT assume the latest revision validates this data.
        _, data = spatial.extract(old_doc)
        print(f"[read] unknown revision; extracted raw fields only: {dict(data)}")
    else:
        _, data = spatial.extract(old_doc, revision=rev)
        spatial.validate(dict(data), revision=rev)
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_migrate() -> None:
    """Migrate spatial data from r2 to the latest revision (r3).

    r2 and r3 share the same strict-2D data shape; the migration re-stamps the
    document with the latest revision's identity (its commit-pinned schema_url).
    """
    doc = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r2"), revision="r2"
    )
    src_rev = spatial.detect(doc)
    _, old = spatial.extract(doc, revision=src_rev)
    migrated = spatial.insert({}, spatial.create(dimensions=old["spatial:dimensions"]))
    print(f"[migrate] {src_rev} -> {spatial.detect(migrated)} OK")


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
