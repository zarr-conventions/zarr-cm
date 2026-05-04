from __future__ import annotations

import builtins
import importlib
import sys
from typing import Any

import pytest


def test_zarr_cm_import_does_not_pull_pydantic() -> None:
    """Plain ``import zarr_cm`` must not import zarr_cm.pydantic.

    Verifies the optional extra is truly optional: a user who installs
    ``zarr-cm`` without the extra never executes the pydantic guard at
    all (because the subpackage is never imported).
    """
    # Reset zarr_cm and zarr_cm.pydantic so a fresh import is observable.
    for mod_name in [m for m in list(sys.modules) if m.startswith("zarr_cm")]:
        del sys.modules[mod_name]

    importlib.import_module("zarr_cm")

    assert "zarr_cm" in sys.modules
    assert "zarr_cm.pydantic" not in sys.modules


def test_zarr_cm_pydantic_import_error_when_pydantic_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Importing ``zarr_cm.pydantic`` without pydantic raises a clear error."""
    # Drop any cached version of zarr_cm.pydantic and pydantic itself.
    for mod_name in [
        m
        for m in list(sys.modules)
        if m == "pydantic" or m.startswith("zarr_cm.pydantic")
    ]:
        del sys.modules[mod_name]

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "pydantic" or name.startswith("pydantic."):
            msg = f"No module named {name!r}"
            raise ImportError(msg)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError, match="zarr-cm\\[pydantic\\]"):
        importlib.import_module("zarr_cm.pydantic")
