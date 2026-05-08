"""Base class for convention pydantic models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from typing import Self

    from zarr_cm._core import ConventionMetadataObject

DataT = TypeVar("DataT")


class ConventionModuleProtocol(Protocol[DataT]):
    """The surface of a convention module that ``ConventionModel`` depends on.

    Generic on the concrete convention's TypedDict so each subclass can bind
    to its own data shape (``GeoProjAttrs``, ``MultiscalesAttrs``, etc.).
    """

    UUID: str

    def insert(
        self,
        attrs: dict[str, Any],
        data: DataT,
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]: ...

    def extract(self, attrs: dict[str, Any]) -> tuple[dict[str, Any], DataT]: ...


class ConventionModel(BaseModel):
    """Base for all convention models.

    Subclasses MUST set the class variables ``_CMO`` and ``_MODULE`` to
    point at the matching convention's CMO and module. The base class
    uses ``_MODULE`` to delegate ``insert`` / ``extract`` to the existing
    JSON-dict API, keeping the JSON shape canonical.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    _CMO: ClassVar[ConventionMetadataObject]
    _MODULE: ClassVar[ConventionModuleProtocol[Any]]

    def to_attrs(self) -> dict[str, Any]:
        """Dump to the JSON-shaped dict (the TypedDict form)."""
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_attrs(cls, attrs: dict[str, Any]) -> Self:
        """Construct from a JSON-shaped dict."""
        return cls.model_validate(attrs)

    def insert(
        self, attrs: dict[str, Any], *, overwrite: bool = False
    ) -> dict[str, Any]:
        """Insert this convention into a Zarr attributes dict."""
        return self._MODULE.insert(attrs, self.to_attrs(), overwrite=overwrite)

    @classmethod
    def extract(cls, attrs: dict[str, Any]) -> tuple[dict[str, Any], Self | None]:
        """Extract this convention from a Zarr attributes dict, if present.

        Detection is by ``uuid`` in the ``zarr_conventions`` array of the
        input *attrs*. Returns ``(remaining, None)`` when this convention's
        CMO is not present, otherwise ``(remaining, model)``.
        """
        present = any(
            cmo.get("uuid") == cls._MODULE.UUID
            for cmo in attrs.get("zarr_conventions", [])
        )
        remaining, data = cls._MODULE.extract(attrs)
        if not present:
            return remaining, None
        return remaining, cls.from_attrs(dict(data))
