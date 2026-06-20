from __future__ import annotations

from zarr_cm import license as license_
from zarr_cm import multiscales, proj, spatial, uom
from zarr_cm._contract import ConventionModule


def _dispatch_targets() -> list[tuple[str, object]]:
    """Every module the package actually dispatches to: each non-revisioned
    convention module, plus every revision submodule of a revisioned convention.

    Revisioned conventions expose their per-revision submodules as public
    ``r2``/``r3``/... namespaces (the underlying modules that carry the full
    convention surface); ``_REVISIONS`` holds thin dispatch wrappers, not the
    modules, so we discover the public revision namespaces here instead."""
    targets: list[tuple[str, object]] = []
    for name, mod in (
        ("geo-proj", proj),
        ("spatial", spatial),
        ("multiscales", multiscales),
        ("license", license_),
        ("uom", uom),
    ):
        revisions = getattr(mod, "_REVISIONS", None)
        if revisions is None:
            targets.append((name, mod))
        else:
            targets.extend(
                (f"{name}:{label}", getattr(mod, label)) for label in revisions
            )
    return targets


# Note: importing ConventionModule at module scope (above) already proves
# zarr_cm._contract imports cleanly at runtime — if it didn't, this whole test
# module would fail to collect. No separate import test is needed.


def test_all_dispatch_targets_satisfy_contract() -> None:
    targets = _dispatch_targets()
    # Sanity: we actually found the known set (7 today: spatial r2/r3,
    # proj r2/r3, multiscales, license, uom).
    assert len(targets) >= 7
    for name, mod in targets:
        assert isinstance(mod, ConventionModule), (
            f"dispatch target {name!r} does not satisfy ConventionModule"
        )
