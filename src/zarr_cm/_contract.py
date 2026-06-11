"""Structural contract for convention modules dispatched by the registry.

Defines :class:`ConventionModule` and statically asserts that every convention
module (and revision submodule) satisfies it. A signature or constant drift in
any dispatch target fails ``mypy src/`` at the corresponding ``_check_*`` line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from ._core import ConventionMetadataObject


@runtime_checkable
class ConventionModule(Protocol):
    """Structural contract every convention module (and revision submodule) satisfies."""

    UUID: str
    SCHEMA_URL: str
    SPEC_URL: str
    CMO: ConventionMetadataObject
    CONVENTION_KEYS: set[str]

    # ``create`` is typed as an attribute, not a method: each convention's
    # ``create`` has a distinct concrete keyword signature (e.g. ``dimensions``,
    # ``bbox``) with *required* keyword params, which is structurally incompatible
    # with a uniform ``create(**kwargs: Any)`` method. As a Protocol attribute the
    # return type is matched invariantly, so even ``Callable[..., Mapping[str, Any]]``
    # rejects a ``-> SpatialAttrs`` (TypedDict) function; ``Callable[..., Any]`` is
    # the minimal form that accepts every convention's ``create`` while still
    # requiring the member to exist and be callable.
    create: Callable[..., Any]

    def insert(
        self, attrs: dict[str, Any], data: Any, *, overwrite: bool = ...
    ) -> dict[str, Any]: ...
    def extract(
        self, attrs: dict[str, Any]
    ) -> tuple[dict[str, Any], Mapping[str, Any]]: ...
    def validate(self, data: dict[str, Any]) -> Mapping[str, Any]: ...


if TYPE_CHECKING:
    from .spatial import _r2 as _spatial_r2

    _check_spatial_r2: ConventionModule = _spatial_r2
