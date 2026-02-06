from __future__ import annotations


def wrap_attrs(
    attrs: dict[str, object], *, node_type: str = "array"
) -> dict[str, object]:
    """Wrap attributes dict in a full Zarr node metadata dict for schema validation."""
    return {"zarr_format": 3, "node_type": node_type, "attributes": attrs}
