# Convention Examples + `detect` API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a public `detect()` revision-detection helper to every convention
(plus an aggregate `detect_revisions`), then ship one runnable example script
per convention demonstrating create / read-unknown-revision / migrate, with a
test that runs the examples.

**Architecture:** A thin `_core.resolve_revision_label` wrapper distinguishes
"convention absent" (raise) from "present but unknown revision" (None) and
otherwise returns the claimed revision label. Each convention surface
(revisioned facades `spatial`/`proj`; flat modules
`multiscales`/`license`/`uom`) exposes `detect(attrs) -> str | None` built on
it. The top-level package adds
`detect_revisions(attrs) -> dict[ConventionName, str | None]`. Examples live in
a new top-level `examples/` dir; a subprocess-based test runs each.

**Tech Stack:** Python 3.11+, mypy strict (pre-commit hook scoped to `src` only
— run via `uv run pre-commit run mypy --files <paths>`), pytest, ruff, pylint
(must stay 10.00/10 via `uvx nox -s pylint`). Tests in `tests/` are NOT a
package (absolute imports, `from conftest import ...`). DO NOT use
`git commit --no-verify`. If a commit aborts because a hook reformatted a file,
`git add` again and re-commit.

**Reference spec:**
`docs/superpowers/specs/2026-06-16-examples-and-detect-design.md`

**Verified facts (use verbatim):**

- `_core.detect_revision(attrs, uuid, schema_url_by_revision) -> str | None`
  already exists (returns label, or None if UUID present but schema_url
  unrecognized).
- Revisioned facades (`spatial`/`proj`) already have module-level `UUID`,
  `LATEST`, `_REVISIONS`, and `_SCHEMA_URL_BY_REVISION: Final[dict[str, str]]`,
  and import `from zarr_cm._core import detect_revision`. They have `__all__`
  (must add `"detect"`).
- Flat modules (`multiscales`/`license`/`uom`) have `UUID`, `SCHEMA_URL` (a
  `refs/tags/v1` URL), no `_REVISIONS`, no `__all__`.
- `create` signatures: spatial/proj `(*args, revision="r2", **kwargs)`;
  `multiscales(*, layout, resampling_method=None)`;
  `license(*, spdx=None, url=None, text=None, file=None, path=None)`;
  `uom(*, ucum, description=None)`.
- Flat `validate(data)` / `extract(attrs)` take NO `revision=` kwarg;
  spatial/proj `validate`/`extract` take `*, revision: str | None = None`.
- `zarr_cm._detect_conventions(attrs) -> frozenset[ConventionName]` matches
  present conventions by UUID.
  `ConventionName = Literal["geo-proj","spatial","multiscales","license","uom"]`.
  `_REGISTRY` maps name -> module (geo-proj -> proj package).
- CI runs `uv run pytest`; `nox -s tests` runs all of `tests/`. No new CI/nox
  job needed for the examples test.

---

## File Structure

- `src/zarr_cm/_core.py` — add `resolve_revision_label` (Task 1).
- `src/zarr_cm/spatial/__init__.py`, `src/zarr_cm/proj/__init__.py` — add
  `detect`, export it (Task 2).
- `src/zarr_cm/__init__.py` — add `detect_revisions` aggregate, export it (Task
  2).
- `src/zarr_cm/multiscales.py`, `src/zarr_cm/license.py`, `src/zarr_cm/uom.py` —
  add `detect` + `_SCHEMA_URL_BY_REVISION` (Task 3).
- `examples/spatial.py` (Task 4); `examples/proj.py`, `examples/multiscales.py`,
  `examples/license.py`, `examples/uom.py` (Task 5).
- `tests/test_examples.py` (Task 6).
- `tests/test_detect.py` — unit tests for `detect`/`detect_revisions` (Tasks 2 &
  3).

---

## Task 1: `_core.resolve_revision_label`

**Files:**

- Modify: `src/zarr_cm/_core.py`
- Test: `tests/test_core_detect.py` (new)

- [ ] **Step 1: Write the failing test** `tests/test_core_detect.py`:

```python
from __future__ import annotations

import pytest

from zarr_cm._core import resolve_revision_label

UUID = "test-uuid-1234"
URLS = {"r1": "https://example/r1.json", "r2": "https://example/r2.json"}


def _attrs(schema_url: str | None) -> dict[str, object]:
    cmo: dict[str, object] = {"uuid": UUID}
    if schema_url is not None:
        cmo["schema_url"] = schema_url
    return {"zarr_conventions": [cmo]}


def test_returns_label_for_known_url() -> None:
    assert resolve_revision_label(_attrs(URLS["r1"]), UUID, URLS, "demo") == "r1"
    assert resolve_revision_label(_attrs(URLS["r2"]), UUID, URLS, "demo") == "r2"


def test_returns_none_for_present_but_unknown_url() -> None:
    got = resolve_revision_label(
        _attrs("https://example/UNKNOWN.json"), UUID, URLS, "demo"
    )
    assert got is None


def test_raises_when_convention_absent() -> None:
    with pytest.raises(ValueError, match="demo"):
        resolve_revision_label({"zarr_conventions": []}, UUID, URLS, "demo")
    with pytest.raises(ValueError, match="demo"):
        resolve_revision_label({}, UUID, URLS, "demo")
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_core_detect.py -q` Expected: FAIL —
`ImportError: cannot import name 'resolve_revision_label'`.

- [ ] **Step 3: Implement in `src/zarr_cm/_core.py`** (append after
      `detect_revision`):

```python
def resolve_revision_label(
    attrs: dict[str, Any],
    uuid: str,
    schema_url_by_revision: dict[str, str],
    convention_name: str,
) -> str | None:
    """Return the revision label a document claims for a convention.

    Returns the label whose ``schema_url`` matches the convention's CMO, or
    ``None`` if the convention's ``uuid`` is present but its ``schema_url`` is
    unrecognized (an older/newer/foreign revision). Raises ``ValueError`` if the
    convention is absent (no CMO with *uuid*) -- asking which revision is present
    for a convention that is not there is a caller error.
    """
    present = any(cmo.get("uuid") == uuid for cmo in attrs.get("zarr_conventions", []))
    if not present:
        msg = f"convention {convention_name!r} is not present in attrs"
        raise ValueError(msg)
    return detect_revision(attrs, uuid, schema_url_by_revision)
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_core_detect.py -q` Expected: PASS (3 tests).

- [ ] **Step 5: mypy + ruff**

Run: `uv run pre-commit run mypy --files src/zarr_cm/_core.py` Expected: Passed.
Run: `uv run ruff check src/zarr_cm/_core.py tests/test_core_detect.py`
Expected: All checks passed.

- [ ] **Step 6: Commit**

```bash
git add src/zarr_cm/_core.py tests/test_core_detect.py
git commit -m "feat: add _core.resolve_revision_label (label / None / raise-if-absent)"
```

---

## Task 2: `detect` on revisioned facades + aggregate `detect_revisions`

**Files:**

- Modify: `src/zarr_cm/spatial/__init__.py`, `src/zarr_cm/proj/__init__.py`,
  `src/zarr_cm/__init__.py`
- Test: `tests/test_detect.py` (new)

- [ ] **Step 1: Write the failing test** `tests/test_detect.py`:

```python
from __future__ import annotations

import pytest

import zarr_cm
from zarr_cm import proj, spatial


def test_spatial_detect_known_revisions() -> None:
    r1 = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    r2 = spatial.insert({}, spatial.create(dimensions=["y", "x"]))  # latest = r2
    assert spatial.detect(r1) == "r1"
    assert spatial.detect(r2) == "r2"


def test_spatial_detect_unknown_revision_returns_none() -> None:
    doc = {
        "spatial:dimensions": ["y", "x"],
        "zarr_conventions": [
            {
                "uuid": spatial.UUID,
                "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/0000000000000000000000000000000000000000/schema.json",
            }
        ],
    }
    assert spatial.detect(doc) is None


def test_spatial_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="spatial"):
        spatial.detect({"foo": "bar"})


def test_proj_detect_known_revisions() -> None:
    r1 = proj.insert({}, proj.create(code="EPSG:4326", revision="r1"), revision="r1")
    r2 = proj.insert({}, proj.create(code="EPSG:4326"))
    assert proj.detect(r1) == "r1"
    assert proj.detect(r2) == "r2"


def test_detect_revisions_aggregate() -> None:
    attrs = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    attrs = proj.insert(attrs, proj.create(code="EPSG:4326"))  # r2
    result = zarr_cm.detect_revisions(attrs)
    assert result == {"spatial": "r1", "geo-proj": "r2"}


def test_detect_revisions_empty() -> None:
    assert zarr_cm.detect_revisions({"foo": "bar"}) == {}
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_detect.py -q` Expected: FAIL —
`AttributeError: module 'zarr_cm.spatial' has no attribute 'detect'` (and
`zarr_cm.detect_revisions` missing).

- [ ] **Step 3: Add `detect` to `src/zarr_cm/spatial/__init__.py`.**

Change the import line `from zarr_cm._core import detect_revision` to also
import the new helper:

```python
from zarr_cm._core import detect_revision, resolve_revision_label
```

Add this function (place it next to `_resolve_read_revision`):

```python
def detect(attrs: dict[str, Any]) -> str | None:
    """Return the revision label this document claims for the spatial convention.

    Returns the label (e.g. ``"r1"``/``"r2"``), or ``None`` if the convention is
    present but at an unrecognized revision. Raises ``ValueError`` if the spatial
    convention is absent from *attrs*.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "spatial")
```

Add `"detect"` to the `__all__` list (keep it sorted).

- [ ] **Step 4: Add `detect` to `src/zarr_cm/proj/__init__.py`** — identical,
      but the convention name string is `"geo-proj"` (the registry/display name)
      and the docstring says "proj":

```python
from zarr_cm._core import detect_revision, resolve_revision_label
```

```python
def detect(attrs: dict[str, Any]) -> str | None:
    """Return the revision label this document claims for the proj convention.

    Returns the label (e.g. ``"r1"``/``"r2"``), or ``None`` if the convention is
    present but at an unrecognized revision. Raises ``ValueError`` if the proj
    convention is absent from *attrs*.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "geo-proj")
```

Add `"detect"` to proj's `__all__`.

- [ ] **Step 5: Add `detect_revisions` to `src/zarr_cm/__init__.py`.**

After `extract_all` (near the other aggregate functions), add:

```python
def detect_revisions(
    attrs: dict[str, Any],
) -> dict[ConventionName, str | None]:
    """Map each present convention to the revision label it claims.

    Detects which conventions are present (by UUID) and returns a mapping from
    each present convention's display name to its claimed revision label, or
    ``None`` if present at an unrecognized revision. Absent conventions are not
    included.
    """
    result: dict[ConventionName, str | None] = {}
    for name in _detect_conventions(attrs):
        result[name] = _get_module(name).detect(attrs)
    return result
```

Add `"detect_revisions"` to the top-level `__all__` (keep sorted).

> Note: `_get_module(name).detect(attrs)` works because the registry maps to the
> package/module exposing `detect`. For `"geo-proj"` the registry points at the
> `proj` package (which has `detect`). The flat modules get `detect` in Task 3 —
> but `detect_revisions` only calls `.detect` on conventions detected as
> PRESENT, and Task 3 runs before the full suite is green; if running this
> task's tests before Task 3, `test_detect_revisions_aggregate` only touches
> spatial+proj, so it passes. (The empty-case test touches nothing.)

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_detect.py -q` Expected: PASS (6 tests).

- [ ] **Step 7: mypy + ruff + pylint**

Run:
`uv run pre-commit run mypy --files src/zarr_cm/spatial/__init__.py src/zarr_cm/proj/__init__.py src/zarr_cm/__init__.py`
Expected: Passed. Run: `uv run ruff check src/zarr_cm tests/test_detect.py`
Expected: All checks passed. Run: `uvx nox -s pylint` Expected: 10.00/10,
success. (If pylint flags `detect_revisions` calling `.detect` on a `ModuleType`
— W0212 or no-member — note that `_get_module` returns `types.ModuleType` and
`.detect` is dynamic; the existing `_rev_kwargs`/`_read_rev_kwargs` already do
`hasattr(mod, "_REVISIONS")` / `mod._resolve_read_revision`, so dynamic module
attribute access is an established pattern here. If pylint complains, mirror the
existing handling.)

- [ ] **Step 8: Commit**

```bash
git add src/zarr_cm/spatial/__init__.py src/zarr_cm/proj/__init__.py src/zarr_cm/__init__.py tests/test_detect.py
git commit -m "feat: public detect() on spatial/proj + aggregate detect_revisions"
```

---

## Task 3: `detect` on flat modules

**Files:**

- Modify: `src/zarr_cm/multiscales.py`, `src/zarr_cm/license.py`,
  `src/zarr_cm/uom.py`
- Test: `tests/test_detect.py` (extend)

- [ ] **Step 1: Add failing tests** — append to `tests/test_detect.py`:

```python
from zarr_cm import license as license_
from zarr_cm import multiscales, uom


def test_flat_detect_present_returns_v1() -> None:
    ms = multiscales.insert({}, multiscales.create(layout=[{"asset": "0"}]))
    assert multiscales.detect(ms) == "v1"
    li = license_.insert({}, license_.create(spdx="MIT"))
    assert license_.detect(li) == "v1"
    um = uom.insert({}, uom.create(ucum={"unit": "m"}))
    assert uom.detect(um) == "v1"


def test_flat_detect_unknown_url_returns_none() -> None:
    doc = {
        "multiscales": {"layout": [{"asset": "0"}]},
        "zarr_conventions": [
            {"uuid": multiscales.UUID, "schema_url": "https://example/other.json"}
        ],
    }
    assert multiscales.detect(doc) is None


def test_flat_detect_absent_raises() -> None:
    with pytest.raises(ValueError, match="multiscales"):
        multiscales.detect({"foo": "bar"})
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_detect.py -k flat -q` Expected: FAIL —
`module 'zarr_cm.multiscales' has no attribute 'detect'`.

- [ ] **Step 3: Add `detect` to each flat module.** For
      `src/zarr_cm/multiscales.py`, add the import (extend the existing
      `from zarr_cm._core import (...)` block) and, after the `CONVENTION_KEYS`
      constant, add the single-revision map and `detect`:

```python
from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
    resolve_revision_label,
)
```

```python
_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {"v1": SCHEMA_URL}


def detect(attrs: dict[str, Any]) -> str | None:
    """Return the revision label this document claims for the multiscales convention.

    Multiscales has a single revision (``"v1"``); returns it when present with the
    known schema_url, ``None`` if present with an unrecognized schema_url, and
    raises ``ValueError`` if the convention is absent.
    """
    return resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, "multiscales")
```

Do the identical change in `src/zarr_cm/license.py` (convention name
`"license"`, docstring "license") and `src/zarr_cm/uom.py` (convention name
`"uom"`, docstring "uom"). Each already imports from `zarr_cm._core` — extend
that import to include `resolve_revision_label`. Place
`_SCHEMA_URL_BY_REVISION` + `detect` after that module's `CONVENTION_KEYS`.

> The flat modules have no `__all__`, so a module-level `def detect` is public
> automatically — no export edit needed.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_detect.py -q` Expected: PASS (all, incl. the 3
flat tests).

- [ ] **Step 5: mypy + ruff + pylint**

Run:
`uv run pre-commit run mypy --files src/zarr_cm/multiscales.py src/zarr_cm/license.py src/zarr_cm/uom.py`
Expected: Passed. Run: `uv run ruff check src/zarr_cm` Expected: All checks
passed. Run: `uvx nox -s pylint` Expected: 10.00/10.

- [ ] **Step 6: Commit**

```bash
git add src/zarr_cm/multiscales.py src/zarr_cm/license.py src/zarr_cm/uom.py tests/test_detect.py
git commit -m "feat: public detect() on multiscales/license/uom flat modules"
```

---

## Task 4: `examples/spatial.py` (establish the pattern; lossy migration)

**Files:**

- Create: `examples/spatial.py`

This is the hardest example (lossy 3D→2D migration) and sets the template for
Task 5.

- [ ] **Step 1: Write `examples/spatial.py`:**

```python
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
    # An older r1 document (3D is allowed under r1):
    old_doc = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    rev = spatial.detect(old_doc)
    print(f"[read] detected revision {rev!r} for the stored document")
    if rev is None:
        # Present but unrecognized: extract best-effort, do NOT assume latest.
        _, data = spatial.extract(old_doc)
        print(f"[read] unknown revision; extracted raw fields only: {dict(data)}")
    else:
        # Known revision: extract and validate under exactly that revision.
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
        # The real choices: drop the non-XY axis to fit r2 ...
        xy = old3["spatial:dimensions"][-2:]
        dropped = spatial.insert({}, spatial.create(dimensions=xy))
        print(
            f"[migrate] ... dropped leading axis -> {dropped['spatial:dimensions']} (r2)"
        )
        # ... or keep the data at r1 (no migration). Both are explicit choices.


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
```

- [ ] **Step 2: Run it as a user would**

Run: `uv run python examples/spatial.py` Expected: prints the
create/read/migrate narration and ends with `OK`, exit 0.

- [ ] **Step 3: ruff (examples should lint too)**

Run: `uv run ruff check examples/spatial.py` Expected: All checks passed.
(`print` is fine — `examples/**` is not under a no-print rule, but if `T20`
fires, add `examples/**` to `[tool.ruff.lint.per-file-ignores]` with `["T20"]`
in `pyproject.toml`, mirroring the existing
`tests/**`/`docs/examples/**`/`.github/scripts/**` entries, and commit that
pyproject change with this task.)

- [ ] **Step 4: Commit**

```bash
git add examples/spatial.py pyproject.toml
git commit -m "docs: add spatial convention example (create/read/migrate)"
```

(Only include `pyproject.toml` if you had to add the `examples/**` T20 ignore.)

---

## Task 5: `examples/` for proj, multiscales, license, uom

**Files:**

- Create: `examples/proj.py`, `examples/multiscales.py`, `examples/license.py`,
  `examples/uom.py`

Follow the same three-workflow structure as `examples/spatial.py`. Each ends
with `print("OK")` and exit 0.

- [ ] **Step 1: Write `examples/proj.py`** (clean same-shape r1 -> r2
      migration):

```python
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
    # r2 keeps the same fields; rebuild from the old data and insert at latest.
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
```

- [ ] **Step 2: Write `examples/multiscales.py`** (single revision; migrate =
      identity scaffold):

```python
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
        # Flat modules take no revision= kwarg (single revision).
        _, data = multiscales.extract(doc)
        multiscales.validate(dict(data))
        print(f"[read] validated under {rev!r}")


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
```

- [ ] **Step 3: Write `examples/license.py`** (single revision):

```python
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
```

- [ ] **Step 4: Write `examples/uom.py`** (single revision):

```python
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
```

- [ ] **Step 5: Run all four**

Run:
`for f in proj multiscales license uom; do echo "=== $f ==="; uv run python examples/$f.py || echo "FAILED $f"; done`
Expected: each prints its narration and `OK`, exit 0. If any workflow needs
private API or contortions to express, STOP and report — that is the API-pain
signal the spec calls out.

- [ ] **Step 6: ruff**

Run: `uv run ruff check examples/` Expected: All checks passed.

- [ ] **Step 7: Commit**

```bash
git add examples/proj.py examples/multiscales.py examples/license.py examples/uom.py
git commit -m "docs: add proj/multiscales/license/uom convention examples"
```

---

## Task 6: Test that runs the examples

**Files:**

- Create: `tests/test_examples.py`

- [ ] **Step 1: Write the test** `tests/test_examples.py`:

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
_SCRIPTS = sorted(_EXAMPLES_DIR.glob("*.py"))


def test_examples_dir_is_populated() -> None:
    assert len(_SCRIPTS) >= 5, f"expected >=5 example scripts, found {_SCRIPTS}"


@pytest.mark.parametrize("script", _SCRIPTS, ids=lambda p: p.stem)
def test_example_runs_clean(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{script.name} exited {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert result.stdout.strip().endswith("OK")
```

- [ ] **Step 2: Run**

Run: `uv run pytest tests/test_examples.py -v` Expected: PASS —
`test_examples_dir_is_populated` plus one parametrized case per script (5+), all
green.

- [ ] **Step 3: ruff**

Run: `uv run ruff check tests/test_examples.py` Expected: All checks passed.

- [ ] **Step 4: Commit**

```bash
git add tests/test_examples.py
git commit -m "test: run convention examples as part of the suite"
```

---

## Task 7: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Full nox gate**

Run: `uvx nox` Expected: `lint`, `pylint` (10.00/10), `tests` all pass. The
`tests` session now includes `test_examples.py` (running all five scripts) and
`test_detect.py`/`test_core_detect.py`.

- [ ] **Step 2: Full pre-commit on all files**

Run: `uv run pre-commit run --all-files` Expected: all hooks pass (mypy on src
incl. the new `detect`/`resolve_revision_label`; ruff; validators).

- [ ] **Step 3: Confirm the public API additions import and behave**

Run:

```bash
uv run python -c "
import zarr_cm
from zarr_cm import spatial, proj, multiscales, license as lic, uom
# detect present on every convention
for m in (spatial, proj, multiscales, lic, uom):
    assert callable(m.detect)
# aggregate
attrs = zarr_cm.create_many({'spatial': {'spatial:dimensions': ['y','x']}, 'license': {'spdx':'MIT'}})
got = zarr_cm.detect_revisions(attrs)
assert got == {'spatial': 'r2', 'license': 'v1'}, got
print('ok', got)
"
```

Expected: prints `ok {'spatial': 'r2', 'license': 'v1'}`.

> Note on `test_package.py::test_version`: if it fails locally with a
> `0.2.1.devN+g...` version mismatch, that is a pre-existing hatch-vcs
> editable-install staleness artifact (metadata lags HEAD), NOT caused by this
> work. Fix locally with `uv pip install -e .`; it passes in nox's fresh venv
> and in CI.

- [ ] **Step 4: Final commit if any verification fixups were needed**

```bash
git add -A
git commit -m "chore: verification fixups for examples + detect"
```

(Skip if nothing needed fixing.)

---

## Notes for the implementer

- The examples are the litmus test for "is the API pain-free?". If a workflow
  can only be written with private API (`_`-prefixed) or awkward contortions,
  STOP and report — do not force it. The `detect` addition is expected to make
  all three workflows clean.
- Flat modules' `validate`/`extract` take NO `revision=` kwarg; only
  spatial/proj do. The flat examples call `validate(data)` / `extract(attrs)`
  plainly.
- `detect` returns: a label (known) / `None` (present-but-unknown) / raises
  `ValueError` (absent). The examples branch on label-vs-None; they never pass
  an absent doc to `detect`.
- Do NOT extend the `ConventionModule` protocol (`src/zarr_cm/_contract.py`) to
  require `detect` — it is a read convenience, intentionally outside that
  contract (spec Part A).
- Keep `__all__` lists sorted where present (spatial/proj facades, top-level).
  Flat modules have no `__all__`; a module-level `def detect` is public
  automatically.
- examples live at top-level `examples/`, not `src/` (not packaged) and not
  `docs/` (so `test_docs.py`'s pytest-examples collection is unaffected).
