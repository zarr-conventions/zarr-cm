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

- **`create`** creates convention metadata.
- **`validate`** checks convention metadata for validity.
- **`insert`** adds convention metadata to a Zarr attributes dict and returns a
  new dict with a `zarr_conventions` entry.
- **`extract`** removes convention metadata from an attributes dict and returns
  the remaining attributes and the extracted convention data.
- **`validate_group_metadata`**, **`validate_array_metadata`** and
  **`validate_node_metadata`** validate a whole `zarr.json` document. See
  [Validating whole metadata documents](#validating-whole-metadata-documents).

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import geo_proj

# Create
data = geo_proj.create(code="EPSG:4326")
print(data)
#> {'proj:code': 'EPSG:4326'}

# Validate
print(geo_proj.validate({"proj:code": "EPSG:4326"}))
#> {'proj:code': 'EPSG:4326'}

# Insert
attrs = {"foo": "bar"}
result = geo_proj.insert(attrs, data)
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
remaining, extracted = geo_proj.extract(result)
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
provides all three, and the package-level versions fan out over every convention
the document declares.

The single-convention validators also **narrow the document's type**. Every
metadata document is a `GroupMetadata[AttrsT]` or `ArrayMetadata[AttrsT]` — a
generic TypedDict whose type parameter states what is known about `attributes`.
Bare `GroupMetadata` is the wide form (an arbitrary JSON object), and validating
against a convention narrows it to that convention's attrs type, so a signature
can require a validated document and the validated document keeps its field
types:

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import GroupMetadata, SpatialConventionAttrs, spatial

def write_group(node: GroupMetadata[SpatialConventionAttrs]) -> str:
    # attributes are typed as spatial's TypedDict, not an untyped JSON object
    return f"writing, bbox={node['attributes'].get('spatial:bbox')}"

attrs = spatial.insert({}, spatial.create(bbox=[0.0, 0.0, 1.0, 1.0]))
group: GroupMetadata = {"zarr_format": 3, "node_type": "group", "attributes": attrs}

print(write_group(spatial.validate_group_metadata(group)))
#> writing, bbox=[0.0, 0.0, 1.0, 1.0]
```

<!-- blacken-docs:on -->

Handing `write_group` the wide `group` without validating is a type error. The
narrowed document is the same object, returned unchanged — the narrowing is a
type-level claim about the moment of validation, and the mapping underneath
stays mutable, so it records that validation _happened_, not that the contents
are still valid.

Two boundaries are deliberate. The `attributes` parameter is covariant, so a
narrowed document still flows anywhere the wide form is accepted — validators
chain — but narrowing does not _accumulate_: there is no intersection type, so
validating against spatial and then proj yields proj's type alone. And the
package-level validators fan out over whichever conventions the document
declares — a runtime-determined set — so they cannot narrow at all; they return
their input at the type it came in with.

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
import zarr_cm
from zarr_cm import spatial

attributes = spatial.insert({}, spatial.create(bbox=[-180.0, -90.0, 180.0, 90.0]))

# A group may carry a footprint with no dimensions.
group = {"zarr_format": 3, "node_type": "group", "attributes": attributes}
print(zarr_cm.validate_node_metadata(group)["node_type"])
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
several conventions at once, keyed by convention name. `extract_all` and
`validate_all` are shortcuts that operate on all known conventions.

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import create_many, extract_all

# Create attributes with multiple conventions at once
attrs = create_many(
    {
        "geo-proj": {"proj:code": "EPSG:4326"},
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
#> ['geo-proj', 'license', 'spatial']
print(extracted["geo-proj"])
#> {'proj:code': 'EPSG:4326'}
```

<!-- blacken-docs:on -->
