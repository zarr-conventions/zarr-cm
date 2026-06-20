"""Structural contract for convention modules dispatched by the registry.

Defines :class:`ConventionModule` and statically asserts that every convention
module (and revision submodule) satisfies it. A signature or constant drift in
any dispatch target fails ``pyright src/`` at the corresponding ``_check_*`` line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ._core import ConventionMetadataObject


@runtime_checkable
class ConventionModule(Protocol):
    """Structural contract every convention module (and revision submodule) satisfies.

    Pins the dispatch surface: the constants ``UUID``/``SCHEMA_URL``/``SPEC_URL``/
    ``CMO``/``CONVENTION_KEYS`` and the operations ``create``/``insert``/``extract``/
    ``validate``. The callable signatures themselves are pinned by the typed
    dispatch protocols in the aggregate modules, while this structural protocol
    verifies each convention module exposes the shared names.
    """

    # The uppercase property names below deliberately mirror the module-level
    # constants they pin (UUID/SCHEMA_URL/...), so snake_case does not apply.
    # pylint: disable=invalid-name

    # Read-only properties (not plain attributes): a plain ``x: str`` Protocol
    # member is mutable and therefore invariant, which would reject the modules'
    # ``Final``/``Literal`` constants (e.g. ``UUID: Final = "689b..."``). Declaring
    # them as read-only properties makes the member covariant so the literal
    # constants satisfy the contract.
    @property
    def UUID(self) -> str: ...
    @property
    def SCHEMA_URL(self) -> str: ...
    @property
    def SPEC_URL(self) -> str: ...
    @property
    def CMO(self) -> ConventionMetadataObject: ...
    @property
    def CONVENTION_KEYS(self) -> set[str]: ...

    # Likewise read-only: the modules expose these as plain functions, which are
    # only assignable to an invariant ``object`` member via a covariant property.
    @property
    def create(self) -> object: ...
    @property
    def insert(self) -> object: ...
    @property
    def extract(self) -> object: ...
    @property
    def validate(self) -> object: ...


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
    # drift in any of these fails `pyright src/` at the corresponding line.
    # Adding a convention or revision means adding one line here.
    _check_spatial_r1: ConventionModule = _spatial_r1
    _check_spatial_r2: ConventionModule = _spatial_r2
    _check_proj_r1: ConventionModule = _proj_r1
    _check_proj_r2: ConventionModule = _proj_r2
    _check_multiscales_r1: ConventionModule = _multiscales_r1
    _check_multiscales_r2: ConventionModule = _multiscales_r2
    _check_license: ConventionModule = _license
    _check_uom: ConventionModule = _uom
