"""Pydantic model for the geo-proj convention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self

from pydantic import Field, model_validator

from zarr_cm import geo_proj
from zarr_cm.pydantic._base import ConventionModel

if TYPE_CHECKING:
    from zarr_cm._core import ConventionMetadataObject


class GeoProjModel(ConventionModel):
    """CRS information for geospatial data."""

    code: str | None = Field(default=None, alias="proj:code")
    wkt2: str | None = Field(default=None, alias="proj:wkt2")
    projjson: dict[str, Any] | None = Field(default=None, alias="proj:projjson")

    _CMO: ClassVar[ConventionMetadataObject] = geo_proj.CMO
    _MODULE: ClassVar[Any] = geo_proj

    @model_validator(mode="after")
    def _validate(self) -> Self:
        geo_proj.validate(self.to_attrs())
        return self
