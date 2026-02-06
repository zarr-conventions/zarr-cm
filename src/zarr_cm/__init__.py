"""
Copyright (c) 2026 Davis Bennett. All rights reserved.

zarr-cm: Python implementation of Zarr Conventions Metadata
"""

from __future__ import annotations

from ._core import (
    ConventionAttrs,
    ConventionMetadataObject,
    validate_convention_metadata_object,
)
from ._version import version as __version__
from .geo_proj import GeoProjAttrs, GeoProjConventionAttrs
from .license import LicenseAttrs, LicenseConventionAttrs
from .multiscales import (
    LayoutObject,
    MultiscalesAttrs,
    MultiscalesConventionAttrs,
    Transform,
)
from .spatial import SpatialAttrs, SpatialConventionAttrs
from .uom import UCUM, UomAttrs, UomConventionAttrs

__all__ = [
    "UCUM",
    "ConventionAttrs",
    "ConventionMetadataObject",
    "GeoProjAttrs",
    "GeoProjConventionAttrs",
    "LayoutObject",
    "LicenseAttrs",
    "LicenseConventionAttrs",
    "MultiscalesAttrs",
    "MultiscalesConventionAttrs",
    "SpatialAttrs",
    "SpatialConventionAttrs",
    "Transform",
    "UomAttrs",
    "UomConventionAttrs",
    "__version__",
    "validate_convention_metadata_object",
]
