"""Sources of valid convention metadata, one per revision of each convention.

Each `Revision` bundles a revision module with a Hypothesis strategy for the
keyword arguments its `create()` accepts, so a property test can say "for any
valid data of any revision, invariant X holds" and have that mean something.
The strategies are written against the upstream JSON schemas vendored under
`tests/schemas/`, and `test_properties.py` checks the generated data against
those schemas -- so a generator that drifted from the spec would fail there,
not silently narrow the tests.

Values are kept JSON-native (lists, not tuples; finite floats) so that the
same data can round-trip through `json.dumps`/`json.loads` unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from hypothesis import strategies as st

import zarr_cm
from zarr_cm import license as license_
from zarr_cm import multiscales, proj, spatial, stac, uom

if TYPE_CHECKING:
    from types import ModuleType
    from uuid import UUID

SCHEMAS = Path(__file__).parent / "schemas"

Kwargs = dict[str, Any]

# --- primitive helpers -------------------------------------------------------

text = st.text(min_size=1, max_size=20)
finite_floats = st.floats(allow_nan=False, allow_infinity=False, width=32)
numbers: st.SearchStrategy[float] = st.one_of(finite_floats, st.integers(-1000, 1000))

json_values: st.SearchStrategy[Any] = st.recursive(
    st.none() | st.booleans() | st.integers() | finite_floats | st.text(max_size=10),
    lambda inner: st.lists(inner, max_size=3)
    | st.dictionaries(st.text(max_size=8), inner, max_size=3),
    max_leaves=6,
)


def optional(strategy: st.SearchStrategy[Any]) -> st.SearchStrategy[Any]:
    """`None` (meaning: leave the keyword out) or a drawn value."""
    return st.none() | strategy


def drop_none(kwargs: Kwargs) -> Kwargs:
    return {k: v for k, v in kwargs.items() if v is not None}


# --- proj --------------------------------------------------------------------

_PROJJSON = st.dictionaries(text, st.text(max_size=10) | st.integers(), max_size=3)


def _proj_kwargs(
    code: st.SearchStrategy[str], *, exactly_one: bool
) -> st.SearchStrategy[Kwargs]:
    """Choose which of code / wkt2 / projjson to set; r2 wants exactly one."""
    fields = ("code", "wkt2", "projjson")
    values = {"code": code, "wkt2": text, "projjson": _PROJJSON}
    if exactly_one:
        chosen = st.sampled_from(fields).map(lambda f: (f,))
    else:
        chosen = st.sets(st.sampled_from(fields), min_size=1).map(tuple)
    return chosen.flatmap(
        lambda names: st.fixed_dictionaries({name: values[name] for name in names})
    )


PROJ_R2_KWARGS = _proj_kwargs(
    st.from_regex(r"[A-Z]+:[0-9]+", fullmatch=True), exactly_one=True
)
PROJ_R3_KWARGS = _proj_kwargs(
    st.from_regex(r"[^:\n]+:[^:\n]+", fullmatch=True), exactly_one=False
)

# --- spatial -----------------------------------------------------------------

SPATIAL_KWARGS: st.SearchStrategy[Kwargs] = st.fixed_dictionaries(
    {
        "dimensions": optional(st.lists(text, min_size=2, max_size=2)),
        "bbox": optional(st.lists(numbers, min_size=4, max_size=4)),
        "transform_type": optional(text),
        "transform": optional(st.lists(numbers, min_size=6, max_size=6)),
        "shape": optional(st.lists(st.integers(1, 10_000), min_size=2, max_size=2)),
        "registration": optional(st.sampled_from(["node", "pixel"])),
    }
).map(drop_none)

# --- multiscales -------------------------------------------------------------

_PATH_SEGMENT = st.from_regex(r"[A-Za-z0-9_-]+", fullmatch=True)
_PATH = st.lists(_PATH_SEGMENT, min_size=1, max_size=3).map("/".join)
_TRANSFORM = st.fixed_dictionaries(
    {},
    optional={
        "scale": st.lists(numbers, min_size=1, max_size=3),
        "translation": st.lists(numbers, min_size=1, max_size=3),
    },
)


@st.composite
def _layout_object(draw: st.DrawFn) -> dict[str, Any]:
    entry: dict[str, Any] = {"asset": draw(_PATH)}
    if draw(st.booleans()):
        entry["derived_from"] = draw(_PATH)
        entry["transform"] = draw(_TRANSFORM)  # required alongside derived_from
    elif draw(st.booleans()):
        entry["transform"] = draw(_TRANSFORM)
    if draw(st.booleans()):
        entry["resampling_method"] = draw(text)
    return entry


MULTISCALES_KWARGS: st.SearchStrategy[Kwargs] = st.fixed_dictionaries(
    {
        "layout": st.lists(_layout_object(), min_size=1, max_size=4),
        "resampling_method": optional(text),
    }
).map(drop_none)

# --- license / uom -----------------------------------------------------------

LICENSE_KWARGS: st.SearchStrategy[Kwargs] = st.sets(
    st.sampled_from(["spdx", "url", "text", "file", "path"]), min_size=1
).flatmap(lambda names: st.fixed_dictionaries(dict.fromkeys(names, text)))

UOM_KWARGS: st.SearchStrategy[Kwargs] = st.fixed_dictionaries(
    {
        "ucum": st.fixed_dictionaries({}, optional={"unit": text, "version": text}),
        "description": optional(text),
    }
).map(drop_none)

# --- stac ----------------------------------------------------------------

# stac:item / stac:collection may be any JSON object: test_properties.py stubs
# their upstream $ref targets (schemas.stacspec.org) to accept anything.
_STAC_OBJECT = st.dictionaries(text, json_values, max_size=3)
_STAC_LINK = st.fixed_dictionaries({"href": text}, optional={"rel": text, "type": text})

STAC_KWARGS: st.SearchStrategy[Kwargs] = st.sampled_from(
    ["item", "collection", "key", "link"]
).flatmap(
    lambda field: st.fixed_dictionaries(
        {
            field: {
                "item": _STAC_OBJECT,
                "collection": _STAC_OBJECT,
                "key": text,
                "link": _STAC_LINK,
            }[field]
        }
    )
)


# --- the registry ------------------------------------------------------------


class Revision(NamedTuple):
    """One revision of one convention, with a source of valid `create()` input."""

    convention: zarr_cm.CanonicalConventionName
    label: str | None
    """Revision label, or `None` for conventions that have no revisions."""
    module: ModuleType
    """The revision module: `proj.r2`, `spatial.r3`, `license`, ..."""
    package: ModuleType
    """The dispatching package: `proj`, `spatial`, `license`, ..."""
    schema: dict[str, Any]
    """The upstream JSON schema this revision snapshots."""
    node_type: str
    """A node type the convention's data is valid on without extra keys."""
    kwargs: st.SearchStrategy[Kwargs]
    """Keyword arguments for `module.create()` that always yield valid data."""

    def __repr__(self) -> str:  # keeps Hypothesis' failure output readable
        return f"Revision({self.convention}, {self.label})"


def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / name).read_text())


REVISIONS: tuple[Revision, ...] = (
    Revision(
        "proj", "r2", proj.r2, proj, _schema("proj-r2.json"), "group", PROJ_R2_KWARGS
    ),
    Revision(
        "proj", "r3", proj.r3, proj, _schema("proj-r3.json"), "group", PROJ_R3_KWARGS
    ),
    # spatial: arrays additionally require spatial:dimensions, so groups are the
    # node type on which *any* generated data is valid.
    Revision(
        "spatial",
        "r2",
        spatial.r2,
        spatial,
        _schema("spatial-r2.json"),
        "group",
        SPATIAL_KWARGS,
    ),
    Revision(
        "spatial",
        "r3",
        spatial.r3,
        spatial,
        _schema("spatial-r3.json"),
        "group",
        SPATIAL_KWARGS,
    ),
    # multiscales is group-only; uom's schema is array-only.
    Revision(
        "multiscales",
        "r2",
        multiscales.r2,
        multiscales,
        _schema("multiscales-r2.json"),
        "group",
        MULTISCALES_KWARGS,
    ),
    Revision(
        "license",
        None,
        license_,
        license_,
        _schema("license.json"),
        "group",
        LICENSE_KWARGS,
    ),
    Revision("uom", None, uom, uom, _schema("uom.json"), "array", UOM_KWARGS),
    Revision("stac", None, stac, stac, _schema("stac.json"), "group", STAC_KWARGS),
)

REVISIONED: tuple[Revision, ...] = tuple(r for r in REVISIONS if r.label is not None)

BY_CONVENTION: dict[str, tuple[Revision, ...]] = {
    name: tuple(r for r in REVISIONS if r.convention == name)
    for name in zarr_cm.CONVENTION_NAMES
}

revisions = st.sampled_from(REVISIONS)
"""Any revision of any convention."""


@st.composite
def revision_pairs(draw: st.DrawFn) -> tuple[Revision, Revision]:
    """Two *different* revisions of the same convention."""
    name = draw(st.sampled_from([n for n, rs in BY_CONVENTION.items() if len(rs) > 1]))
    first, second = draw(st.permutations(BY_CONVENTION[name]))[:2]
    return first, second


@st.composite
def revision_selections(
    draw: st.DrawFn,
) -> dict[zarr_cm.CanonicalConventionName, Revision]:
    """A non-empty choice of conventions, one revision each: a `create_many` input."""
    names = draw(st.sets(st.sampled_from(sorted(zarr_cm.CONVENTION_NAMES)), min_size=1))
    return {name: draw(st.sampled_from(BY_CONVENTION[name])) for name in sorted(names)}


# --- things that are *not* ours -----------------------------------------------

_reserved = zarr_cm.ALL_CONVENTION_KEYS | {"zarr_conventions"}

foreign_attrs: st.SearchStrategy[dict[str, Any]] = st.dictionaries(
    st.text(min_size=1, max_size=10).filter(lambda k: k not in _reserved),
    json_values,
    max_size=4,
)
"""Attributes belonging to nobody: keys no convention claims, arbitrary values."""

_known_uuids = {r.module.UUID for r in REVISIONS}


def _foreign_declaration(u: UUID, name: str) -> dict[str, str]:
    return {"uuid": str(u), "name": name}


foreign_declarations: st.SearchStrategy[list[dict[str, str]]] = st.lists(
    st.builds(
        _foreign_declaration,
        st.uuids().filter(lambda u: str(u) not in _known_uuids),
        text,
    ),
    max_size=3,
)
"""`zarr_conventions` entries for conventions this package does not know."""
