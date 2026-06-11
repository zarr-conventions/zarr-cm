"""spatial convention: https://github.com/zarr-conventions/spatial

Exposes revisions of the spatial convention. ``r1`` is the original
2D-or-3D draft; later revisions track upstream changes. The package-level
functions dispatch by a keyword-only ``revision`` argument and default to
the latest revision for writes / auto-detect for reads.
"""

from __future__ import annotations

import typing
from typing import Any, Final, cast

from . import _r1

if typing.TYPE_CHECKING:
    import types
from ._r1 import (
    CMO as CMO,
)
from ._r1 import (
    CONVENTION_KEYS as CONVENTION_KEYS,
)
from ._r1 import (
    SCHEMA_URL as SCHEMA_URL,
)
from ._r1 import (
    SPEC_URL as SPEC_URL,
)
from ._r1 import (
    UUID as UUID,
)
from ._r1 import (
    SpatialAttrs as SpatialAttrs,
)
from ._r1 import (
    SpatialConventionAttrs as SpatialConventionAttrs,
)

_REVISIONS: Final[dict[str, types.ModuleType]] = {"r1": _r1}
LATEST: Final = "r1"

# public per-revision namespaces
r1 = _r1


def _revision(label: str) -> Any:
    try:
        return _REVISIONS[label]
    except KeyError:
        msg = f"Unknown revision {label!r}. Valid revisions: {sorted(_REVISIONS)}"
        raise ValueError(msg) from None


def create(*args: Any, revision: str = LATEST, **kwargs: Any) -> Any:
    return _revision(revision).create(*args, **kwargs)


def insert(
    attrs: dict[str, Any], data: Any, *, revision: str = LATEST, overwrite: bool = False
) -> dict[str, Any]:
    return cast(
        "dict[str, Any]", _revision(revision).insert(attrs, data, overwrite=overwrite)
    )


def validate(data: dict[str, Any], *, revision: str = LATEST) -> Any:
    return _revision(revision).validate(data)


def extract(attrs: dict[str, Any], *, revision: str = LATEST) -> Any:
    return _revision(revision).extract(attrs)
