"""Example: the multiscales convention.

Run: ``python examples/multiscales.py``. Demonstrates create / read-unknown /
migrate. Multiscales has a single revision today; the migrate workflow shows the
identical detect -> extract -> rebuild -> insert scaffold as an identity step,
ready for a real revision when one lands.
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
    """2. Read multiscales data, branching on the detected revision."""
    doc = multiscales.insert({}, multiscales.create(layout=[{"asset": "0"}]))
    rev = multiscales.detect(doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = multiscales.extract(doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = multiscales.extract(doc)
        multiscales.validate(dict(data))
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_migrate() -> None:
    """3. Identity migration scaffold (one revision today)."""
    doc = multiscales.insert({}, multiscales.create(layout=[{"asset": "0"}]))
    rev = multiscales.detect(doc)
    _, old = multiscales.extract(doc)
    migrated = multiscales.insert({}, multiscales.create(layout=old["layout"]))
    print(
        f"[migrate] {rev} -> {multiscales.detect(migrated)} (identity; single revision)"
    )


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
