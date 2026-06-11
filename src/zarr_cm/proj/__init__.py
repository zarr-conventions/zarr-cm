"""proj convention: https://github.com/zarr-conventions/proj

Formerly known as geo-proj. ``r1`` is the original draft kept verbatim with
its historical URLs so existing documents round-trip correctly. The
package-level functions dispatch by a keyword-only ``revision`` argument and
default to the latest revision for writes / auto-detect for reads.
"""

from __future__ import annotations

import typing
from typing import Any, Final, cast

from zarr_cm._core import detect_revision

from . import _r1, _r2

if typing.TYPE_CHECKING:
    import types
from ._r2 import (
    CMO as CMO,
)
from ._r2 import (
    CONVENTION_KEYS as CONVENTION_KEYS,
)
from ._r2 import (
    SCHEMA_URL as SCHEMA_URL,
)
from ._r2 import (
    SPEC_URL as SPEC_URL,
)
from ._r2 import (
    UUID as UUID,
)
from ._r2 import (
    GeoProjAttrs as GeoProjAttrs,
)
from ._r2 import (
    GeoProjConventionAttrs as GeoProjConventionAttrs,
)

_REVISIONS: Final[dict[str, types.ModuleType]] = {"r1": _r1, "r2": _r2}
LATEST: Final = "r2"

# public per-revision namespaces
r1 = _r1
r2 = _r2

_SCHEMA_URL_BY_REVISION: Final[dict[str, str]] = {
    label: mod.SCHEMA_URL for label, mod in _REVISIONS.items()
}


def _resolve_read_revision(attrs: dict[str, Any], revision: str | None) -> str:
    if revision is not None:
        return revision
    return detect_revision(attrs, UUID, _SCHEMA_URL_BY_REVISION) or LATEST


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


def validate(data: dict[str, Any], *, revision: str | None = None) -> Any:
    return _revision(_resolve_read_revision(data, revision)).validate(data)


def extract(attrs: dict[str, Any], *, revision: str | None = None) -> Any:
    return _revision(_resolve_read_revision(attrs, revision)).extract(attrs)
