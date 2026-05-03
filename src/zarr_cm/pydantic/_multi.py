"""Multi-convention helpers for the pydantic layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from zarr_cm import ConventionName
    from zarr_cm.pydantic._base import ConventionModel


def build_attrs(
    *models: ConventionModel,
    base: dict[str, Any] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Insert one or more convention models into a single attributes dict.

    Each model's CMO is appended to ``zarr_conventions``. Convention
    properties are merged at the root of *attrs* (flat-key) or nested
    under a single key (wrapper-key), depending on the model.

    Collision behavior: if *base* contains a key that a model would write
    and *overwrite* is False, ``ValueError`` is raised. With
    ``overwrite=True`` the model's value wins.
    """
    result: dict[str, Any] = dict(base) if base else {}
    for m in models:
        result = m.insert(result, overwrite=overwrite)
    return result


def parse_attrs(
    attrs: dict[str, Any],
    *,
    strict: bool = False,
) -> tuple[dict[str, Any], dict[ConventionName, ConventionModel]]:
    """Detect and extract every known convention model from *attrs*.

    Detection is by ``uuid`` in ``zarr_conventions``. Unknown UUIDs are
    ignored by default (forward compatibility); when *strict* is True any
    unrecognized UUID raises ``ValueError``.

    Returns ``(remaining, models)`` where ``models`` keys are
    ``ConventionName`` literals (e.g. ``"geo-proj"``).
    """
    # Local import avoids an import cycle at package load (see __init__.py).
    from zarr_cm.pydantic import _MODEL_REGISTRY, _NAME_BY_UUID  # noqa: PLC0415

    remaining = attrs
    found: dict[ConventionName, ConventionModel] = {}
    for cmo in list(attrs.get("zarr_conventions", [])):
        uuid = cmo.get("uuid")
        if uuid is None:
            continue
        cls = _MODEL_REGISTRY.get(uuid)
        if cls is None:
            if strict:
                msg = f"Unknown convention UUID: {uuid}"
                raise ValueError(msg)
            continue
        remaining, parsed = cls.extract(remaining)
        if parsed is None:
            continue
        name = cast("ConventionName", _NAME_BY_UUID[uuid])
        found[name] = parsed
    return remaining, found
