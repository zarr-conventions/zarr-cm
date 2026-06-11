from __future__ import annotations

import zarr_cm
from zarr_cm._contract import ConventionModule


def _dispatch_targets() -> list[tuple[str, object]]:
    """Every module the package actually dispatches to: each registry module,
    plus every revision submodule of a revisioned convention."""
    targets: list[tuple[str, object]] = []
    for name, mod in zarr_cm._REGISTRY.items():
        revisions = getattr(mod, "_REVISIONS", None)
        if revisions is None:
            targets.append((name, mod))
        else:
            for label, rev_mod in revisions.items():
                targets.append((f"{name}:{label}", rev_mod))
    return targets


# Note: importing ConventionModule at module scope (above) already proves
# zarr_cm._contract imports cleanly at runtime — if it didn't, this whole test
# module would fail to collect. No separate import test is needed.


def test_all_dispatch_targets_satisfy_contract() -> None:
    targets = _dispatch_targets()
    # Sanity: we actually found the known set (7 today: spatial r1/r2,
    # proj r1/r2, multiscales, license, uom).
    assert len(targets) >= 7
    for name, mod in targets:
        assert isinstance(mod, ConventionModule), (
            f"dispatch target {name!r} does not satisfy ConventionModule"
        )
