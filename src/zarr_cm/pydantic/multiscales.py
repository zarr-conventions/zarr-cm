"""Pydantic models for the multiscales convention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zarr_cm import multiscales
from zarr_cm.pydantic._base import ConventionModel, ConventionModuleProtocol

if TYPE_CHECKING:
    from zarr_cm._core import ConventionMetadataObject
    from zarr_cm.multiscales import MultiscalesAttrs


class TransformModel(BaseModel):
    """Coordinate transformation with scale and translation."""

    model_config = ConfigDict(extra="forbid")

    scale: list[float] | None = None
    translation: list[float] | None = None


class LayoutObjectModel(BaseModel):
    """A single resolution level in a multiscale pyramid."""

    model_config = ConfigDict(extra="forbid")

    asset: str
    derived_from: str | None = None
    transform: TransformModel | None = None
    resampling_method: str | None = None

    @model_validator(mode="after")
    def _derived_requires_transform(self) -> Self:
        if self.derived_from is not None and self.transform is None:
            msg = "layout entry with 'derived_from' is missing 'transform'"
            raise ValueError(msg)
        return self


class MultiscalesModel(ConventionModel):
    """Multiscale pyramid layout and metadata."""

    layout: list[LayoutObjectModel] = Field(min_length=1)
    resampling_method: str | None = None

    _CMO: ClassVar[ConventionMetadataObject] = multiscales.CMO
    _MODULE: ClassVar[ConventionModuleProtocol[MultiscalesAttrs]] = multiscales

    def to_attrs(self) -> dict[str, Any]:
        return {"multiscales": super().to_attrs()}

    def insert(
        self, attrs: dict[str, Any], *, overwrite: bool = False
    ) -> dict[str, Any]:
        # Pass the unwrapped form because _MODULE.insert wraps internally.
        data = cast("MultiscalesAttrs", super().to_attrs())
        return self._MODULE.insert(attrs, data, overwrite=overwrite)

    @classmethod
    def from_attrs(cls, attrs: dict[str, Any]) -> MultiscalesModel:
        if "multiscales" in attrs and isinstance(attrs["multiscales"], dict):
            return cls.model_validate(attrs["multiscales"])
        return cls.model_validate(attrs)
