# zarr-cm

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]

[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]

[![Coverage][coverage-badge]][coverage-link]

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/zarr-conventions/zarr-cm/workflows/CI/badge.svg
[actions-link]:             https://github.com/zarr-conventions/zarr-cm/actions
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/zarr-cm
[conda-link]:               https://github.com/conda-forge/zarr-cm-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/zarr-conventions/zarr-cm/discussions
[pypi-link]:                https://pypi.org/project/zarr-cm/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/zarr-cm
[pypi-version]:             https://img.shields.io/pypi/v/zarr-cm
[rtd-badge]:                https://readthedocs.org/projects/zarr-cm/badge/?version=latest
[rtd-link]:                 https://zarr-cm.readthedocs.io/en/latest/?badge=latest
[coverage-badge]:           https://codecov.io/github/zarr-conventions/zarr-cm/branch/main/graph/badge.svg
[coverage-link]:            https://codecov.io/github/zarr-conventions/zarr-cm

<!-- prettier-ignore-end -->

Python types and utilities for
[Zarr Conventions Metadata](https://github.com/zarr-conventions/).

## Overview

`zarr-cm` provides typed Python support for the published Zarr conventions:

| Convention                                                     | Module                | Description                             |
| -------------------------------------------------------------- | --------------------- | --------------------------------------- |
| [geo-proj](https://github.com/zarr-experimental/geo-proj)      | `zarr_cm.geo_proj`    | Coordinate reference system information |
| [spatial](https://github.com/zarr-conventions/spatial)         | `zarr_cm.spatial`     | Spatial coordinate metadata             |
| [multiscales](https://github.com/zarr-conventions/multiscales) | `zarr_cm.multiscales` | Multiscale pyramid layout               |
| [license](https://github.com/clbarnes/zarr-convention-license) | `zarr_cm.license`     | License specifiers                      |
| [uom](https://github.com/clbarnes/zarr-convention-uom)         | `zarr_cm.uom`         | Units of measurement                    |

Each module provides:

- **TypedDict types** for convention-specific metadata
- **`insert`** — add convention metadata to a Zarr attributes dict
- **`extract`** — remove and return convention metadata from an attributes dict
- **`validate`** — check runtime invariants the type system cannot express

## Installation

```bash
pip install zarr-cm
```

## Usage

<!-- blacken-docs:off -->
<!-- prettier-ignore -->
```python
from zarr_cm import geo_proj

# Create convention metadata
data = geo_proj.create(code="EPSG:4326")
print(data)
#> {'proj:code': 'EPSG:4326'}

# Validate
print(geo_proj.validate({"proj:code": "EPSG:4326"}))
#> {'proj:code': 'EPSG:4326'}

# Insert into an attributes dict
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

# Extract it back out
remaining, extracted = geo_proj.extract(result)
print(remaining)
#> {'foo': 'bar'}
print(extracted)
#> {'proj:code': 'EPSG:4326'}
```

<!-- blacken-docs:on -->
