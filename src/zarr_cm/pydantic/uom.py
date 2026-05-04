"""Pydantic models for the uom convention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from pydantic import BaseModel, ConfigDict, field_validator

from zarr_cm import uom
from zarr_cm.pydantic._base import ConventionModel

if TYPE_CHECKING:
    from zarr_cm._core import ConventionMetadataObject


class UCUMModel(BaseModel):
    """Unified Code for Units of Measurement."""

    model_config = ConfigDict(extra="forbid")

    unit: str | None = None
    version: str | None = None


class UomModel(ConventionModel):
    """Unit of measurement metadata for a Zarr array."""

    ucum: UCUMModel
    description: str | None = None

    @field_validator("ucum", mode="before")
    @classmethod
    def _coerce_ucum(cls, value: object) -> object:
        if isinstance(value, str):
            return {"unit": value}
        return value

    _CMO: ClassVar[ConventionMetadataObject] = uom.CMO
    _MODULE: ClassVar[Any] = uom

    def to_attrs(self) -> dict[str, Any]:
        return {"uom": super().to_attrs()}

    def insert(
        self, attrs: dict[str, Any], *, overwrite: bool = False
    ) -> dict[str, Any]:
        # Pass the unwrapped form because _MODULE.insert wraps internally.
        return cast(
            "dict[str, Any]",
            self._MODULE.insert(attrs, super().to_attrs(), overwrite=overwrite),
        )

    @classmethod
    def from_attrs(cls, attrs: dict[str, Any]) -> UomModel:
        if "uom" in attrs and isinstance(attrs["uom"], dict):
            return cls.model_validate(attrs["uom"])
        return cls.model_validate(attrs)
