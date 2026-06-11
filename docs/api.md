# API Reference

## Multi-convention

<!-- prettier-ignore -->
::: zarr_cm
    options:
      members:
        - CONVENTION_NAMES
        - ALL_CONVENTION_KEYS
        - MultiConventionAttrs
        - GEO_PROJ
        - SPATIAL
        - MULTISCALES
        - LICENSE
        - UOM
        - create_many
        - validate_many
        - validate_all
        - insert_many
        - extract_many
        - extract_all

## Core

<!-- prettier-ignore -->
::: zarr_cm._core

## geo-proj

::: zarr_cm.geo_proj

## spatial

::: zarr_cm.spatial

## multiscales

::: zarr_cm.multiscales

## license

::: zarr_cm.license

## uom

::: zarr_cm.uom

## Optional: pydantic models

The `zarr_cm.pydantic` subpackage requires the `pydantic` extra
(`pip install zarr-cm[pydantic]`).

<!-- prettier-ignore -->
::: zarr_cm.pydantic
    options:
      members:
        - ConventionModel
        - GeoProjModel
        - SpatialModel
        - MultiscalesModel
        - LayoutObjectModel
        - TransformModel
        - LicenseModel
        - UomModel
        - UCUMModel
        - build_attrs
        - parse_attrs
