# zarr-cm

Python types and utilities for
[Zarr Conventions Metadata](https://github.com/zarr-conventions/).

## Installation

```bash
pip install zarr-cm
```

## Supported conventions

| Convention                                                     | Module                | Description                             |
| -------------------------------------------------------------- | --------------------- | --------------------------------------- |
| [geo-proj](https://github.com/zarr-experimental/geo-proj)      | `zarr_cm.geo_proj`    | Coordinate reference system information |
| [spatial](https://github.com/zarr-conventions/spatial)         | `zarr_cm.spatial`     | Spatial coordinate metadata             |
| [multiscales](https://github.com/zarr-conventions/multiscales) | `zarr_cm.multiscales` | Multiscale pyramid layout               |
| [license](https://github.com/clbarnes/zarr-convention-license) | `zarr_cm.license`     | License specifiers                      |
| [uom](https://github.com/clbarnes/zarr-convention-uom)         | `zarr_cm.uom`         | Units of measurement                    |

## Usage

Each convention module provides the following operations:

- **`create`** creates convention metadata.
- **`validate`** checks convention metadata for validity.
- **`insert`** adds convention metadata to a Zarr attributes dict and returns a
  new dict with a `zarr_conventions` entry.
- **`extract`** removes convention metadata from an attributes dict and returns
  the remaining attributes and the extracted convention data.

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
            'schema_url': 'https://raw.githubusercontent.com/zarr-experimental/geo-proj/refs/tags/v1/schema.json',
            'spec_url': 'https://github.com/zarr-experimental/geo-proj/blob/v1/README.md',
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
