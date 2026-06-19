"""Structural contract for convention modules dispatched by the registry.

Defines :class:`ConventionModule` and statically asserts that every convention
module (and revision submodule) satisfies it. A signature or constant drift in
any dispatch target fails ``mypy src/`` at the corresponding ``_check_*`` line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from typing import cast

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

    UUID: str
    SCHEMA_URL: str
    SPEC_URL: str
    CMO: ConventionMetadataObject
    CONVENTION_KEYS: set[str]

    create: object
    insert: object
    extract: object
    validate: object


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
    _check_spatial_r1: ConventionModule = cast("ConventionModule", _spatial_r1)
    _check_spatial_r2: ConventionModule = cast("ConventionModule", _spatial_r2)
    _check_proj_r1: ConventionModule = cast("ConventionModule", _proj_r1)
    _check_proj_r2: ConventionModule = cast("ConventionModule", _proj_r2)
    _check_multiscales_r1: ConventionModule = cast("ConventionModule", _multiscales_r1)
    _check_multiscales_r2: ConventionModule = cast("ConventionModule", _multiscales_r2)
    _check_license: ConventionModule = cast("ConventionModule", _license)
    _check_uom: ConventionModule = cast("ConventionModule", _uom)
