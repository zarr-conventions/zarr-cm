# Convention Examples + `detect` API — Design

**Date:** 2026-06-16 **Branch:** `bump-proj-and-spatial` **Scope:** A public
revision-detection helper, one runnable example script per convention
demonstrating create / read-unknown-revision / migrate, and a test that runs the
examples.

## Motivation

The package should let a user, for each convention, painlessly: (1) create new
data complying with the convention, (2) read data written under an unknown
revision of a known convention, and (3) migrate data from an old revision to a
new one. Prototyping these against the current API found:

- **Create** is clean.
- **Read unknown revision** works at the `extract` level but there is no public
  way to ask "which revision does this document claim?" — the detection logic
  exists only as private `_core.detect_revision` / facade
  `_resolve_read_revision`. Without it a reader cannot cleanly branch on
  known-vs-unknown-revision.
- **Migrate** has no library affordance, and intentionally will not get a
  generic one: migration needs per-convention, per-revision-pair judgment a
  library cannot generalize (e.g. spatial r1 3D → r2 strict-2D is lossy). The
  goal is to make the _building blocks_ painless so each migration is short and
  explicit, not to ship a `migrate()` routine.

So the only API addition is a public revision-detection helper; migration stays
hand-written per example using the existing `extract(revision=)` /
`insert(revision=)`.

## Part A: Public revision-detection helpers

### Per-convention `detect`

Add `detect(attrs: dict[str, Any]) -> str | None` to every convention surface:
`spatial`, `proj` (revisioned facades) and `multiscales`, `license`, `uom` (flat
modules). Semantics, uniform across all five:

- Returns the **revision label** the document claims (e.g. `"r1"`, `"r2"`) when
  the convention's UUID is present in `attrs["zarr_conventions"]` and the
  matching CMO's `schema_url` maps to a known revision.
- Returns **`None`** when the convention's UUID is present but the `schema_url`
  matches no known revision — "present, but at a revision I don't recognize" (an
  older/newer/foreign snapshot).
- **Raises `ValueError`** when the convention is **absent** (no CMO with the
  convention's UUID). Asking "which revision of spatial is this?" about a
  document that carries no spatial convention is a caller error; the message
  names the convention.

`detect` is the public, non-falling-back sibling of the facades' existing
`_resolve_read_revision` (which returns `LATEST` on unknown — wrong for a reader
that needs to _know_ it's unknown).

### Flat (single-revision) modules

`multiscales`/`license`/`uom` are single modules without `_REVISIONS`. To keep
`detect`'s signature identical across all conventions, they get a uniform notion
of one revision. Implementation: a shared helper in `_core` resolves a label
from `(attrs, uuid, {label: schema_url})`; the flat modules pass a single-entry
map `{<label>: SCHEMA_URL}`. The label for a flat module is its current schema's
tag — use `"v1"` (matches the `refs/tags/v1` the flat-module `SCHEMA_URL`s
already point at). So `multiscales.detect(doc)` returns `"v1"` when present with
the known schema_url, `None` if present with a different schema_url, raises if
absent.

### Aggregate `detect_revisions`

Add top-level
`zarr_cm.detect_revisions(attrs) -> dict[ConventionName, str | None]`: detect
which conventions are present (reusing `_detect_conventions`, which matches by
UUID), and map each present convention's display name to its claimed label or
`None`. Absent conventions are simply not keys. This is the multi-convention
read entry point.

### Shared implementation

Factor the label-resolution out of the facades into `_core`:

```python
# _core.py (already has detect_revision returning label | None)
# detect_revision(attrs, uuid, schema_url_by_revision) -> str | None
#   - returns the label whose schema_url matches the matching CMO's schema_url
#   - returns None if the UUID is present but the schema_url is unrecognized
# Add a thin wrapper that distinguishes ABSENT (raise) from present-but-unknown:


def resolve_revision_label(
    attrs: dict[str, Any],
    uuid: str,
    schema_url_by_revision: dict[str, str],
    convention_name: str,
) -> str | None:
    """Return the claimed revision label, or None if present-but-unrecognized.

    Raises ValueError if no CMO with *uuid* is present (convention absent).
    """
    present = any(cmo.get("uuid") == uuid for cmo in attrs.get("zarr_conventions", []))
    if not present:
        msg = f"convention {convention_name!r} is not present in attrs"
        raise ValueError(msg)
    return detect_revision(attrs, uuid, schema_url_by_revision)
```

- **Revisioned facades** (`spatial`/`proj`): `detect(attrs)` calls
  `resolve_revision_label(attrs, UUID, _SCHEMA_URL_BY_REVISION, <name>)`.
- **Flat modules**: define a module-level
  `_SCHEMA_URL_BY_REVISION = {"v1": SCHEMA_URL}` and `detect(attrs)` calls the
  same wrapper. (Or inline the single-entry map.)

`detect` is added to each facade/module's `__all__` (public). The runtime
contract test (`ConventionModule`) is NOT extended to require `detect` — the
protocol pins the dispatch surface the registry/aggregate layer relies on;
`detect` is a read convenience, out of that contract's scope. (Documented so a
future maintainer does not "fix" the protocol to include it.)

## Part B: Example scripts

New top-level `examples/` directory (not under `src/` or `docs/` — shipped-
adjacent reference code, not packaged). One script per convention:
`examples/spatial.py`, `examples/proj.py`, `examples/multiscales.py`,
`examples/license.py`, `examples/uom.py`.

Each script is self-contained, uses only the public API + stdlib, prints
narration, and is structured as three labelled workflow functions plus a
`__main__` guard:

```text
"""Example: working with the <convention> convention across revisions."""
from __future__ import annotations
from zarr_cm import <convention>


def workflow_create() -> dict:
    """1. Create new data complying with the latest revision."""
    # <convention>.create(...) -> insert({}, data); print; return attrs


def workflow_read_unknown() -> None:
    """2. Read data written under an unknown/older revision."""
    # build/obtain a doc; rev = <convention>.detect(doc)
    #   rev is a known label -> extract(revision=rev) + validate(revision=rev)
    #   rev is None          -> present-but-unknown: extract best-effort, warn,
    #                           do NOT assume the latest revision validates it


def workflow_migrate() -> None:
    """3. Migrate data from an old revision to a new one (hand-written)."""
    # write an old-revision doc; detect() it; extract(revision=<old>);
    # build the target revision's data dict; insert(revision=<new>);
    # assert the resulting CMO carries the target revision's schema_url.


if __name__ == "__main__":
    workflow_create()
    workflow_read_unknown()
    workflow_migrate()
    print("OK")
```

Per-convention specifics:

- **spatial** — migration is the honest lossy case. A 2D r1 doc migrates cleanly
  to r2. A 3D r1 doc _cannot_ (r2 is strict-2D): the example detects this by
  catching the `ValueError` from validating/inserting under r2, prints that the
  migration is lossy, and shows the two real choices (drop the non-XY axis to
  fit r2, or keep the data at r1). No silent data loss.
- **proj** — clean same-shape migration r1 → r2 (corrected URLs + `proj:code`
  regex). The example builds the r2 data from the extracted r1 fields and shows
  the CMO `schema_url` changing from the `zarr-experimental` r1 URL to the
  commit-pinned `zarr-conventions/proj` r2 URL.
- **multiscales / license / uom** — single revision today. The create and
  read-unknown workflows are full; the migrate workflow shows the identical
  detect → extract → (rebuild) → insert scaffold as an identity migration, with
  a comment that there is only one revision now and the same code will handle a
  real revision when one lands.

API-shape note for the example author: `validate`/`extract` accept a keyword
`revision=` on the revisioned facades (`spatial`/`proj`) but the flat modules'
`validate(data)` / `extract(attrs)` take no `revision` argument (they have a
single revision). So the flat-convention examples call `validate(data)` /
`extract(attrs)` plainly; only the spatial/proj examples pass `revision=`. This
asymmetry is expected (a flat module has nothing to disambiguate) — do not try
to pass `revision=` to a flat module's `validate`/`extract`.

The scripts double as the litmus test for "is the API pain-free?": each workflow
must be expressible with only the public API. If any needs private access or
contortions, that is a signal to revisit the API (the `detect` addition is
expected to close the gap; confirm while writing).

## Part C: Test that runs the examples

New `tests/test_examples.py`:

- Discovers scripts via `Path(__file__).parent.parent / "examples"` glob `*.py`,
  with a sanity `assert len(scripts) >= 5`.
- Parametrizes over them; runs each as a subprocess
  (`subprocess.run([sys.executable, str(script)], ...)`) and asserts
  `returncode == 0`. Subprocess (not import) runs the script the way a user
  would, exercising the `__main__` path. On failure, include the script's
  captured stdout/stderr in the assertion message for debuggability.
- Behavioral assertions live INSIDE each example (e.g. "migrated CMO has the new
  schema_url"); the test asserts clean exit, not exact stdout (stdout is
  narration and brittle).
- Tests are non-package (absolute imports); this test needs no conftest helper.

No new nox session: the existing `tests` session runs all of `tests/`, so
`test_examples.py` is covered by `nox -s tests` and CI automatically. (A
dedicated session was considered and rejected as unnecessary surface.)

## Out of scope

- A generic `migrate()` routine (migration is per-convention judgment; examples
  hand-write it).
- Extending the `ConventionModule` protocol to require `detect`.
- Examples for multi-convention documents beyond what each single-convention
  script needs (the aggregate `detect_revisions` is exercised by the unit tests,
  not necessarily a dedicated example).
