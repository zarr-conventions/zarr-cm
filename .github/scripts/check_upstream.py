"""Detect schema drift between vendored snapshots and upstream main.

This script compares the vendored JSON schema snapshots under
``.github/upstream-schemas/`` against the current ``main`` branch schema
of each tracked upstream convention repository.

It ONLY detects drift — it never edits ``src/`` or creates new revision
files.  Authoring a new ``_rN.py`` is a deliberate human step.

Exit codes
----------
0  All tracked conventions are in sync with their vendored snapshots.
1  One or more conventions have drifted, or a network error occurred.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[2]

TRACKED: dict[str, dict[str, str]] = {
    "spatial": {
        "upstream": "https://raw.githubusercontent.com/zarr-conventions/spatial/main/schema.json",
        "vendored": ".github/upstream-schemas/spatial/54d81b7ced0376e63ee10f34db31db7d08dcc28d.json",
    },
    "proj": {
        "upstream": "https://raw.githubusercontent.com/zarr-conventions/proj/main/schema.json",
        "vendored": ".github/upstream-schemas/proj/5ca5b2f92e5c7245f957d9128b289ee535f0720d.json",
    },
    "multiscales": {
        "upstream": "https://raw.githubusercontent.com/zarr-conventions/multiscales/main/schema.json",
        "vendored": ".github/upstream-schemas/multiscales/9b78efa75fef0fed302d9cf880037c569354d860.json",
    },
}


class CheckResult(TypedDict):
    convention: str
    status: Literal["ok", "drift", "error"]
    message: str


def fetch_upstream(url: str) -> object:
    """Fetch and JSON-parse the schema at *url*.

    Raises ``urllib.error.URLError`` on network failure.
    """
    with urllib.request.urlopen(url, timeout=30) as response:
        body = response.read()
    return json.loads(body)


def load_vendored(path: str) -> object:
    """Load and JSON-parse the vendored snapshot at *path* (repo-root-relative)."""
    full_path = REPO_ROOT / path
    return json.loads(full_path.read_text(encoding="utf-8"))


def check_convention(name: str, config: dict[str, str]) -> CheckResult:
    """Check one convention for drift.

    Returns a :class:`CheckResult` describing the outcome.
    """
    vendored_path = config["vendored"]
    upstream_url = config["upstream"]
    sha = Path(vendored_path).stem

    try:
        upstream_schema = fetch_upstream(upstream_url)
    except urllib.error.URLError as exc:
        return CheckResult(
            convention=name,
            status="error",
            message=f"network error fetching {upstream_url!r}: {exc}",
        )

    try:
        vendored_schema = load_vendored(vendored_path)
    except OSError as exc:
        return CheckResult(
            convention=name,
            status="error",
            message=f"could not read vendored snapshot {vendored_path!r}: {exc}",
        )

    if upstream_schema == vendored_schema:
        return CheckResult(
            convention=name,
            status="ok",
            message="upstream main matches vendored snapshot",
        )
    return CheckResult(
        convention=name,
        status="drift",
        message=(
            f"upstream main differs from vendored snapshot {sha}; "
            "consider snapshotting a new revision"
        ),
    )


def main() -> int:
    """Run drift detection for all tracked conventions.

    Returns the exit code (0 = all OK, 1 = drift or error).
    """
    exit_code = 0
    for name, config in TRACKED.items():
        result = check_convention(name, config)
        status = result["status"].upper()
        message = result["message"]
        if result["status"] == "ok":
            print(f"[{name}] {status}: {message}")
        elif result["status"] == "drift":
            print(f"[{name}] {status}: {message}", file=sys.stderr)
            exit_code = 1
        else:  # error
            print(f"[{name}] WARNING ({status}): {message}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
