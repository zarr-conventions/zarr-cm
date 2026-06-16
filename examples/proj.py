"""Example: the proj convention across revisions.

Run: ``python examples/proj.py``. Demonstrates create / read-unknown / migrate.
"""

from __future__ import annotations

from typing import Any

from zarr_cm import proj


def workflow_create() -> dict[str, Any]:
    """1. Create new data complying with the latest proj revision (r2)."""
    attrs = proj.insert({}, proj.create(code="EPSG:4326"))
    print(f"[create] wrote latest proj data; revision = {proj.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """2. Read data written under an older or unrecognized revision."""
    old_doc = proj.insert(
        {}, proj.create(code="EPSG:4326", revision="r1"), revision="r1"
    )
    rev = proj.detect(old_doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = proj.extract(old_doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = proj.extract(old_doc, revision=rev)
        proj.validate(dict(data), revision=rev)
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_migrate() -> None:
    """3. Migrate proj data r1 -> r2 (same fields; URLs/regex differ)."""
    old_doc = proj.insert(
        {}, proj.create(code="EPSG:4326", revision="r1"), revision="r1"
    )
    src = proj.detect(old_doc)
    _, old = proj.extract(old_doc, revision=src)
    migrated = proj.insert({}, proj.create(code=old["proj:code"]))
    before = [c.get("schema_url") for c in old_doc["zarr_conventions"]]
    after = [c.get("schema_url") for c in migrated["zarr_conventions"]]
    print(f"[migrate] {src} -> {proj.detect(migrated)}")
    print(f"    schema_url before: {before}")
    print(f"    schema_url after:  {after}")
    assert "zarr-conventions/proj" in after[0]


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
