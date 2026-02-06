from __future__ import annotations

import importlib.metadata

import pytest

import zarr_cm as m
from zarr_cm._core import validate_convention_metadata_object


def test_version():
    assert importlib.metadata.version("zarr_cm") == m.__version__


def test_validate_cmo_valid() -> None:
    validate_convention_metadata_object({"uuid": "abc"})


def test_validate_cmo_empty() -> None:
    with pytest.raises(ValueError, match="at least one"):
        validate_convention_metadata_object({})
