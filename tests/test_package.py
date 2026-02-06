from __future__ import annotations

import importlib.metadata

import zarr_cm as m


def test_version():
    assert importlib.metadata.version("zarr_cm") == m.__version__
