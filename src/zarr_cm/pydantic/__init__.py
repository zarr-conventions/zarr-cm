"""Optional pydantic models for zarr-cm conventions.

Requires the ``pydantic`` extra::

    pip install zarr-cm[pydantic]
"""

from __future__ import annotations

try:
    import pydantic  # noqa: F401
except ImportError as e:  # pragma: no cover - exercised via packaging tests
    msg = (
        "zarr_cm.pydantic requires pydantic. "
        "Install with: pip install zarr-cm[pydantic]"
    )
    raise ImportError(msg) from e

from zarr_cm import geo_proj as _geo_proj
from zarr_cm import license as _license
from zarr_cm import multiscales as _multiscales
from zarr_cm import spatial as _spatial
from zarr_cm import uom as _uom
from zarr_cm.pydantic._base import ConventionModel
from zarr_cm.pydantic._multi import build_attrs, parse_attrs
from zarr_cm.pydantic.geo_proj import GeoProjModel
from zarr_cm.pydantic.license import LicenseModel
from zarr_cm.pydantic.multiscales import (
    LayoutObjectModel,
    MultiscalesModel,
    TransformModel,
)
from zarr_cm.pydantic.spatial import SpatialModel
from zarr_cm.pydantic.uom import UCUMModel, UomModel

_MODEL_REGISTRY: dict[str, type[ConventionModel]] = {
    _geo_proj.UUID: GeoProjModel,
    _spatial.UUID: SpatialModel,
    _multiscales.UUID: MultiscalesModel,
    _license.UUID: LicenseModel,
    _uom.UUID: UomModel,
}

_NAME_BY_UUID: dict[str, str] = {
    _geo_proj.UUID: "geo-proj",
    _spatial.UUID: "spatial",
    _multiscales.UUID: "multiscales",
    _license.UUID: "license",
    _uom.UUID: "uom",
}

__all__ = [
    "ConventionModel",
    "GeoProjModel",
    "LayoutObjectModel",
    "LicenseModel",
    "MultiscalesModel",
    "SpatialModel",
    "TransformModel",
    "UCUMModel",
    "UomModel",
    "build_attrs",
    "parse_attrs",
]
