"""Example: the license convention.

Run: ``python examples/license.py``. Demonstrates create / read-unknown /
migrate. License has a single revision today (identity migrate scaffold).
"""

from __future__ import annotations

from typing import Any

from zarr_cm import license as license_


def workflow_create() -> dict[str, Any]:
    """1. Create new license data."""
    attrs = license_.insert({}, license_.create(spdx="MIT"))
    print(f"[create] wrote license data; revision = {license_.detect(attrs)}")
    return attrs


def workflow_read_unknown() -> None:
    """2. Read license data, branching on the detected revision."""
    doc = license_.insert({}, license_.create(spdx="Apache-2.0"))
    rev = license_.detect(doc)
    print(f"[read] detected revision {rev!r}")
    if rev is None:
        _, data = license_.extract(doc)
        print(f"[read] unknown revision; raw fields: {dict(data)}")
    else:
        _, data = license_.extract(doc)
        license_.validate(dict(data))
        print(f"[read] validated under {rev!r}: {dict(data)}")


def workflow_migrate() -> None:
    """3. Identity migration scaffold (one revision today)."""
    doc = license_.insert({}, license_.create(spdx="MIT"))
    rev = license_.detect(doc)
    _, old = license_.extract(doc)
    migrated = license_.insert({}, license_.create(spdx=old["spdx"]))
    print(f"[migrate] {rev} -> {license_.detect(migrated)} (identity; single revision)")


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
