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
    """1. Create new data complying with the latest spatial revision (r2, 2D)."""
    data = spatial.create(dimensions=["y", "x"], bbox=[0.0, 0.0, 1.0, 1.0])
    attrs = spatial.insert({}, data)
    print("[create] wrote latest-revision spatial data:")
    print(f"    dimensions = {attrs['spatial:dimensions']}")
    print(f"    revision   = {spatial.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """2. Read data written under an older or unrecognized revision."""
    old_doc = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
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
    """3. Migrate spatial data from r1 to r2 (hand-written; r2 is strict 2D)."""
    # Case A: a 2D r1 document migrates cleanly to r2.
    doc_2d = spatial.insert(
        {}, spatial.create(dimensions=["y", "x"], revision="r1"), revision="r1"
    )
    _, old = spatial.extract(doc_2d, revision=spatial.detect(doc_2d))
    migrated = spatial.insert({}, spatial.create(dimensions=old["spatial:dimensions"]))
    print(f"[migrate] 2D r1 -> r2 OK; new revision = {spatial.detect(migrated)}")

    # Case B: a 3D r1 document CANNOT migrate to r2 unchanged (r2 is 2D-only).
    doc_3d = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    _, old3 = spatial.extract(doc_3d, revision=spatial.detect(doc_3d))
    try:
        spatial.create(dimensions=old3["spatial:dimensions"])  # r2, rejects 3D
    except ValueError as exc:
        print(f"[migrate] 3D r1 -> r2 is lossy and was refused: {exc}")
        xy = old3["spatial:dimensions"][-2:]
        dropped = spatial.insert({}, spatial.create(dimensions=xy))
        print(
            f"[migrate] ... dropped leading axis -> {dropped['spatial:dimensions']} (r2)"
        )


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
