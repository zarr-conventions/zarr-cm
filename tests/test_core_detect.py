from __future__ import annotations

import pytest

from zarr_cm._core import resolve_revision_label

UUID = "test-uuid-1234"
URLS = {"r1": "https://example/r1.json", "r2": "https://example/r2.json"}


def _attrs(schema_url: str | None) -> dict[str, object]:
    cmo: dict[str, object] = {"uuid": UUID}
    if schema_url is not None:
        cmo["schema_url"] = schema_url
    return {"zarr_conventions": [cmo]}


def test_returns_label_for_known_url() -> None:
    assert resolve_revision_label(_attrs(URLS["r1"]), UUID, URLS, "demo") == "r1"
    assert resolve_revision_label(_attrs(URLS["r2"]), UUID, URLS, "demo") == "r2"


def test_returns_none_for_present_but_unknown_url() -> None:
    got = resolve_revision_label(
        _attrs("https://example/UNKNOWN.json"), UUID, URLS, "demo"
    )
    assert got is None


def test_raises_when_convention_absent() -> None:
    with pytest.raises(ValueError, match="demo"):
        resolve_revision_label({"zarr_conventions": []}, UUID, URLS, "demo")
    with pytest.raises(ValueError, match="demo"):
        resolve_revision_label({}, UUID, URLS, "demo")


def test_returns_none_when_cmo_has_no_schema_url() -> None:
    # Present by UUID but the CMO carries no schema_url at all -> unrecognized.
    assert resolve_revision_label(_attrs(None), UUID, URLS, "demo") is None
