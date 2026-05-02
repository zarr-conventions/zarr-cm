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

from zarr_cm.pydantic._base import ConventionModel
from zarr_cm.pydantic.geo_proj import GeoProjModel
from zarr_cm.pydantic.license import LicenseModel
from zarr_cm.pydantic.spatial import SpatialModel

__all__ = [
    "ConventionModel",
    "GeoProjModel",
    "LicenseModel",
    "SpatialModel",
]
