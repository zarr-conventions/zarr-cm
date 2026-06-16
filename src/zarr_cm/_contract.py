"""Structural contract for convention modules dispatched by the registry.

Defines :class:`ConventionModule` and statically asserts that every convention
module (and revision submodule) satisfies it. A signature or constant drift in
any dispatch target fails ``mypy src/`` at the corresponding ``_check_*`` line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ._core import ConventionMetadataObject


@runtime_checkable
class ConventionModule(Protocol):
    """Structural contract every convention module (and revision submodule) satisfies.

    Pins the dispatch surface: the constants ``UUID``/``SCHEMA_URL``/``SPEC_URL``/
    ``CMO``/``CONVENTION_KEYS`` and the operations ``create``/``insert``/``extract``/
    ``validate``. Operation return types are widened to ``Mapping[str, Any]`` so that
    each convention's own ``*Attrs`` ``TypedDict`` still structurally conforms.
    """

    UUID: str
    SCHEMA_URL: str
    SPEC_URL: str
    CMO: ConventionMetadataObject
    CONVENTION_KEYS: set[str]

    # ``create`` uses ``*args, **kwargs`` because each convention's ``create`` has
    # a distinct concrete keyword signature (e.g. ``dimensions``, ``bbox``) with
    # *required* keyword params — not substitutable for a fixed parameter list.
    # As a *method* (not a ``Callable`` attribute) the params are checked
    # contravariantly so ``*args, **kwargs`` accepts any of them, while the return
    # type stays covariant — so ``-> Mapping[str, Any]`` still has teeth: a
    # ``create`` returning a non-mapping fails the check (a ``Callable`` attribute
    # would lose that, matching the return invariantly and forcing ``Any``).
    def create(self, *args: Any, **kwargs: Any) -> Mapping[str, Any]: ...

    def insert(
        self, attrs: dict[str, Any], data: Any, *, overwrite: bool = ...
    ) -> dict[str, Any]: ...
    def extract(
        self, attrs: dict[str, Any]
    ) -> tuple[dict[str, Any], Mapping[str, Any]]: ...
    def validate(self, data: dict[str, Any]) -> Mapping[str, Any]: ...


if TYPE_CHECKING:
    from . import license as _license
    from . import uom as _uom
    from .multiscales import _r1 as _multiscales_r1
    from .multiscales import _r2 as _multiscales_r2
    from .proj import _r1 as _proj_r1
    from .proj import _r2 as _proj_r2
    from .spatial import _r1 as _spatial_r1
    from .spatial import _r2 as _spatial_r2

    # Each dispatch target must satisfy ConventionModule. A signature/constant
    # drift in any of these fails `mypy src/` at the corresponding line.
    # Adding a convention or revision means adding one line here.
    _check_spatial_r1: ConventionModule = _spatial_r1
    _check_spatial_r2: ConventionModule = _spatial_r2
    _check_proj_r1: ConventionModule = _proj_r1
    _check_proj_r2: ConventionModule = _proj_r2
    _check_multiscales_r1: ConventionModule = _multiscales_r1
    _check_multiscales_r2: ConventionModule = _multiscales_r2
    _check_license: ConventionModule = _license
    _check_uom: ConventionModule = _uom
