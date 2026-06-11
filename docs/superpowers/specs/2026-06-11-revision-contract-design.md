# Convention Module Contract — Design

**Date:** 2026-06-11 **Branch:** `bump-proj-and-spatial` **Scope:** All
convention modules dispatched by the registry (spatial + proj revision
submodules, and the flat multiscales/license/uom modules).

## Motivation

`zarr-cm` dispatches the same four operations (`create`, `insert`, `extract`,
`validate`) and reads the same module-level constants (`UUID`, `SCHEMA_URL`,
`SPEC_URL`, `CMO`, `CONVENTION_KEYS`) across every convention module — including
each revision submodule (`spatial._r1`, `spatial._r2`, `proj._r1`, `proj._r2`).
Nothing currently _guarantees_ a new revision (or an edit to an existing module)
keeps the call shapes and constants the facade and aggregate layer rely on. An
incompatible change — a renamed constant, a dropped function, `extract`
returning a bare dict instead of a tuple, `insert` making `overwrite` positional
— would break dispatch and is only caught, if at all, by whichever runtime test
happens to exercise that path.

This design adds a **statically-enforced structural contract**: a `Protocol`
that captures the dispatch surface, plus per-module conformance checks that fail
`mypy` when a module drifts out of contract. multiscales is the next convention
likely to revise (its upstream `release-1.0.0` branch adds a required `version`
field), so the contract covers all convention modules now, not just
spatial/proj.

## What the contract guarantees ("structural shape only")

The four operations legitimately _vary_ across conventions and revisions:
`create` takes different named kwargs per convention (spatial: `dimensions`/
`bbox`/…; proj: `code`/`wkt2`/`projjson`), and `validate`/`extract`/`create`
return convention- and revision-specific `TypedDict`s (`SpatialAttrs` r1 vs r2
are distinct types). The contract therefore pins **only the structural shape the
dispatch layer depends on**, not exact per-convention signatures:

- the five module-level constants exist with the right types;
- the four operations exist with compatible **call shapes**;
- return types are pinned to a common supertype (`Mapping[str, Any]`), which
  every `*Attrs` `TypedDict` satisfies — so revision-specific return types still
  conform without the contract over-promising.

It does **not** pin `create`'s named kwargs (each convention differs) and does
**not** force r1 and r2 of a convention to return the same type.

## 1. The protocol

New module `src/zarr_cm/_contract.py` defines:

```python
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from ._core import ConventionMetadataObject


@runtime_checkable
class ConventionModule(Protocol):
    """Structural contract every convention module (and revision submodule) satisfies.

    Pins the dispatch surface used by the package facades and the top-level
    aggregate functions: the identifying constants and the four operations'
    call shapes. Return types are widened to ``Mapping[str, Any]`` so each
    convention's specific ``*Attrs`` TypedDict still conforms.
    """

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
```

Design notes:

- **Module-as-protocol.** mypy treats a _module_ as satisfying a `Protocol`
  structurally: module-level functions match the `def`-style members (the
  protocol's `self` slot maps to the module), and module-level names match the
  attribute members. This is the mechanism that lets `import`ed modules be
  checked against `ConventionModule`.
- **`create(self, **kwargs: Any)`\*\* deliberately does not pin named kwargs —
  conventions differ. It catches "create removed / made positional-only /
  returns the wrong kind of thing".
- **`overwrite: bool = ...`** (the literal ellipsis default) pins `overwrite` as
  a keyword argument with a default without asserting the default's value.
- **Return types `Mapping[str, Any]`.** A `TypedDict` is a `Mapping[str, Any]`,
  so `SpatialAttrs`/`GeoProjAttrs`/`MultiscalesAttrs`/… all conform. This is the
  "structural shape only" decision made concrete.
- **`@runtime_checkable`** enables the runtime presence check in §3. (Note:
  `isinstance` against a runtime-checkable protocol verifies attribute
  _presence_ only, not signatures — signatures are the static layer's job.)

## 2. Static conformance checks

In the same module, one typed assignment per dispatch target, under
`TYPE_CHECKING` so they are checker-only (no runtime import cost, no cycles):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import license as _license
    from . import multiscales as _multiscales
    from . import uom as _uom
    from .proj import _r1 as _proj_r1
    from .proj import _r2 as _proj_r2
    from .spatial import _r1 as _spatial_r1
    from .spatial import _r2 as _spatial_r2

    # Each dispatch target must satisfy ConventionModule. A signature/constant
    # drift in any of these makes the corresponding assignment fail `mypy src/`.
    # Adding a convention or revision means adding one line here.
    _check_spatial_r1: ConventionModule = _spatial_r1
    _check_spatial_r2: ConventionModule = _spatial_r2
    _check_proj_r1: ConventionModule = _proj_r1
    _check_proj_r2: ConventionModule = _proj_r2
    _check_multiscales: ConventionModule = _multiscales
    _check_license: ConventionModule = _license
    _check_uom: ConventionModule = _uom
```

- The flat modules (`multiscales`/`license`/`uom`) already satisfy the contract
  today (verified: all five constants present; `insert`/`extract`/`validate`
  have the exact call shapes; their `create` kwargs differ, which the protocol
  permits). No change to those modules is required.
- When multiscales becomes a `multiscales/` package, its single
  `_check_multiscales` line is replaced by `_check_multiscales_r1` /
  `_check_multiscales_r2` — the same pattern as spatial/proj.

## 3. Enforcement (two layers)

**Layer 1 — static (mypy), the primary guarantee.** `_contract.py` lives in
`src/`, which the existing `src`-scoped mypy pre-commit hook type-checks on
every commit. A drift fails `mypy src/` with an error at the offending
`_check_*` line. Zero new CI wiring. This layer catches signature/type/constant
drift on every known dispatch target.

**Layer 2 — runtime (pytest), the registration guard.** A new
`tests/test_contract.py`:

1. `import zarr_cm._contract` — proves the module imports cleanly at runtime
   (the `TYPE_CHECKING` block is invisible to the interpreter).
2. Enumerates the _actual_ dispatch targets and asserts each satisfies the
   `@runtime_checkable` `ConventionModule`:
   - every module value in `zarr_cm._REGISTRY`;
   - for each revisioned convention (a registry module exposing `_REVISIONS`),
     every revision module in that facade's `_REVISIONS`.

   For each, `assert isinstance(mod, ConventionModule)`.

This layer catches what mypy cannot: a newly-registered convention or revision
that nobody added a static `_check_*` line for — the enumeration reaches it via
the registry/`_REVISIONS` and fails on missing attributes. The two layers are
complementary: Layer 1 verifies _signatures_ on the statically-named modules;
Layer 2 verifies _presence_ across the live dispatch set.

## Implementation risk to de-risk first

Two assumptions in this design rest on mypy/typing behavior that must be
verified by a small spike before building the rest:

1. **A module satisfies a `Protocol` with non-method (attribute) members.** The
   modules declare constants by inference + `Final` (e.g.
   `CONVENTION_KEYS: Final = {"spatial:dimensions", ...}` is inferred
   `set[str]`), not by a bare `: set[str]` annotation. The spike confirms mypy
   accepts these against the protocol's `UUID: str` /
   `CONVENTION_KEYS: set[str]` members (and resolves any invariance issue, e.g.
   widening a protocol member to `Mapping`/`AbstractSet` or `Collection[str]` if
   `set[str]` proves too strict).
2. **A negative check fails as intended.** Temporarily break one `_rN` (e.g.
   rename `CONVENTION_KEYS`) and confirm `mypy src/` errors at the matching
   `_check_*` line, then revert. This proves the guard has teeth before relying
   on it.

The implementation plan's first task is this spike; if mypy rejects the
attribute-member form, fall back to widening the offending protocol members to
the broadest type that still catches real drift (documented in the plan).

## 4. What is intentionally NOT changed

- **Registry value types stay `types.ModuleType`.** Retyping `_REGISTRY` /
  `_REVISIONS` values as `ConventionModule` is rejected: the facades and
  aggregate layer access module attributes outside the protocol
  (`mod.SCHEMA_URL` is on it, but `mod._REVISIONS`, `mod._resolve_read_revision`
  are not), so a protocol-typed registry would force the protocol to grow beyond
  the clean public contract or require casts at every internal access. The
  protocol is a verification artifact, not a structural change to dispatch.
- **No new constraints on `create` kwargs** (per "structural shape only").
- **No changes to the flat modules** — they already conform.

## Out of scope

- Per-convention exact-signature contracts (a distinct protocol per convention
  family pinning `create`'s kwargs and the specific `*Attrs` return type).
- Converting multiscales/license/uom into revision packages (done when they
  actually revise; the contract is ready for it).
- Runtime signature verification (mypy owns signatures; `@runtime_checkable`
  only checks presence).
