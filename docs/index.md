# zarr-cm

Python types and utilities for
[Zarr Conventions Metadata](https://github.com/zarr-conventions/).

## Installation

```bash
pip install zarr-cm
```

## Supported conventions

| Convention                                                     | Module                                   | Description                             |
| -------------------------------------------------------------- | ---------------------------------------- | --------------------------------------- |
| [proj](https://github.com/zarr-conventions/proj)               | `zarr_cm.proj` (also `zarr_cm.geo_proj`) | Coordinate reference system information |
| [spatial](https://github.com/zarr-conventions/spatial)         | `zarr_cm.spatial`                        | Spatial coordinate metadata             |
| [multiscales](https://github.com/zarr-conventions/multiscales) | `zarr_cm.multiscales`                    | Multiscale pyramid layout               |
| [license](https://github.com/clbarnes/zarr-convention-license) | `zarr_cm.license`                        | License specifiers                      |
| [uom](https://github.com/clbarnes/zarr-convention-uom)         | `zarr_cm.uom`                            | Units of measurement                    |

## Usage

Each convention module provides the following operations:

- **`create`** creates convention metadata: the convention's own keys, nothing
  else.
- **`create_convention_attrs`** creates a complete stand-alone attributes dict:
  that same convention data plus the `zarr_conventions` entry declaring it.
- **`validate`** checks convention metadata for validity.
- **`insert`** composes: it adds convention metadata to an attributes dict that
  already exists, returning a new dict with the `zarr_conventions` entry
  appended. Reach for `create_convention_attrs` when there is nothing to compose
  with.
- **`extract`** removes convention metadata from an attributes dict and returns
  the remaining attributes and the extracted convention data.
- **`validate_group_metadata`**, **`validate_array_metadata`** and
  **`validate_node_metadata`** validate a whole `zarr.json` document. See
  [Validating whole metadata documents](#validating-whole-metadata-documents).

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import proj

# Create
data = proj.create(code="EPSG:4326")
print(data)
#> {'proj:code': 'EPSG:4326'}

# Validate
print(proj.validate({"proj:code": "EPSG:4326"}))
#> {'proj:code': 'EPSG:4326'}

# Insert
attrs = {"foo": "bar"}
result = proj.insert(attrs, data)
print(result)
"""
{
    'foo': 'bar',
    'proj:code': 'EPSG:4326',
    'zarr_conventions': [
        {
            'uuid': 'f17cb550-5864-4468-aeb7-f3180cfb622f',
            'schema_url': 'https://raw.githubusercontent.com/zarr-conventions/proj/5ca5b2f92e5c7245f957d9128b289ee535f0720d/schema.json',
            'spec_url': 'https://github.com/zarr-conventions/proj/blob/5ca5b2f92e5c7245f957d9128b289ee535f0720d/README.md',
            'name': 'proj:',
            'description': 'Coordinate reference system information for geospatial data',
        }
    ],
}
"""

# Extract
remaining, extracted = proj.extract(result)
print(remaining)
#> {'foo': 'bar'}
print(extracted)
#> {'proj:code': 'EPSG:4326'}
```

<!-- blacken-docs:on -->

### Convention revisions

Conventions evolve. `create`/`insert` default to the latest revision;
`validate`/`extract` auto-detect the revision from existing metadata. Pass
`revision=` to target a specific revision:

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import spatial

# Writes use the latest revision by default (spatial r3 is strictly 2D)
latest = spatial.create(dimensions=["y", "x"])
print(latest)
#> {'spatial:dimensions': ['y', 'x']}

# Opt into an older revision explicitly to model older data
old = spatial.create(dimensions=["y", "x"], revision="r2")
print(old)
#> {'spatial:dimensions': ['y', 'x']}
```

<!-- blacken-docs:on -->

### Group-level spatial metadata

The `spatial:` spec requires `spatial:dimensions` only on arrays, so a group may
carry other `spatial:` keys on their own — for example a union footprint over
child arrays that do not share a single grid:

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import spatial

footprint = spatial.create(bbox=[-180.0, -90.0, 180.0, 90.0])
print(footprint)
#> {'spatial:bbox': [-180.0, -90.0, 180.0, 90.0]}

# As a complete attributes dict, declaring the convention it uses:
attributes = spatial.create_convention_attrs(bbox=[-180.0, -90.0, 180.0, 90.0])
print(sorted(attributes))
#> ['spatial:bbox', 'zarr_conventions']
```

<!-- blacken-docs:on -->

## Validating whole metadata documents

`validate` sees only an attributes dict, so it cannot check the rules that
depend on which kind of node the attributes belong to. The node-level entry
points take a whole `zarr.json` document and can: `spatial` requires
`spatial:dimensions` on arrays but not on groups, and `multiscales` applies to
groups only.

`validate_node_metadata` dispatches on the document's `node_type` to
`validate_array_metadata` or `validate_group_metadata`. Every convention module
provides all three.

The validators also **narrow the document's type**. A convention-bearing
document is represented as `Metadata[AttrsT]`, a generic union of array and
group TypedDicts whose type parameter states what is known about `attributes`.
`Metadata[Mapping[str, JSONValue]]` is the wide form, and validating against a
convention narrows it to that convention's attrs type. The node discriminator
and base array fields remain typed too, so a signature can require a validated
document:

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from collections.abc import Mapping

from zarr_cm import JSONValue, GroupMetadata, SpatialConventionAttrs, spatial

def write_group(node: GroupMetadata[SpatialConventionAttrs]) -> str:
    # attributes are typed as spatial's TypedDict, not an untyped JSON object
    return f"writing, bbox={node['attributes'].get('spatial:bbox')}"

attributes = spatial.create_convention_attrs(bbox=[0.0, 0.0, 1.0, 1.0])
group: GroupMetadata[Mapping[str, JSONValue]] = {
    "zarr_format": 3,
    "node_type": "group",
    "attributes": attributes,
}

print(write_group(spatial.validate_group_metadata(group)))
#> writing, bbox=[0.0, 0.0, 1.0, 1.0]
```

<!-- blacken-docs:on -->

Handing `write_group` the wide `group` without validating is a type error.
Validation returns a new document with its `attributes` tree normalized to
ordinary JSON containers. The input mapping is not mutated. The returned mapping
is still mutable, so the narrowed type records that validation _happened_, not
that later mutations remain valid.

Two boundaries are deliberate. The `attributes` parameter is covariant, so a
narrowed document still flows anywhere the wide form is accepted and validators
chain. Narrowing does not _accumulate_: there is no intersection type, so
validating against spatial and then proj yields proj's type alone.

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import spatial

attributes = spatial.create_convention_attrs(bbox=[-180.0, -90.0, 180.0, 90.0])

# A group may carry a footprint with no dimensions.
group = {"zarr_format": 3, "node_type": "group", "attributes": attributes}
print(spatial.validate_node_metadata(group)["node_type"])
#> group

# The same attributes on an array are not valid.
array = {**group, "node_type": "array"}
try:
    spatial.validate_array_metadata(array)
except ValueError as exc:
    print(exc)
    #> 'spatial:dimensions' is required on array nodes
```

<!-- blacken-docs:on -->

## Multiple conventions

`create_many`, `insert_many`, `extract_many`, and `validate_many` work with
several conventions at once, keyed by convention name (`"proj"`, `"spatial"`,
`"multiscales"`, `"license"`, `"uom"`; the pre-rename spelling `"geo-proj"` is
still accepted as an alias for `"proj"`). `extract_all` and `validate_all` are
shortcuts that operate on all known conventions.

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import create_many, extract_all

# Create attributes with multiple conventions at once
attrs = create_many(
    {
        "proj": {"proj:code": "EPSG:4326"},
        "spatial": {"spatial:dimensions": ["y", "x"]},
        "license": {"spdx": "MIT"},
    }
)
print(sorted(attrs.keys()))
#> ['license', 'proj:code', 'spatial:dimensions', 'zarr_conventions']

# Extract all known conventions
remaining, extracted = extract_all(attrs)
print(remaining)
#> {}
print(sorted(extracted.keys()))
#> ['license', 'proj', 'spatial']
print(extracted["proj"])
#> {'proj:code': 'EPSG:4326'}
```

<!-- blacken-docs:on -->

### Composing GeoZarr metadata

A typical geospatial group carries `proj:`, `spatial:` and `multiscales`
together. Build each with its module's `create` (so it is validated), then
combine them with `create_many`. The `zarr_conventions` array lists exactly the
conventions present, in the order given:

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import create_many, multiscales, proj, spatial

attrs = create_many(
    {
        "proj": proj.create(code="EPSG:27704"),
        "spatial": spatial.create(
            dimensions=["y", "x"],
            transform=[10.0, 0.0, 5400000.0, 0.0, -10.0, 2700000.0],
            transform_type="affine",
            shape=[10000, 10000],
        ),
        "multiscales": multiscales.create(
            layout=[
                {"asset": "0"},
                {"asset": "1", "derived_from": "0", "transform": {"scale": [2.0, 2.0]}},
            ]
        ),
    }
)
print([cmo["name"] for cmo in attrs["zarr_conventions"]])
#> ['proj:', 'spatial:', 'multiscales']
```

<!-- blacken-docs:on -->

The result is a plain dict, ready for `group.attrs.update(attrs)` or
`xarray.Dataset.attrs.update(attrs)`.

### Registry helpers

`latest_revisions` reports which revision each revisioned convention writes by
default; `convention_metadata` returns the `zarr_conventions` entry for a
convention (optionally at a specific revision) as a fresh copy. Downstream
packages that need to know what an installed `zarr-cm` will write can pin
against these instead of reaching into the convention modules:

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import convention_metadata, latest_revisions

print(latest_revisions())
#> {'proj': 'r3', 'spatial': 'r3', 'multiscales': 'r2'}

cmo = convention_metadata("proj")
print(cmo["name"], cmo["uuid"])
#> proj: f17cb550-5864-4468-aeb7-f3180cfb622f

# Registry entries are keyed on schema_url, which pins the revision
print(convention_metadata("proj", revision="r2")["schema_url"] == cmo["schema_url"])
#> False
```

<!-- blacken-docs:on -->
