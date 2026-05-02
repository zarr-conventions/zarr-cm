"""Pydantic model for the spatial convention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self

from pydantic import Field, model_validator

from zarr_cm import spatial
from zarr_cm.pydantic._base import ConventionModel

if TYPE_CHECKING:
    from zarr_cm._core import ConventionMetadataObject


class SpatialModel(ConventionModel):
    """Spatial coordinate metadata."""

    dimensions: list[str] = Field(alias="spatial:dimensions")
    bbox: list[float] | None = Field(default=None, alias="spatial:bbox")
    transform_type: str | None = Field(default=None, alias="spatial:transform_type")
    transform: list[float] | None = Field(default=None, alias="spatial:transform")
    shape: list[int] | None = Field(default=None, alias="spatial:shape")
    registration: Literal["node", "pixel"] | None = Field(
        default=None, alias="spatial:registration"
    )

    _CMO: ClassVar[ConventionMetadataObject] = spatial.CMO
    _MODULE: ClassVar[Any] = spatial

    @model_validator(mode="after")
    def _validate(self) -> Self:
        spatial.validate(self.to_attrs())
        return self
