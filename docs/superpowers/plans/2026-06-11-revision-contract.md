# Convention Module Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a statically-enforced structural `Protocol` (`ConventionModule`)
that every convention module the registry dispatches to must satisfy, so an
incompatible API change in any module/revision fails `mypy` (and a registration
gap fails pytest).

**Architecture:** A new `src/zarr_cm/_contract.py` defines the
`ConventionModule` protocol (constants + the four operations' call shapes,
return types widened to `Mapping[str, Any]`). Per-target
`_check_*: ConventionModule = <module>` assignments under `TYPE_CHECKING` make
`mypy src/` fail on signature/constant drift. A runtime pytest enumerates the
live dispatch set (`_REGISTRY` + each facade's `_REVISIONS`) and
`isinstance`-checks them against the `@runtime_checkable` protocol, catching a
newly-registered target nobody pinned.

**Tech Stack:** Python 3.11+, `typing.Protocol` / `@runtime_checkable`, mypy
(strict), pytest, ruff. Tests in `tests/` are NOT a package
(`from conftest import ...`, absolute imports). The mypy pre-commit hook is
scoped to `src` only — so the static checks MUST live in `src/`. Run mypy via
`uv run pre-commit run mypy --files <paths>`. DO NOT use
`git commit --no-verify`.

**Reference spec:**
`docs/superpowers/specs/2026-06-11-revision-contract-design.md`

**Verified facts (use verbatim):**

- `ConventionMetadataObject` is a TypedDict in `src/zarr_cm/_core.py`.
- Every dispatch target already declares: `UUID: Final = "..."` (infers `str`),
  `SCHEMA_URL`/`SPEC_URL: Final = "..."` (`str`),
  `CMO: Final[ConventionMetadataObject]`, `CONVENTION_KEYS: Final = {...}`
  (infers `set[str]`).
- The seven dispatch targets: `zarr_cm.spatial._r1`, `zarr_cm.spatial._r2`,
  `zarr_cm.proj._r1`, `zarr_cm.proj._r2`, `zarr_cm.multiscales`,
  `zarr_cm.license`, `zarr_cm.uom`.
- `zarr_cm._REGISTRY` maps `ConventionName -> module`; revisioned facades expose
  `_REVISIONS: dict[str, ModuleType]`.

---

## File Structure

- `src/zarr_cm/_contract.py` — NEW. The `ConventionModule` protocol + the
  `TYPE_CHECKING` static `_check_*` assignments. One clear responsibility:
  define and statically verify the dispatch contract.
- `tests/test_contract.py` — NEW. Runtime layer: imports `_contract`, enumerates
  the live dispatch set, isinstance-checks each against the protocol.

No other files change (the flat modules already conform; the spec forbids
retrofitting the registry types).

---

## Task 1: Spike — verify module-as-protocol works in mypy

**Goal:** De-risk the core assumption before building the real thing: does mypy
accept a _module_ as satisfying a `Protocol` whose members include attributes
(`UUID: str`, `CONVENTION_KEYS: set[str]`) declared on the module via `Final`
inference? And does a deliberately-broken module fail? This task ends with a
WORKING minimal `_contract.py` checking ONE module; Task 2 expands it.

**Files:**

- Create: `src/zarr_cm/_contract.py` (minimal, one check)

- [ ] **Step 1: Write the minimal protocol + one static check**

Create `src/zarr_cm/_contract.py`:

```python
"""Structural contract for convention modules dispatched by the registry.

Defines :class:`ConventionModule` and statically asserts that every convention
module (and revision submodule) satisfies it. A signature or constant drift in
any dispatch target fails ``mypy src/`` at the corresponding ``_check_*`` line.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ._core import ConventionMetadataObject


@runtime_checkable
class ConventionModule(Protocol):
    """Structural contract every convention module (and revision submodule) satisfies."""

    UUID: str
    SCHEMA_URL: str
    SPEC_URL: str
    CMO: ConventionMetadataObject
    CONVENTION_KEYS: set[str]

    def create(self, **kwargs: Any) -> Mapping[str, Any]: ...
    def insert(
        self, attrs: dict[str, Any], data: Any, *, overwrite: bool = ...
    ) -> dict[str, Any]: ...
    def extract(
        self, attrs: dict[str, Any]
    ) -> tuple[dict[str, Any], Mapping[str, Any]]: ...
    def validate(self, data: dict[str, Any]) -> Mapping[str, Any]: ...


if TYPE_CHECKING:
    from .spatial import _r2 as _spatial_r2

    _check_spatial_r2: ConventionModule = _spatial_r2
```

- [ ] **Step 2: Run mypy — does the happy path pass?**

Run: `uv run pre-commit run mypy --files src/zarr_cm/_contract.py` Expected:
**Passed**.

**If it FAILS**, read the error. The most likely culprit is an attribute member
being too strict against the module's `Final`-inferred type (e.g.
`CONVENTION_KEYS: set[str]` vs the module's inferred `set[str]` under
invariance, or `CMO` invariance). Apply the documented fallback and re-run:

- Widen `CONVENTION_KEYS: set[str]` →
  `CONVENTION_KEYS: frozenset[str] | set[str]` is NOT the fix; instead try
  `CONVENTION_KEYS: Collection[str]` (import
  `from collections.abc import Collection`). A `Collection[str]` protocol member
  accepts a `set[str]` attribute and still catches "renamed/removed/wrong-type".
- If `CMO: ConventionMetadataObject` errors on invariance, widen to
  `CMO: Mapping[str, Any]`.
- If a `str` constant errors (unlikely), widen to `object` only as a last resort
  and note it. Record in the commit message which (if any) members had to be
  widened and why.

- [ ] **Step 3: Prove the check has teeth (negative test)**

Temporarily break `spatial._r2`: rename its `CONVENTION_KEYS` to
`CONVENTION_KEYZ` in `src/zarr_cm/spatial/_r2.py`.

Run:
`uv run pre-commit run mypy --files src/zarr_cm/_contract.py src/zarr_cm/spatial/_r2.py`
Expected: **Failed**, with an error attributing the mismatch to
`_check_spatial_r2` (e.g. "Incompatible types in assignment" / missing attribute
`CONVENTION_KEYS`).

If mypy does NOT fail, the contract is toothless — STOP and report (the protocol
member for the broken attribute is too loose; tighten it).

Then REVERT the rename: Run: `git checkout src/zarr_cm/spatial/_r2.py` Confirm
`git diff src/zarr_cm/spatial/_r2.py` is empty.

- [ ] **Step 4: Re-run mypy to confirm green after revert**

Run:
`uv run pre-commit run mypy --files src/zarr_cm/_contract.py src/zarr_cm/spatial/_r2.py`
Expected: **Passed**.

- [ ] **Step 5: ruff**

Run: `uv run ruff check src/zarr_cm/_contract.py` Expected: All checks passed.
(If F401 fires on the `TYPE_CHECKING` import or the `_check_*` name being
"unused", note that the assignment USES the import; an unused-variable complaint
on `_check_spatial_r2` should not occur for a module-level annotated assignment,
but if ruff flags it, the established project fix is a leading underscore —
already present — or add it to the protocol module's intent; do not silence with
noqa unless necessary.)

- [ ] **Step 6: Commit**

```bash
git add src/zarr_cm/_contract.py
git commit -m "feat: ConventionModule protocol + spike checking spatial r2"
```

Include in the commit body: whether any protocol member had to be widened from
the spec's form (and why), and confirmation the negative test failed as expected
then reverted clean.

---

## Task 2: Expand static checks to all seven dispatch targets

**Files:**

- Modify: `src/zarr_cm/_contract.py`

- [ ] **Step 1: Add the remaining six static checks**

In `src/zarr_cm/_contract.py`, replace the `if TYPE_CHECKING:` block with the
full set:

```python
if TYPE_CHECKING:
    from . import license as _license
    from . import multiscales as _multiscales
    from . import uom as _uom
    from .proj import _r1 as _proj_r1
    from .proj import _r2 as _proj_r2
    from .spatial import _r1 as _spatial_r1
    from .spatial import _r2 as _spatial_r2

    # Each dispatch target must satisfy ConventionModule. A signature/constant
    # drift in any of these fails `mypy src/` at the corresponding line.
    # Adding a convention or revision means adding one line here.
    _check_spatial_r1: ConventionModule = _spatial_r1
    _check_spatial_r2: ConventionModule = _spatial_r2
    _check_proj_r1: ConventionModule = _proj_r1
    _check_proj_r2: ConventionModule = _proj_r2
    _check_multiscales: ConventionModule = _multiscales
    _check_license: ConventionModule = _license
    _check_uom: ConventionModule = _uom
```

- [ ] **Step 2: Run mypy on the contract + all targets**

Run:
`uv run pre-commit run mypy --files src/zarr_cm/_contract.py src/zarr_cm/spatial/_r1.py src/zarr_cm/spatial/_r2.py src/zarr_cm/proj/_r1.py src/zarr_cm/proj/_r2.py src/zarr_cm/multiscales.py src/zarr_cm/license.py src/zarr_cm/uom.py`
Expected: **Passed** (all seven modules satisfy the contract).

**If a flat module fails** (e.g. `multiscales`/`license`/`uom` has a subtly
different `insert`/`extract`/`validate` shape than the protocol), do NOT change
the flat module — instead determine whether the protocol member is wrong (too
strict) and widen it minimally, OR report if the module genuinely diverges from
the contract (that would be a real finding worth surfacing, not silently
papering over). Record the resolution.

- [ ] **Step 3: Full mypy over src (nothing else regressed)**

Run: `uv run pre-commit run mypy --all-files` Expected: **Passed**.

- [ ] **Step 4: ruff**

Run: `uv run ruff check src/zarr_cm/_contract.py` Expected: All checks passed.

- [ ] **Step 5: Commit**

```bash
git add src/zarr_cm/_contract.py
git commit -m "feat: statically check all seven dispatch targets against ConventionModule"
```

---

## Task 3: Runtime registration guard

**Goal:** Catch the one thing mypy can't — a convention/revision added to the
live dispatch set (`_REGISTRY` / a facade's `_REVISIONS`) that nobody pinned
with a `_check_*` line. Enumerate the live set and isinstance-check each against
the runtime-checkable protocol.

**Files:**

- Create: `tests/test_contract.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_contract.py`:

```python
from __future__ import annotations

import zarr_cm
from zarr_cm._contract import ConventionModule


def _dispatch_targets() -> list[tuple[str, object]]:
    """Every module the package actually dispatches to: each registry module,
    plus every revision submodule of a revisioned convention."""
    targets: list[tuple[str, object]] = []
    for name, mod in zarr_cm._REGISTRY.items():
        revisions = getattr(mod, "_REVISIONS", None)
        if revisions is None:
            targets.append((name, mod))
        else:
            for label, rev_mod in revisions.items():
                targets.append((f"{name}:{label}", rev_mod))
    return targets


def test_contract_module_imports() -> None:
    # The TYPE_CHECKING static-check block is invisible at runtime; this proves
    # the module itself imports cleanly.
    import zarr_cm._contract  # noqa: F401


def test_all_dispatch_targets_satisfy_contract() -> None:
    targets = _dispatch_targets()
    # Sanity: we actually found the known set (7 today: spatial r1/r2,
    # proj r1/r2, multiscales, license, uom).
    assert len(targets) >= 7
    for name, mod in targets:
        assert isinstance(
            mod, ConventionModule
        ), f"dispatch target {name!r} does not satisfy ConventionModule"
```

- [ ] **Step 2: Run — verify it passes (the targets already conform)**

Run: `uv run pytest tests/test_contract.py -v` Expected: **PASS** (both tests).
The runtime `isinstance` against a `@runtime_checkable` protocol checks
attribute/method PRESENCE; all seven targets have all members.

If `test_all_dispatch_targets_satisfy_contract` FAILS, a target is missing a
required attribute/method — that is a real conformance gap; report it (do not
weaken the test).

- [ ] **Step 3: Prove the guard has teeth (manual negative check)**

Temporarily comment out `validate` in `src/zarr_cm/uom.py` (or rename it). Run:
`uv run pytest tests/test_contract.py::test_all_dispatch_targets_satisfy_contract -q`
Expected: **FAIL** naming `'uom'` (runtime_checkable isinstance returns False
when a member is absent). Then REVERT: `git checkout src/zarr_cm/uom.py`;
confirm `git diff src/zarr_cm/uom.py` empty, and re-run the test to confirm
PASS.

- [ ] **Step 4: ruff + full test suite**

Run: `uv run ruff check tests/test_contract.py` Expected: All checks passed.
(`import zarr_cm._contract` inside the test needs the `# noqa: F401`;
`zarr_cm._REGISTRY` access is a private-member access in a test, which ruff's
default config allows — if a private-access lint fires, it is acceptable in
tests per the project's `tests/**` ruff exemptions.)

Run: `uv run pytest -q` Expected: all PASS (prior count + 2).

- [ ] **Step 5: Commit**

```bash
git add tests/test_contract.py
git commit -m "test: runtime guard that every dispatch target satisfies ConventionModule"
```

---

## Task 4: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Full nox gate**

Run: `uvx nox` Expected: `lint`, `pylint`, `tests` sessions all pass. (pylint
must stay 10.00/10 — if the new `_contract.py` triggers a pylint message,
address it: e.g. `missing-class-docstring` is disabled already; an
`unused-import` in the `TYPE_CHECKING` block should not fire since the imports
are used by the `_check_*` assignments. If pylint flags the `_check_*`
assignments as unused, that is the same class as a deliberate type-check
artifact — add a targeted `# pylint: disable=unused-variable` on the block with
a comment, mirroring how the protected-access disable was handled in
src/zarr_cm/**init**.py.)

- [ ] **Step 2: Confirm the static guard is actually wired into the commit
      gate**

Run: `uv run pre-commit run mypy --all-files` Expected: **Passed**, and the run
includes `src/zarr_cm/_contract.py` (it is under `src/`, which the hook's
`files: src|noxfile.py` matches).

- [ ] **Step 3: End-to-end teeth check across both layers (then revert)**

Break a constant on a revision module: in `src/zarr_cm/proj/_r2.py`, rename
`SCHEMA_URL` to `SCHEMA_URI` (this breaks both the static `_check_proj_r2` AND,
because `_resolve_read_revision`/`_SCHEMA_URL_BY_REVISION` reads
`mod.SCHEMA_URL`, the runtime presence check). Run:
`uv run pre-commit run mypy --all-files` → Expected: **Failed** (static layer
catches it). Run: `uv run pytest tests/test_contract.py -q` → Expected: **FAIL**
(runtime layer catches the missing `SCHEMA_URL`). REVERT:
`git checkout src/zarr_cm/proj/_r2.py`; confirm `git diff` clean; re-run both →
both pass.

- [ ] **Step 4: Final commit if any verification fixups were needed**

```bash
git add -A
git commit -m "chore: verification fixups for convention module contract"
```

(If no fixups were needed, skip — there is nothing to commit.)

---

## Notes for the implementer

- The static checks MUST stay in `src/` — the mypy pre-commit hook is scoped to
  `src|noxfile.py`. A check placed in `tests/` would never run in the gate.
- Do NOT retype `_REGISTRY` / `_REVISIONS` values as `ConventionModule` (spec
  §4): the facades access non-protocol module attributes and it would force the
  protocol to grow or require casts.
- Do NOT change the flat modules (`multiscales`/`license`/`uom`) to fit the
  protocol — they already conform; if mypy disagrees, the protocol member is too
  strict and should be widened (Task 2 Step 2).
- Revisions/conventions are added in two places that must stay in sync: the
  `_check_*` block in `_contract.py` (static) and the live
  `_REGISTRY`/`_REVISIONS` (which the runtime test enumerates). The runtime test
  is precisely what catches forgetting the static line.
- The `overwrite: bool = ...` ellipsis is a real protocol default-marker, not a
  placeholder.
