"""Example: the uom (units of measurement) convention.

Run: ``python examples/uom.py``. Demonstrates create / read-unknown / migrate.
Uom has a single revision today (identity migrate scaffold).
"""

from __future__ import annotations

from typing import Any

from zarr_cm import uom


def workflow_create() -> dict[str, Any]:
    """1. Create new uom data."""
    attrs = uom.insert({}, uom.create(ucum={"unit": "m"}, description="metres"))
    print(f"[create] wrote uom data; revision = {uom.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """2. Read uom data, branching on the detected revision."""
    doc = uom.insert({}, uom.create(ucum={"unit": "s"}))
    rev = uom.detect(doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = uom.extract(doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = uom.extract(doc)
        uom.validate(dict(data))
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_migrate() -> None:
    """3. Identity migration scaffold (one revision today)."""
    doc = uom.insert({}, uom.create(ucum={"unit": "m"}))
    rev = uom.detect(doc)
    _, old = uom.extract(doc)
    migrated = uom.insert({}, uom.create(ucum=old["ucum"]))
    print(f"[migrate] {rev} -> {uom.detect(migrated)} (identity; single revision)")


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
