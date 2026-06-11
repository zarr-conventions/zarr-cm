# Convention Revisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose per-revision submodules for the `spatial` and `proj`
conventions so users can author data at the latest spec while still
reading/validating data created with older convention versions.

**Architecture:** Each of `spatial` and `proj` becomes a Python _package_
containing self-contained per-revision modules (`_r1.py`, `_r2.py`). A facade
`__init__.py` registers revisions, re-exports the latest revision's API, and
dispatches `create`/`insert`/`validate`/`extract` by a keyword-only `revision=`
argument. Write functions default to the latest revision; read functions
auto-detect the revision from the document's pinned `schema_url` commit SHA and
fall back to latest. Top-level aggregate functions gain a
`revisions={convention: id}` override.

**Tech Stack:** Python 3.11+, TypedDict, hatchling, pytest, jsonschema,
pytest-examples, ruff, mypy. Tests live in `tests/` (NOT a package — use
`from conftest import wrap_attrs`, absolute imports).

**Reference spec:**
`docs/superpowers/specs/2026-06-11-convention-revisions-design.md`

**Key constants (use verbatim):**

- spatial r2 snapshot commit SHA: `f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a`
- proj r2 snapshot commit SHA: `d150edbde61b53e9d17520f6d107c9d3689e5910`
- spatial UUID (shared): `689b58e2-cf7b-45e0-9fff-9cfc0883d6b4`
- proj UUID (shared): `f17cb550-5864-4468-aeb7-f3180cfb622f`
- ConventionName for proj stays `"geo-proj"` (do NOT rename the registry key in
  this plan).

---

## File Structure

**spatial package** (replaces `src/zarr_cm/spatial.py`):

- `src/zarr_cm/spatial/__init__.py` — facade: `_REVISIONS`, `LATEST`, public
  `r1`/`r2`, dispatch functions, re-export latest types/constants.
- `src/zarr_cm/spatial/_r1.py` — verbatim copy of current `spatial.py` (2D-or-3D
  draft), URLs unchanged.
- `src/zarr_cm/spatial/_r2.py` — strict-2D shape, `schema_url`/`spec_url` pinned
  to the r2 SHA.

**proj package** (replaces `src/zarr_cm/geo_proj.py`):

- `src/zarr_cm/proj/__init__.py` — facade.
- `src/zarr_cm/proj/_r1.py` — verbatim copy of current `geo_proj.py`, stale URLs
  unchanged.
- `src/zarr_cm/proj/_r2.py` — corrected `zarr-conventions/proj` URLs pinned to
  r2 SHA + `proj:code` regex.
- `src/zarr_cm/geo_proj.py` — thin compat alias re-exporting the `proj`
  package's latest API and names.

**core / aggregate:**

- `src/zarr_cm/_core.py` — add a revision-detection helper.
- `src/zarr_cm/__init__.py` — registry now points at packages; `_detect`
  resolves revisions; aggregate functions gain `revisions=`.

**vendored snapshots / fixtures:**

- `.github/upstream-schemas/spatial/f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.json`
- `.github/upstream-schemas/proj/d150edbde61b53e9d17520f6d107c9d3689e5910.json`
- `tests/schemas/spatial-r2.json`, `tests/schemas/proj-r2.json` (copies used by
  tests; r1 keeps existing `spatial.json` / `geo-proj.json`).

**tests:**

- `tests/test_spatial.py` — split/extend for r1 + r2.
- `tests/test_geo_proj.py` — keep (covers compat alias + r1).
- `tests/test_proj.py` — new, covers proj r1 + r2.
- `tests/test_revisions.py` — new, cross-cutting detection/round-trip.
- `tests/test_multi.py` — extend for `revisions=` override.

**docs:**

- `docs/index.md`, `docs/api.md` — update examples/output and add `proj`.

---

## Task 1: Convert spatial.py into a package with r1 (no behavior change)

**Files:**

- Create: `src/zarr_cm/spatial/_r1.py`
- Create: `src/zarr_cm/spatial/__init__.py`
- Delete: `src/zarr_cm/spatial.py`
- Test: existing `tests/test_spatial.py` (must keep passing)

- [ ] **Step 1: Create the package dir and move current code into `_r1.py`**

```bash
mkdir -p src/zarr_cm/spatial
git mv src/zarr_cm/spatial.py src/zarr_cm/spatial/_r1.py
```

- [ ] **Step 2: Make `__init__.py` re-export `_r1` so the public API is
      unchanged**

Create `src/zarr_cm/spatial/__init__.py`:

```python
"""spatial convention: https://github.com/zarr-conventions/spatial

Exposes revisions of the spatial convention. ``r1`` is the original
2D-or-3D draft; later revisions track upstream changes. The package-level
functions dispatch by a keyword-only ``revision`` argument and default to
the latest revision for writes / auto-detect for reads.
"""

from __future__ import annotations

from typing import Any

from . import _r1

_REVISIONS = {"r1": _r1}
LATEST = "r1"

# public per-revision namespaces
r1 = _r1

# re-export latest revision's types/constants at package level
from ._r1 import (  # noqa: E402
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    SpatialAttrs,
    SpatialConventionAttrs,
)


def _revision(label: str) -> Any:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


def create(*args: Any, revision: str = LATEST, **kwargs: Any) -> Any:
    return _revision(revision).create(*args, **kwargs)


def insert(
    attrs: dict[str, Any], data: Any, *, revision: str = LATEST, overwrite: bool = False
) -> dict[str, Any]:
    return _revision(revision).insert(attrs, data, overwrite=overwrite)


def validate(data: dict[str, Any], *, revision: str = LATEST) -> Any:
    return _revision(revision).validate(data)


def extract(attrs: dict[str, Any], *, revision: str = LATEST) -> Any:
    return _revision(revision).extract(attrs)
```

> Note: at this point there is only `r1`, so `validate`/`extract` default to
> `LATEST` (== r1). Auto-detection arrives in Task 7 once r2 exists.

- [ ] **Step 3: Run the existing spatial tests to verify nothing broke**

Run: `uv run pytest tests/test_spatial.py -q` Expected: PASS (same count as
before — the public `zarr_cm.spatial` API is unchanged).

- [ ] **Step 4: Run mypy on the package**

Run: `uv run mypy src/zarr_cm/spatial` Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add -A src/zarr_cm/spatial
git commit -m "refactor: make spatial a package with r1 revision"
```

---

## Task 2: Add spatial r2 (strict 2D) module

**Files:**

- Create: `src/zarr_cm/spatial/_r2.py`
- Test: `tests/test_spatial.py` (add r2 tests)

- [ ] **Step 1: Write failing r2 tests**

Append to `tests/test_spatial.py`:

```python
from zarr_cm.spatial import r1 as spatial_r1
from zarr_cm.spatial import r2 as spatial_r2


def test_r2_accepts_2d() -> None:
    result = spatial_r2.validate({"spatial:dimensions": ["y", "x"]})
    assert result == {"spatial:dimensions": ["y", "x"]}


def test_r2_rejects_3d_dimensions() -> None:
    with pytest.raises(ValueError, match="exactly 2"):
        spatial_r2.validate({"spatial:dimensions": ["z", "y", "x"]})


def test_r2_rejects_6_element_bbox() -> None:
    with pytest.raises(ValueError, match="exactly 4"):
        spatial_r2.validate(
            {
                "spatial:dimensions": ["y", "x"],
                "spatial:bbox": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            }
        )


def test_r2_rejects_nonpositive_shape_item() -> None:
    with pytest.raises(ValueError, match="positive"):
        spatial_r2.validate(
            {"spatial:dimensions": ["y", "x"], "spatial:shape": [0, 10]}
        )


def test_r2_schema_url_pinned_to_commit() -> None:
    assert "f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a" in spatial_r2.SCHEMA_URL
    assert "refs/tags/v1" not in spatial_r2.SCHEMA_URL


def test_r1_still_accepts_3d() -> None:
    result = spatial_r1.validate({"spatial:dimensions": ["z", "y", "x"]})
    assert result == {"spatial:dimensions": ["z", "y", "x"]}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_spatial.py -k "r2 or r1_still" -q` Expected: FAIL
— `ImportError`/`AttributeError`: `spatial` has no attribute `r2`.

- [ ] **Step 3: Create `src/zarr_cm/spatial/_r2.py`**

```python
"""spatial convention, revision r2 (strict 2D).

Snapshot of upstream main at commit f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.
Narrows every dimension-bearing key to a fixed 2D length and requires shape
items to be positive.
"""

from __future__ import annotations

from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)

SpatialAttrs = TypedDict(
    "SpatialAttrs",
    {
        "spatial:dimensions": list[str],
        "spatial:bbox": NotRequired[list[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float]],
        "spatial:shape": NotRequired[list[int]],
        "spatial:registration": NotRequired[str],
    },
)

SpatialConventionAttrs = TypedDict(
    "SpatialConventionAttrs",
    {
        "zarr_conventions": list[ConventionMetadataObject],
        "spatial:dimensions": list[str],
        "spatial:bbox": NotRequired[list[float]],
        "spatial:transform_type": NotRequired[str],
        "spatial:transform": NotRequired[list[float]],
        "spatial:shape": NotRequired[list[int]],
        "spatial:registration": NotRequired[str],
    },
)

UUID: Final = "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4"
_COMMIT: Final = "f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a"
SCHEMA_URL: Final = (
    f"https://raw.githubusercontent.com/zarr-conventions/spatial/{_COMMIT}/schema.json"
)
SPEC_URL: Final = (
    f"https://github.com/zarr-conventions/spatial/blob/{_COMMIT}/README.md"
)

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "spatial:",
    "description": "Spatial coordinate information",
}

CONVENTION_KEYS: Final = {
    "spatial:dimensions",
    "spatial:bbox",
    "spatial:transform_type",
    "spatial:transform",
    "spatial:shape",
    "spatial:registration",
}

# r2: every dimension-bearing key is a fixed 2D length.
_VALID_LENGTHS: Final[dict[str, int]] = {
    "spatial:dimensions": 2,
    "spatial:bbox": 4,
    "spatial:transform": 6,
    "spatial:shape": 2,
}

_VALID_REGISTRATIONS: Final = ("node", "pixel")


def create(
    *,
    dimensions: list[str],
    bbox: list[float] | None = None,
    transform_type: str | None = None,
    transform: list[float] | None = None,
    shape: list[int] | None = None,
    registration: str | None = None,
) -> SpatialAttrs:
    """Create a ``SpatialAttrs`` dict (r2, strict 2D) from keyword arguments."""
    result = SpatialAttrs({"spatial:dimensions": dimensions})
    if bbox is not None:
        result["spatial:bbox"] = bbox
    if transform_type is not None:
        result["spatial:transform_type"] = transform_type
    if transform is not None:
        result["spatial:transform"] = transform
    if shape is not None:
        result["spatial:shape"] = shape
    if registration is not None:
        result["spatial:registration"] = registration
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: SpatialAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert spatial (r2) convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, dict(data), overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], SpatialAttrs]:
    """Extract spatial (r2) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, SpatialAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> SpatialAttrs:
    """Validate spatial (r2) convention data: strict 2D, positive shape items."""
    if "spatial:dimensions" not in data:
        msg = "'spatial:dimensions' is required"
        raise ValueError(msg)

    for key, expected in _VALID_LENGTHS.items():
        if key in data:
            n = len(data[key])
            if n != expected:
                msg = f"'{key}' must have exactly {expected} items, got {n}"
                raise ValueError(msg)

    if "spatial:shape" in data and any(v < 1 for v in data["spatial:shape"]):
        msg = "'spatial:shape' items must be positive (>= 1)"
        raise ValueError(msg)

    if (
        "spatial:registration" in data
        and data["spatial:registration"] not in _VALID_REGISTRATIONS
    ):
        msg = f"'spatial:registration' must be one of {_VALID_REGISTRATIONS}, got {data['spatial:registration']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
```

- [ ] **Step 4: Register r2 in the facade**

In `src/zarr_cm/spatial/__init__.py`, change the registry and latest, add the
`r2` alias, and switch the re-export to `_r2`:

```python
from . import _r1, _r2

_REVISIONS = {"r1": _r1, "r2": _r2}
LATEST = "r2"

r1 = _r1
r2 = _r2

from ._r2 import (  # noqa: E402
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    SpatialAttrs,
    SpatialConventionAttrs,
)
```

> Leave the `validate`/`extract` defaults as `revision=LATEST` for now; Task 7
> converts reads to auto-detect. The existing `tests/test_spatial.py` write
> tests call `spatial.create(...)` which now produces r2 — verify they still
> pass in the next step (the existing tests use 2D inputs, so they pass; the
> `test_insert_spatial_3d_with_extras` test uses `spatial.insert`, not
> `create`/`validate`, so it does not validate and still passes).

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_spatial.py -q` Expected: PASS (all existing + new
r1/r2 tests).

- [ ] **Step 6: mypy**

Run: `uv run mypy src/zarr_cm/spatial` Expected: no new errors.

- [ ] **Step 7: Commit**

```bash
git add -A src/zarr_cm/spatial tests/test_spatial.py
git commit -m "feat: add spatial r2 (strict 2D) revision"
```

---

## Task 3: Vendor the spatial r2 upstream schema + fixture test

**Files:**

- Create:
  `.github/upstream-schemas/spatial/f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.json`
- Create: `tests/schemas/spatial-r2.json` (copy of the above)
- Test: `tests/test_spatial.py`

- [ ] **Step 1: Download the pinned upstream schema**

```bash
mkdir -p .github/upstream-schemas/spatial
curl -fsSL "https://raw.githubusercontent.com/zarr-conventions/spatial/f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a/schema.json" \
  -o .github/upstream-schemas/spatial/f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.json
cp .github/upstream-schemas/spatial/f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.json tests/schemas/spatial-r2.json
```

Expected: both files exist and contain valid JSON
(`python -c "import json,sys; json.load(open(sys.argv[1]))" tests/schemas/spatial-r2.json`
exits 0).

- [ ] **Step 2: Write a failing fixture test**

Append to `tests/test_spatial.py`:

```python
R2_SCHEMA_PATH = Path(__file__).parent / "schemas" / "spatial-r2.json"
R2_SCHEMA = json.loads(R2_SCHEMA_PATH.read_text())


def test_r2_create_validates_against_vendored_schema() -> None:
    data = spatial_r2.create(
        dimensions=["y", "x"],
        bbox=[0.0, 0.0, 1.0, 1.0],
        transform=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
        shape=[100, 200],
        registration="pixel",
    )
    node = wrap_attrs(spatial_r2.insert({}, data))
    jsonschema.validate(node, R2_SCHEMA)
```

- [ ] **Step 3: Run to verify it passes (or surfaces a real mismatch)**

Run:
`uv run pytest tests/test_spatial.py::test_r2_create_validates_against_vendored_schema -v`
Expected: PASS. If it FAILS, the r2 Python shape disagrees with the vendored
schema — fix `_r2.py` to match the schema (the schema is the source of truth),
then re-run.

- [ ] **Step 4: Commit**

```bash
git add .github/upstream-schemas/spatial tests/schemas/spatial-r2.json tests/test_spatial.py
git commit -m "test: vendor spatial r2 schema and validate r2 output against it"
```

---

## Task 4: Convert geo_proj.py into a proj package with r1 + compat alias

**Files:**

- Create: `src/zarr_cm/proj/_r1.py`
- Create: `src/zarr_cm/proj/__init__.py`
- Create: `src/zarr_cm/geo_proj.py` (compat alias)
- Delete: original `src/zarr_cm/geo_proj.py`
- Test: existing `tests/test_geo_proj.py` (must keep passing)

- [ ] **Step 1: Move current geo_proj code into the package as `_r1.py`**

```bash
mkdir -p src/zarr_cm/proj
git mv src/zarr_cm/geo_proj.py src/zarr_cm/proj/_r1.py
```

- [ ] **Step 2: Create `src/zarr_cm/proj/__init__.py` (facade, r1 only for
      now)**

```python
"""proj convention: https://github.com/zarr-conventions/proj

Formerly ``geo-proj``. ``r1`` is the original draft (kept verbatim, including
its historical URLs, so existing documents round-trip). Later revisions track
upstream. Functions dispatch by a keyword-only ``revision`` argument.
"""

from __future__ import annotations

from typing import Any

from . import _r1

_REVISIONS = {"r1": _r1}
LATEST = "r1"

r1 = _r1

from ._r1 import (  # noqa: E402
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    GeoProjAttrs,
    GeoProjConventionAttrs,
)


def _revision(label: str) -> Any:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


def create(*args: Any, revision: str = LATEST, **kwargs: Any) -> Any:
    return _revision(revision).create(*args, **kwargs)


def insert(
    attrs: dict[str, Any], data: Any, *, revision: str = LATEST, overwrite: bool = False
) -> dict[str, Any]:
    return _revision(revision).insert(attrs, data, overwrite=overwrite)


def validate(data: dict[str, Any], *, revision: str = LATEST) -> Any:
    return _revision(revision).validate(data)


def extract(attrs: dict[str, Any], *, revision: str = LATEST) -> Any:
    return _revision(revision).extract(attrs)
```

- [ ] **Step 3: Create the `geo_proj` compat alias module**

Create `src/zarr_cm/geo_proj.py`:

```python
"""Backward-compatibility alias for the renamed ``proj`` convention package.

Upstream renamed ``geo-proj`` to ``proj``. Importing ``zarr_cm.geo_proj``
continues to work and exposes the latest ``proj`` revision's API.
"""

from __future__ import annotations

from zarr_cm.proj import (
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    GeoProjAttrs,
    GeoProjConventionAttrs,
    create,
    extract,
    insert,
    validate,
)

__all__ = [
    "CMO",
    "CONVENTION_KEYS",
    "SCHEMA_URL",
    "SPEC_URL",
    "UUID",
    "GeoProjAttrs",
    "GeoProjConventionAttrs",
    "create",
    "extract",
    "insert",
    "validate",
]
```

- [ ] **Step 4: Run existing geo_proj tests**

Run: `uv run pytest tests/test_geo_proj.py -q` Expected: PASS (public
`zarr_cm.geo_proj` API unchanged — still r1).

- [ ] **Step 5: mypy**

Run: `uv run mypy src/zarr_cm/proj src/zarr_cm/geo_proj.py` Expected: no new
errors.

- [ ] **Step 6: Commit**

```bash
git add -A src/zarr_cm/proj src/zarr_cm/geo_proj.py
git commit -m "refactor: make proj a package with r1 + geo_proj compat alias"
```

---

## Task 5: Add proj r2 (corrected URLs + proj:code regex)

**Files:**

- Create: `src/zarr_cm/proj/_r2.py`
- Test: `tests/test_proj.py` (new)

- [ ] **Step 1: Write failing r2 tests in a new file `tests/test_proj.py`**

```python
from __future__ import annotations

import pytest

from zarr_cm.proj import r1 as proj_r1
from zarr_cm.proj import r2 as proj_r2


def test_r2_accepts_valid_code() -> None:
    result = proj_r2.validate({"proj:code": "EPSG:4326"})
    assert result == {"proj:code": "EPSG:4326"}


def test_r2_rejects_malformed_code() -> None:
    with pytest.raises(ValueError, match="proj:code"):
        proj_r2.validate({"proj:code": "epsg-4326"})


def test_r1_accepts_malformed_code() -> None:
    # r1 has no regex; only the "exactly one" rule applies.
    result = proj_r1.validate({"proj:code": "epsg-4326"})
    assert result == {"proj:code": "epsg-4326"}


def test_r2_still_enforces_exactly_one() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        proj_r2.validate({})


def test_r2_schema_url_corrected_and_pinned() -> None:
    assert "zarr-conventions/proj" in proj_r2.SCHEMA_URL
    assert "zarr-experimental" not in proj_r2.SCHEMA_URL
    assert "d150edbde61b53e9d17520f6d107c9d3689e5910" in proj_r2.SCHEMA_URL
    assert "refs/tags/v1" not in proj_r2.SCHEMA_URL


def test_r2_cmo_uses_corrected_url() -> None:
    assert proj_r2.CMO["schema_url"] == proj_r2.SCHEMA_URL
    assert proj_r2.CMO["uuid"] == "f17cb550-5864-4468-aeb7-f3180cfb622f"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_proj.py -q` Expected: FAIL — `proj` has no
attribute `r2`.

- [ ] **Step 3: Create `src/zarr_cm/proj/_r2.py`**

```python
"""proj convention, revision r2.

Snapshot of upstream main at commit d150edbde61b53e9d17520f6d107c9d3689e5910.
Corrects the schema/spec URLs to the zarr-conventions/proj repo and adds the
``proj:code`` authority pattern. The "exactly one of code/wkt2/projjson" rule
is unchanged from r1.
"""

from __future__ import annotations

import re
from typing import Any, Final, NotRequired, TypedDict

from zarr_cm._core import (
    ConventionMetadataObject,
    extract_convention,
    insert_convention,
)

GeoProjAttrs = TypedDict(
    "GeoProjAttrs",
    {
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[dict[str, Any]],
    },
)

GeoProjConventionAttrs = TypedDict(
    "GeoProjConventionAttrs",
    {
        "zarr_conventions": list[ConventionMetadataObject],
        "proj:code": NotRequired[str],
        "proj:wkt2": NotRequired[str],
        "proj:projjson": NotRequired[dict[str, Any]],
    },
)

UUID: Final = "f17cb550-5864-4468-aeb7-f3180cfb622f"
_COMMIT: Final = "d150edbde61b53e9d17520f6d107c9d3689e5910"
SCHEMA_URL: Final = (
    f"https://raw.githubusercontent.com/zarr-conventions/proj/{_COMMIT}/schema.json"
)
SPEC_URL: Final = f"https://github.com/zarr-conventions/proj/blob/{_COMMIT}/README.md"

CMO: Final[ConventionMetadataObject] = {
    "uuid": UUID,
    "schema_url": SCHEMA_URL,
    "spec_url": SPEC_URL,
    "name": "proj:",
    "description": "Coordinate reference system information for geospatial data",
}

CONVENTION_KEYS: Final = {"proj:code", "proj:wkt2", "proj:projjson"}

_CODE_PATTERN: Final = re.compile(r"^[A-Z]+:[0-9]+$")


def create(
    *,
    code: str | None = None,
    wkt2: str | None = None,
    projjson: dict[str, Any] | None = None,
) -> GeoProjAttrs:
    """Create a ``GeoProjAttrs`` dict (r2) from keyword arguments."""
    result = GeoProjAttrs()
    if code is not None:
        result["proj:code"] = code
    if wkt2 is not None:
        result["proj:wkt2"] = wkt2
    if projjson is not None:
        result["proj:projjson"] = projjson
    validate(dict(result))
    return result


def insert(
    attrs: dict[str, Any], data: GeoProjAttrs, *, overwrite: bool = False
) -> dict[str, Any]:
    """Insert proj (r2) convention metadata into an attributes dict."""
    return insert_convention(attrs, CMO, dict(data), overwrite=overwrite)


def extract(
    attrs: dict[str, Any],
) -> tuple[dict[str, Any], GeoProjAttrs]:
    """Extract proj (r2) convention metadata from an attributes dict."""
    remaining, convention_data = extract_convention(
        attrs,
        CONVENTION_KEYS,
        lambda cmo: cmo.get("uuid") == UUID,
    )
    return remaining, GeoProjAttrs(**convention_data)  # type: ignore[typeddict-item]


def validate(data: dict[str, Any]) -> GeoProjAttrs:
    """Validate proj (r2) data.

    Exactly one of ``proj:code``, ``proj:wkt2``, or ``proj:projjson`` must be
    present, and ``proj:code`` (if present) must match ``^[A-Z]+:[0-9]+$``.
    """
    present = [k for k in ("proj:code", "proj:wkt2", "proj:projjson") if k in data]
    if len(present) != 1:
        msg = f"Exactly one of 'proj:code', 'proj:wkt2', 'proj:projjson' must be present, got: {present}"
        raise ValueError(msg)
    if "proj:code" in data and not _CODE_PATTERN.match(data["proj:code"]):
        msg = f"'proj:code' must match {_CODE_PATTERN.pattern!r}, got {data['proj:code']!r}"
        raise ValueError(msg)
    return data  # type: ignore[return-value]
```

- [ ] **Step 4: Register r2 in `src/zarr_cm/proj/__init__.py`**

```python
from . import _r1, _r2

_REVISIONS = {"r1": _r1, "r2": _r2}
LATEST = "r2"

r1 = _r1
r2 = _r2

from ._r2 import (  # noqa: E402
    CMO,
    CONVENTION_KEYS,
    SCHEMA_URL,
    SPEC_URL,
    UUID,
    GeoProjAttrs,
    GeoProjConventionAttrs,
)
```

- [ ] **Step 5: Run proj tests + the compat alias tests**

Run: `uv run pytest tests/test_proj.py tests/test_geo_proj.py -q` Expected:
PASS. Note `tests/test_geo_proj.py` now exercises r2 via the alias; if any test
asserts the old `zarr-experimental` URL or `refs/tags/v1`, update that assertion
to the corrected pinned URL (the alias now exposes latest = r2).

- [ ] **Step 6: mypy**

Run: `uv run mypy src/zarr_cm/proj` Expected: no new errors.

- [ ] **Step 7: Commit**

```bash
git add -A src/zarr_cm/proj tests/test_proj.py tests/test_geo_proj.py
git commit -m "feat: add proj r2 (corrected URLs + proj:code regex)"
```

---

## Task 6: Vendor the proj r2 upstream schema + fixture test

**Files:**

- Create:
  `.github/upstream-schemas/proj/d150edbde61b53e9d17520f6d107c9d3689e5910.json`
- Create: `tests/schemas/proj-r2.json`
- Test: `tests/test_proj.py`

- [ ] **Step 1: Download the pinned upstream schema**

```bash
mkdir -p .github/upstream-schemas/proj
curl -fsSL "https://raw.githubusercontent.com/zarr-conventions/proj/d150edbde61b53e9d17520f6d107c9d3689e5910/schema.json" \
  -o .github/upstream-schemas/proj/d150edbde61b53e9d17520f6d107c9d3689e5910.json
cp .github/upstream-schemas/proj/d150edbde61b53e9d17520f6d107c9d3689e5910.json tests/schemas/proj-r2.json
```

Expected: both files exist and are valid JSON.

- [ ] **Step 2: Write a failing fixture test**

Append to `tests/test_proj.py`:

```python
import json
from pathlib import Path

import jsonschema
from conftest import wrap_attrs

R2_SCHEMA_PATH = Path(__file__).parent / "schemas" / "proj-r2.json"
R2_SCHEMA = json.loads(R2_SCHEMA_PATH.read_text())


def test_r2_create_validates_against_vendored_schema() -> None:
    data = proj_r2.create(code="EPSG:4326")
    node = wrap_attrs(proj_r2.insert({}, data))
    jsonschema.validate(node, R2_SCHEMA)
```

- [ ] **Step 3: Run**

Run:
`uv run pytest tests/test_proj.py::test_r2_create_validates_against_vendored_schema -v`
Expected: PASS. If FAIL, reconcile `_r2.py` against the vendored schema (schema
is source of truth), then re-run.

- [ ] **Step 4: Commit**

```bash
git add .github/upstream-schemas/proj tests/schemas/proj-r2.json tests/test_proj.py
git commit -m "test: vendor proj r2 schema and validate r2 output against it"
```

---

## Task 7: Revision-aware reads (auto-detect by pinned schema_url SHA)

**Files:**

- Modify: `src/zarr_cm/_core.py` (add `detect_revision` helper)
- Modify: `src/zarr_cm/spatial/__init__.py`, `src/zarr_cm/proj/__init__.py`
  (read funcs auto-detect)
- Test: `tests/test_revisions.py` (new)

- [ ] **Step 1: Write failing detection/round-trip tests in
      `tests/test_revisions.py`**

```python
from __future__ import annotations

import pytest

from zarr_cm import proj, spatial


def test_spatial_extract_autodetects_r1_3d() -> None:
    # Write with r1 (3D), read back with no revision arg -> must detect r1.
    data = spatial.create(dimensions=["z", "y", "x"], revision="r1")
    attrs = spatial.insert({}, data, revision="r1")
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data  # round-trips; r2 would have rejected 3D


def test_spatial_validate_autodetects_r1() -> None:
    attrs = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    # extract auto-detects r1 (allows 3D); validating the extracted data with the
    # detected revision must not raise.
    _r, extracted = spatial.extract(attrs)
    spatial.validate(dict(extracted), revision="r1")  # r1 allows 3D


def test_spatial_extract_detects_r2() -> None:
    data = spatial.create(dimensions=["y", "x"])  # default latest = r2
    attrs = spatial.insert({}, data)
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == data


def test_spatial_extract_unknown_url_falls_back_to_latest() -> None:
    # Legacy doc: spatial UUID but dangling tags/v1 url -> falls back to LATEST (r2).
    attrs = {
        "spatial:dimensions": ["y", "x"],
        "zarr_conventions": [
            {
                "uuid": "689b58e2-cf7b-45e0-9fff-9cfc0883d6b4",
                "schema_url": "https://raw.githubusercontent.com/zarr-conventions/spatial/refs/tags/v1/schema.json",
            }
        ],
    }
    _remaining, extracted = spatial.extract(attrs)
    assert extracted == {"spatial:dimensions": ["y", "x"]}


def test_extract_revision_override_wins() -> None:
    # r2 doc but force-read as r1 via explicit revision.
    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))
    _remaining, extracted = spatial.extract(attrs, revision="r1")
    assert extracted == {"spatial:dimensions": ["y", "x"]}


def test_proj_extract_autodetects_r1_url() -> None:
    data = proj.create(code="EPSG:4326", revision="r1")
    attrs = proj.insert({}, data, revision="r1")
    _remaining, extracted = proj.extract(attrs)
    assert extracted == data
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_revisions.py -q` Expected: FAIL —
`extract`/`validate` still default to `revision=LATEST` and would mis-handle r1
docs / the override.

- [ ] **Step 3: Add `detect_revision` to `src/zarr_cm/_core.py`**

Append:

```python
def detect_revision(
    attrs: dict[str, Any],
    uuid: str,
    schema_url_by_revision: dict[str, str],
) -> str | None:
    """Return the revision label whose pinned schema_url matches the document's CMO.

    Looks for a convention-metadata object in ``attrs['zarr_conventions']``
    whose ``uuid`` matches *uuid*. If found, returns the revision label whose
    ``schema_url`` equals that CMO's ``schema_url``. Returns ``None`` if the
    convention is absent, or present but carrying an unrecognized schema_url
    (e.g. a legacy/dangling URL) — callers fall back to the latest revision.
    """
    by_url = {url: label for label, url in schema_url_by_revision.items()}
    for cmo in attrs.get("zarr_conventions", []):
        if cmo.get("uuid") == uuid:
            return by_url.get(cmo.get("schema_url", ""))
    return None
```

- [ ] **Step 4: Make spatial reads auto-detect**

In `src/zarr_cm/spatial/__init__.py`, add a schema-url map and rewrite
`validate`/`extract` (replace the versions from Task 1/2):

```python
from zarr_cm._core import detect_revision  # add to imports

_SCHEMA_URL_BY_REVISION = {label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()}


def _resolve_read_revision(attrs: dict[str, Any], revision: str | None) -> str:
    if revision is not None:
        return revision
    return detect_revision(attrs, UUID, _SCHEMA_URL_BY_REVISION) or LATEST


def validate(data: dict[str, Any], *, revision: str | None = None) -> Any:
    return _revision(_resolve_read_revision(data, revision)).validate(data)


def extract(attrs: dict[str, Any], *, revision: str | None = None) -> Any:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)
```

> `validate` receives the _convention data_ dict, which usually has no
> `zarr_conventions` array; detection then returns `None` and falls back to
> `LATEST`. That is correct: bare data with no embedded CMO is validated against
> latest unless a revision is named. The meaningful auto-detection path is
> `extract` (operates on full attrs).

- [ ] **Step 5: Make proj reads auto-detect**

Apply the identical change to `src/zarr_cm/proj/__init__.py` (same
`detect_revision` import, `_SCHEMA_URL_BY_REVISION`, `_resolve_read_revision`,
and the two read functions). The `UUID`/`LATEST`/`_REVISIONS` names already
exist there.

- [ ] **Step 6: Run revision + all convention tests**

Run:
`uv run pytest tests/test_revisions.py tests/test_spatial.py tests/test_proj.py tests/test_geo_proj.py -q`
Expected: PASS.

- [ ] **Step 7: mypy**

Run: `uv run mypy src/zarr_cm` Expected: no new errors.

- [ ] **Step 8: Commit**

```bash
git add src/zarr_cm/_core.py src/zarr_cm/spatial/__init__.py src/zarr_cm/proj/__init__.py tests/test_revisions.py
git commit -m "feat: auto-detect convention revision on read by pinned schema_url"
```

---

## Task 8: Aggregate functions — `revisions=` override + revision-aware detection

**Files:**

- Modify: `src/zarr_cm/__init__.py`
- Test: `tests/test_multi.py`

- [ ] **Step 1: Write failing aggregate tests**

Append to `tests/test_multi.py`:

```python
def test_create_many_revision_override() -> None:
    # Force spatial r1 so a 3D doc is allowed.
    result = create_many(
        {"spatial": {"spatial:dimensions": ["z", "y", "x"]}},
        revisions={"spatial": "r1"},
    )
    assert result["spatial:dimensions"] == ["z", "y", "x"]
    # CMO carries the r1 (dangling tags/v1) url, not the r2 pinned url.
    urls = [c.get("schema_url", "") for c in result["zarr_conventions"]]
    assert any("refs/tags/v1" in u for u in urls)


def test_extract_all_autodetects_mixed_revisions() -> None:
    from zarr_cm import proj, spatial

    attrs = spatial.insert(
        {}, spatial.create(dimensions=["z", "y", "x"], revision="r1"), revision="r1"
    )
    attrs = proj.insert(attrs, proj.create(code="EPSG:4326"))  # proj latest = r2
    _remaining, extracted = extract_all(attrs)
    assert extracted["spatial"]["spatial:dimensions"] == ["z", "y", "x"]
    assert extracted["geo-proj"]["proj:code"] == "EPSG:4326"


def test_extract_many_revision_override() -> None:
    from zarr_cm import spatial

    attrs = spatial.insert({}, spatial.create(dimensions=["y", "x"]))  # r2
    _remaining, extracted = extract_many(
        attrs, ["spatial"], revisions={"spatial": "r1"}
    )
    assert extracted["spatial"] == {"spatial:dimensions": ["y", "x"]}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_multi.py -k "revision or mixed" -q` Expected:
FAIL — aggregate functions do not accept `revisions=` yet.

- [ ] **Step 3: Thread `revisions=` through aggregate functions**

In `src/zarr_cm/__init__.py`:

(a) Update the registry to import the packages (the import line
`from . import geo_proj, multiscales, spatial, uom` keeps working because
`geo_proj` is the alias module; add `proj`):

```python
from . import geo_proj, multiscales, proj, spatial, uom
```

Keep `_REGISTRY` keyed by display name; map `"geo-proj"` to the `proj` package
(not the `geo_proj` alias) so revision dispatch resolves there:

```python
_REGISTRY: Final[dict[ConventionName, types.ModuleType]] = {
    "geo-proj": proj,
    "spatial": spatial,
    "multiscales": multiscales,
    "license": license_,
    "uom": uom,
}
```

(b) Add `revisions` to the write aggregates. For modules that accept `revision=`
(spatial, proj), pass it; others ignore it. Use a helper:

```python
def _rev_kwargs(
    mod: types.ModuleType,
    revisions: dict[ConventionName, str] | None,
    name: ConventionName,
) -> dict[str, str]:
    """Return {'revision': label} if this module supports it and a label is given."""
    if revisions and name in revisions and hasattr(mod, "_REVISIONS"):
        return {"revision": revisions[name]}
    return {}
```

Update `create_many`:

```python
def create_many(
    conventions: dict[ConventionName, dict[str, Any]],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, data in conventions.items():
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        mod.validate(data, **rk)
        result = mod.insert(result, data, overwrite=True, **rk)
    return result
```

Update `insert_many` the same way (add `revisions` kw-only param after
`overwrite`, build `rk`, pass to `validate` and `insert`).

(c) Add `revisions` to the read aggregates. `validate_many` / `extract_many`:

```python
def validate_many(
    attrs: dict[str, Any],
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> dict[str, Any]:
    for name in conventions:
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        _, extracted = mod.extract(attrs, **rk)
        mod.validate(dict(extracted), **rk)
    return attrs


def extract_many(
    attrs: dict[str, Any],
    conventions: Iterable[ConventionName],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> tuple[dict[str, Any], dict[ConventionName, dict[str, Any]]]:
    remaining = attrs
    extracted: dict[ConventionName, dict[str, Any]] = {}
    for name in conventions:
        mod = _get_module(name)
        rk = _rev_kwargs(mod, revisions, name)
        remaining, data = mod.extract(remaining, **rk)
        extracted[name] = dict(data)
    return remaining, extracted
```

> When `revisions` is absent for a convention, no `revision` kwarg is passed, so
> spatial/proj fall back to their own auto-detect-on-read behavior from Task 7.
> That is exactly the desired default.

(d) `validate_all` / `extract_all` — forward `revisions`:

```python
def validate_all(
    attrs: dict[str, Any],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> dict[str, Any]:
    return validate_many(attrs, _detect_conventions(attrs), revisions=revisions)


def extract_all(
    attrs: dict[str, Any],
    *,
    revisions: dict[ConventionName, str] | None = None,
) -> tuple[dict[str, Any], dict[ConventionName, dict[str, Any]]]:
    return extract_many(attrs, _detect_conventions(attrs), revisions=revisions)
```

(e) Top-level type re-exports (`SpatialAttrs`, `GeoProjAttrs`, etc.) — these
import lines now resolve to the latest revision automatically because the
packages re-export latest. No change needed beyond confirming
`from .spatial import SpatialAttrs, SpatialConventionAttrs` and
`from .geo_proj import GeoProjAttrs, GeoProjConventionAttrs` still resolve (they
do — alias re-exports them).

- [ ] **Step 4: Run aggregate + full suite**

Run: `uv run pytest tests/test_multi.py tests/test_package.py -q` Expected:
PASS. If `test_multi.py`'s existing
`create_many({"geo-proj": {"proj:code": "EPSG:4326"}})` assertions check the old
`zarr-experimental` URL, update them to the r2 pinned `zarr-conventions/proj`
URL (latest is now r2). `"EPSG:4326"` matches the r2 regex, so the data itself
stays valid.

- [ ] **Step 5: mypy**

Run: `uv run mypy src/zarr_cm` Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
git add src/zarr_cm/__init__.py tests/test_multi.py
git commit -m "feat: revisions= override on aggregate functions"
```

---

## Task 9: Update docs (examples, output, add proj)

**Files:**

- Modify: `docs/index.md`
- Modify: `docs/api.md`
- Test: `tests/test_docs.py`

- [ ] **Step 1: Update `docs/index.md` example output for the new latest URLs**

The `geo_proj` example currently prints a CMO with the old `zarr-experimental`
URL and `refs/tags/v1`. Since `zarr_cm.geo_proj` now exposes proj r2, update the
expected `#>` output block (around lines 54-61) to the r2 CMO:

```text
    'proj:code': 'EPSG:4326',
    'zarr_conventions': [
        {
            'uuid': 'f17cb550-5864-4468-aeb7-f3180cfb622f',
            'schema_url': 'https://raw.githubusercontent.com/zarr-conventions/proj/d150edbde61b53e9d17520f6d107c9d3689e5910/schema.json',
            'spec_url': 'https://github.com/zarr-conventions/proj/blob/d150edbde61b53e9d17520f6d107c9d3689e5910/README.md',
            'name': 'proj:',
            'description': 'Coordinate reference system information for geospatial data',
        },
    ],
```

Keep the surrounding `<!-- blacken-docs:off -->` / `<!-- prettier-ignore -->`
guards intact (per project convention for `#>` blocks). Update the convention
table row (line 16) link to `https://github.com/zarr-conventions/proj` and
module column to `zarr_cm.proj` (mention `zarr_cm.geo_proj` still works).

- [ ] **Step 2: Add a short revision example to `docs/index.md`**

Add a subsection demonstrating the read/write asymmetry. Wrap in the same
guards:

```text
from zarr_cm import spatial

# write defaults to the latest revision (strict 2D)
latest = spatial.create(dimensions=["y", "x"])

# opt into an older revision explicitly
old = spatial.create(dimensions=["z", "y", "x"], revision="r1")
print(sorted(old))
#> ['spatial:dimensions']
```

- [ ] **Step 3: Add `proj` section to `docs/api.md`**

After the existing `## geo-proj` section (`::: zarr_cm.geo_proj`), add:

```markdown
## proj

::: zarr_cm.proj
```

(Keep the `geo-proj` section as the documented compat alias.)

- [ ] **Step 4: Run the docs example tests**

Run: `uv run pytest tests/test_docs.py -q` Expected: PASS. If an example's `#>`
output mismatches, run `uv run pytest tests/test_docs.py --update-examples`
once, then inspect the diff and re-run to confirm.

- [ ] **Step 5: Commit**

```bash
git add docs/index.md docs/api.md
git commit -m "docs: document proj package and convention revisions"
```

---

## Task 10: Point check-upstream tracking at the pinned snapshots

**Files:**

- Modify/confirm: `.github/scripts/` and `.github/workflows/check-upstream.yml`
  (in progress; not yet committed)
- Test: manual dry-run

> This task wires the existing (uncommitted) check-upstream tooling to compare
> upstream `main` against the newest vendored snapshot per tracked convention.
> If the script/workflow does not yet exist in a usable form, create a minimal
> version below; otherwise adapt it.

- [ ] **Step 1: Ensure the tracked set lists spatial + proj with their newest
      snapshot SHAs**

The tracking config must map each convention to: upstream raw `main` schema URL
and the path of the newest vendored snapshot:

- spatial →
  `https://raw.githubusercontent.com/zarr-conventions/spatial/main/schema.json`
  vs
  `.github/upstream-schemas/spatial/f5c536b9a3386e4127e3d2426dcefeebe6e5bf1a.json`
- proj →
  `https://raw.githubusercontent.com/zarr-conventions/proj/main/schema.json` vs
  `.github/upstream-schemas/proj/d150edbde61b53e9d17520f6d107c9d3689e5910.json`

- [ ] **Step 2: Dry-run the check locally**

Run the check script (adapt to its actual entrypoint), e.g.: Run:
`uv run python .github/scripts/check_upstream.py` (or the script's real name)
Expected: exits 0 (no drift) OR reports drift for a convention whose upstream
`main` has moved past the vendored SHA. Either is a valid signal; a drift report
means "snapshot a new revision next."

- [ ] **Step 3: Confirm the workflow only opens an issue / fails — never
      auto-edits source**

Read `.github/workflows/check-upstream.yml` and verify it does not write to
`src/`. Authoring a new `_rN.py` is a human step.

- [ ] **Step 4: Commit the tracking wiring**

```bash
git add .github/scripts .github/workflows/check-upstream.yml
git commit -m "ci: track spatial + proj upstream drift against vendored snapshots"
```

---

## Task 11: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `uv run pytest -q` Expected: all PASS.

- [ ] **Step 2: Run the full lint/type/test gate via nox**

Run: `uv run nox` (or the project's configured sessions: lint, pylint, tests)
Expected: all sessions PASS.

- [ ] **Step 3: Confirm public imports still resolve**

Run:

```bash
uv run python -c "
import zarr_cm
from zarr_cm import spatial, proj, geo_proj
from zarr_cm import SpatialAttrs, GeoProjAttrs
assert spatial.LATEST == 'r2' and proj.LATEST == 'r2'
assert spatial.r1 is not spatial.r2
assert geo_proj.create(code='EPSG:4326')['proj:code'] == 'EPSG:4326'
print('ok')
"
```

Expected: prints `ok`.

- [ ] **Step 4: Final commit if any verification fixups were needed**

```bash
git add -A
git commit -m "chore: verification fixups for convention revisions"
```

---

## Notes for the implementer

- Tests are NOT a package: always `from conftest import wrap_attrs` (absolute).
  No relative imports in `tests/`.
- The schema files are the source of truth for each revision's shape. If a
  fixture test fails, fix the Python `_rN.py` to match the vendored schema, not
  the other way around.
- Revisions are frozen: once `_r1.py` / `_r2.py` ship, do not change their
  behavior. A new upstream change means a new `_r3.py`, never an edit to an
  existing revision.
- `ConventionName` keeps `"geo-proj"` in this plan. A rename to `"proj"` is
  deliberately out of scope.
- Doc code blocks using `#>` output need both `<!-- blacken-docs:off -->` and
  `<!-- prettier-ignore -->` guards.
