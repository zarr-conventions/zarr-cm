from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeGuard


def _is_mapping(value: object) -> TypeGuard[Mapping[object, object]]:
    return isinstance(value, Mapping)


def _is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    return isinstance(value, Sequence) and not isinstance(
        value, str | bytes | bytearray
    )


def wrap_attrs(
    attrs: Mapping[str, object], *, node_type: str = "array"
) -> dict[str, object]:
    """Wrap attributes dict in a full Zarr node metadata dict for schema validation."""
    return {"zarr_format": 3, "node_type": node_type, "attributes": attrs}


def as_mapping(value: object) -> Mapping[str, object]:
    """Narrow a JSON value known by the test to be an object."""
    assert _is_mapping(value)
    result: dict[str, object] = {}
    for key, item in value.items():
        assert isinstance(key, str)
        result[key] = item
    return result


def as_sequence(value: object) -> Sequence[object]:
    """Narrow a JSON value known by the test to be an array."""
    assert _is_sequence(value)
    return list(value)
