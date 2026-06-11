# Convention Revisions — Design

**Date:** 2026-06-11 **Branch:** `bump-proj-and-spatial` **Scope:** `spatial`
and `proj` conventions only.

## Motivation

Upstream Zarr conventions mutate their field shapes **in place** — keeping the
same UUID and the same (dangling) `refs/tags/v1` `schema_url` even as required
keys and cardinalities change. A document written against an older draft is
therefore invalid under the newer one.

`zarr-cm` must do two things at once:

1. **Support the latest published versions** of each convention — new data
   should be authored at the current spec.
2. **Never lock consumers out of older data** — a user must be able to read and
   model metadata they created with an earlier version of a convention.

These two goals split cleanly along **write vs. read**, and that split governs
the entire design.

## Upstream audit (2026-06-11)

There are **no real git tags** on the conventions that are changing; their
`tags/v1` URLs are dangling. Per-convention findings:

| Convention      | Status                                                                                                                                                                                                                                                                                                                                                                    | Action                                                                            |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **spatial**     | REAL revision. `main` narrowed to strictly 2D: `dimensions` exactly 2, `bbox` exactly 4, `transform` exactly 6, `shape` exactly 2 with each item `>= 1`. Our code = the old 2D-or-3D draft. (A `clarify-registration` branch reverts toward 2D/3D and renames the CMO `name` to `"spatial:"` — spec still churning.)                                                      | r1 = 2D-or-3D (current), r2 = strict-2D (`main` snapshot)                         |
| **proj**        | Moved `zarr-experimental/geo-proj` → `zarr-conventions/proj`. UUID unchanged; "exactly one of `code`/`wkt2`/`projjson`" unchanged. Our `SCHEMA_URL`/`SPEC_URL` are doubly stale (wrong org **and** wrong repo). `main` added a `proj:code` pattern `^[A-Z]+:[0-9]+$`. A `shape`/`inheritance` redesign (UUID-keyed, adds spatial fields) lives only on unmerged branches. | r1 = current (stale URLs kept for round-trip), r2 = corrected URLs + `code` regex |
| **multiscales** | Matches `main`; a `release-1.0.0` branch adds a **required `version`** field.                                                                                                                                                                                                                                                                                             | Defer — revision coming, not landed                                               |
| **license**     | Matches upstream; actually **tagged `v1`**.                                                                                                                                                                                                                                                                                                                               | No change                                                                         |
| **uom**         | Matches upstream; actually **tagged `v1`** (minor: array-only scope).                                                                                                                                                                                                                                                                                                     | No change                                                                         |

Only **spatial** and **proj** get the revision machinery now. The other three
adopt the same pattern if and when they actually revise. The redesign branches
on proj (`shape`, `inheritance`) are **not** adopted.

## 1. Revision model & identity

A **revision** is a frozen snapshot of an upstream convention at a specific
commit.

- Each snapshot's `schema.json` is vendored under
  `.github/upstream-schemas/<convention>/<sha>.json`.
- We assign a package-local label `r1`, `r2`, … ordered oldest → newest.
- The **durable identity** of a revision is the upstream **commit SHA**,
  surfaced in the emitted CMO's `schema_url`:
  `https://raw.githubusercontent.com/zarr-conventions/spatial/<sha>/schema.json`
  — pinned to the snapshot commit, **replacing** the dangling `refs/tags/v1`.
- The UUID stays shared across revisions (it is the convention's identity, not
  the revision's).

A written document is therefore **self-describing**: the UUID says _which_
convention, the pinned `schema_url` SHA says _which revision_.
`extract`/`validate` recover the revision by matching the SHA back to a known
snapshot.

## 2. Submodule layout & per-revision contents

Each revisioned convention becomes a package instead of a single module:

```
src/zarr_cm/spatial/
  __init__.py      # facade: revision registry + re-export latest
  _r1.py           # 2D-or-3D draft (verbatim current code)
  _r2.py           # strict-2D (upstream main snapshot)
src/zarr_cm/proj/
  __init__.py
  _r1.py           # current shape, current (stale) URLs
  _r2.py           # corrected zarr-conventions/proj URLs + proj:code regex
```

> Note: the existing module is `geo_proj.py`. The new package is `proj/`
> (matching the upstream rename). The old import path is handled under "Backward
> compatibility" below.

Each `_rN.py` is **self-contained** and owns everything that can drift between
revisions:

- its own `TypedDict`s (`SpatialAttrs`, `SpatialConventionAttrs`, etc.) — the
  types themselves differ (r1 `dimensions` = 2-or-3 items, r2 = exactly 2), so
  they cannot be shared;
- its own `UUID` (shared value, declared locally), `SCHEMA_URL` (pinned to that
  revision's commit SHA), `SPEC_URL`, `CMO`, `CONVENTION_KEYS`;
- its own `create()`, `validate()`, `insert()`, `extract()` — the same
  four-function contract used today.

**spatial concrete shapes:**

- `_r1`:
  `_VALID_LENGTHS = {dimensions:(2,3), bbox:(4,6), transform:(6,9), shape:(2,3)}`
  — verbatim current behavior; `registration` enum `{node, pixel}`.
- `_r2`: `dimensions` exactly 2; `bbox` exactly 4; `transform` exactly 6;
  `shape` exactly 2 with each item `>= 1`; `dimensions` required (matching
  current behavior — we do not model the upstream `node_type`-conditional
  requirement); `registration` enum unchanged.

**proj concrete shapes:**

- `_r1`: current code unchanged, including the existing
  `zarr-experimental/geo-proj` URLs (so already-written docs round-trip to r1).
- `_r2`: corrected `zarr-conventions/proj` URLs pinned to the snapshot SHA;
  `proj:code` validated against `^[A-Z]+:[0-9]+$`; "exactly one of
  `code`/`wkt2`/`projjson`" unchanged.

**Shared plumbing.** `_core.py` (`insert_convention`, `extract_convention`,
`validate_convention_metadata_object`) is revision-agnostic and stays as-is;
each `_rN` passes its own `CMO`/`CONVENTION_KEYS`.

**Duplication is intentional.** `_r1` and `_r2` share near-identical
four-function boilerplate. We choose duplication over a shared base class:
revisions are frozen historical snapshots that must never change once shipped,
so coupling them to a shared abstraction a later revision might need to bend is
the wrong pressure. Each snapshot stands alone.

## 3. Facade + `revision=` defaulting

Each convention's `__init__.py` registers its revisions and re-exports the
latest revision's API.

<!-- blacken-docs:off -->

```python
# src/zarr_cm/spatial/__init__.py
from . import _r1, _r2

_REVISIONS = {"r1": _r1, "r2": _r2}   # insertion order = oldest → newest
LATEST = "r2"

# public per-revision namespaces (the chosen first-class API)
r1 = _r1
r2 = _r2

def _revision(label):
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None

def create(*args, revision=LATEST, **kwargs):
    return _revision(revision).create(*args, **kwargs)

def insert(attrs, data, *, revision=LATEST, overwrite=False):
    return _revision(revision).insert(attrs, data, overwrite=overwrite)

def validate(data, *, revision=None):
    # revision=None → auto-detect from the doc, fall back to LATEST (see §4)
    ...

def extract(attrs, *, revision=None):
    # revision=None → auto-detect from the doc, fall back to LATEST (see §4)
    ...

# latest types re-exported at package level for static typing
from ._r2 import SpatialAttrs, SpatialConventionAttrs
```

<!-- blacken-docs:on -->

Three equivalent ways to target r2, in increasing explicitness:
`spatial.create(...)` (latest) · `spatial.create(..., revision="r2")` ·
`spatial.r2.create(...)`.

`revision=` is keyword-only on every entry point.

## 4. Read/write asymmetry, aggregate functions & detection

The governing principle: **write defaults to latest; read auto-detects.**

| Function   | Default                | Rationale                           |
| ---------- | ---------------------- | ----------------------------------- |
| `create`   | `LATEST`               | author new data at the current spec |
| `insert`   | `LATEST`               | writing — same                      |
| `validate` | auto-detect → `LATEST` | validate the doc as written         |
| `extract`  | auto-detect → `LATEST` | read old data faithfully            |

`revision=` always overrides, in both directions.

**Detection** (`_detect_conventions` in `zarr_cm/__init__.py`) is upgraded to
also resolve a revision per convention:

<!-- blacken-docs:off -->

```python
def _detect(attrs) -> dict[ConventionName, str | None]:
    # {name: revision_label}, or None if the UUID is present
    # but the schema_url SHA is unrecognized
    ...
```

<!-- blacken-docs:on -->

For each convention present (matched by UUID), read the matching CMO's
`schema_url` and look up its pinned commit SHA in that convention's revision
registry. Three outcomes:

- **SHA matches a known revision** → use it.
- **UUID present, URL is legacy / unknown SHA** (e.g. an old doc still carrying
  the dangling `tags/v1` URL) → revision is `None` → resolve to that
  convention's `LATEST`, unless overridden.
- **Override present** → `revisions={"spatial": "r1"}` wins regardless of the
  document.

**Unknown-SHA fallback decision:** resolve to `LATEST` and let validation speak.
If the unknown revision's shape differs, validation may fail — which is honest
(we genuinely do not have that revision) and keeps best-effort reads working. We
do **not** raise eagerly on an unknown SHA.

**Write-side aggregates** gain
`revisions: dict[ConventionName, str] | None = None`; unspecified conventions
use `LATEST`:

```python
create_many({"spatial": {...}}, revisions={"spatial": "r1"})
insert_many(attrs, {...}, revisions={"proj": "r2"})
```

**Read-side aggregates** (`validate_all`, `extract_all`, `validate_many`,
`extract_many`) gain the same `revisions=` kwarg; unspecified conventions use
**detection → fall back to LATEST**:

```python
remaining, extracted = extract_all(attrs)  # auto per-convention
remaining, extracted = extract_all(attrs, revisions={"proj": "r1"})  # force proj r1
```

A mixed document (old r1 spatial + new r2 proj) round-trips correctly with **no
arguments**, because each convention is detected independently from its own
pinned SHA. This is the concrete realization of the motivation.

## 5. Backward compatibility

- **`spatial.create()` and `proj` equivalents now emit r2 (latest) docs.** This
  is a deliberate behavior change so newcomers get the current spec. Users who
  want the old shape pass `revision="r1"`.
- **Top-level `__init__.py` re-exports** (`SpatialAttrs`, `GeoProjAttrs`, …) now
  resolve to the **latest** revision's TypedDicts.
- **`geo_proj` import path.** The module becomes the `proj/` package. To avoid
  breaking `from zarr_cm import geo_proj` and
  `from zarr_cm.geo_proj import GeoProjAttrs`, keep a thin `geo_proj` alias
  module that re-exports from `proj` (latest), with the existing `GeoProjAttrs`
  / `GeoProjConventionAttrs` names preserved. The internal registry key and
  display name handling stay consistent with the current `"geo-proj"`
  ConventionName unless a rename is explicitly decided later.
- Reads of existing documents (carrying old UUIDs / `tags/v1` URLs) resolve to
  `LATEST` via the unknown-SHA fallback, and can be pinned with `revisions=`.

## 6. Testing

- **Vendored snapshots as fixtures.** Each `_rN` gets a test that its `create()`
  output validates against its own vendored
  `.github/upstream-schemas/<convention>/<sha>.json`, so the Python shape and
  the frozen upstream schema cannot silently drift.
- **Per-revision unit tests:**
  - spatial r1: a 3D doc validates. spatial r2: the same 3D doc is rejected; a
    2D doc validates; a `shape` item of `0` is rejected (`minimum: 1`).
  - proj r2: `proj:code` not matching `^[A-Z]+:[0-9]+$` is rejected; r1 accepts
    it; the emitted CMO carries the corrected `zarr-conventions/proj` URL.
- **Round-trip / detection tests:**
  - Write r1 spatial → `extract_all()` (no args) recovers it as r1 via pinned
    SHA; validates; round-trips byte-equal.
  - Mixed doc (r1 spatial + r2 proj) → `extract_all()` detects each
    independently.
  - Legacy doc (UUID present, `tags/v1` URL) → falls back to `LATEST`;
    `revisions=` override forces the intended revision.
- **Tests stay non-package** — `from conftest import wrap_attrs` (absolute
  import); no `__init__.py` in `tests/`.
- **Docs / doctests** updated to show `revision=` and the `revisions=` override,
  keeping the `#>` / pytest-examples format with `blacken-docs:off` and
  `prettier-ignore` guards.

## 7. check-upstream workflow

`.github/workflows/check-upstream.yml` + `.github/scripts/` (in progress): fetch
current upstream `main` for each tracked convention, diff against the newest
vendored snapshot, and **open an issue / fail CI** when upstream has drifted —
signaling "time to snapshot a new revision." It detects drift only; authoring a
new `_rN.py` (with hand-written validation) is a deliberate human step. Wire it
to track **spatial** and **proj** for now.

## Out of scope

- Revisions for `multiscales`, `license`, `uom` (adopt the pattern when they
  revise).
- The proj `shape` / `inheritance` UUID-keyed redesign.
- Auto-generating revision modules from schemas.
