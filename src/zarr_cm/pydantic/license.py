"""Pydantic model for the license convention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

from pydantic import model_validator

from zarr_cm import license as _license_module
from zarr_cm.pydantic._base import ConventionModel, ConventionModuleProtocol

if TYPE_CHECKING:
    from zarr_cm._core import ConventionMetadataObject
    from zarr_cm.license import LicenseAttrs


class LicenseModel(ConventionModel):
    """License metadata for a Zarr node."""

    spdx: str | None = None
    url: str | None = None
    text: str | None = None
    file: str | None = None
    path: str | None = None

    _CMO: ClassVar[ConventionMetadataObject] = _license_module.CMO
    _MODULE: ClassVar[ConventionModuleProtocol[LicenseAttrs]] = _license_module

    @model_validator(mode="after")
    def _validate(self) -> Self:
        # Delegate to the existing module validator for the cross-field rule.
        # The module validates the inner JSON shape (no "license" wrapper).
        _license_module.validate(super().to_attrs())
        return self

    def to_attrs(self) -> dict[str, Any]:
        return {"license": super().to_attrs()}

    def insert(
        self, attrs: dict[str, Any], *, overwrite: bool = False
    ) -> dict[str, Any]:
        # Pass the unwrapped form because _MODULE.insert wraps internally.
        data = cast("LicenseAttrs", super().to_attrs())
        return self._MODULE.insert(attrs, data, overwrite=overwrite)

    @classmethod
    def from_attrs(cls, attrs: dict[str, Any]) -> LicenseModel:
        if "license" in attrs and isinstance(attrs["license"], dict):
            return cls.model_validate(attrs["license"])
        return cls.model_validate(attrs)
