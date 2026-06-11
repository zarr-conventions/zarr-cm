"""Check upstream convention schemas for changes.

Compares locally stored schema snapshots against the current upstream versions.
Exits with code 0 if no changes are detected, code 1 if changes are found.
When changes are found, prints a markdown-formatted summary to stdout.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "upstream-schemas"
SOURCES_FILE = SCHEMAS_DIR / "sources.json"


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read().decode()


def main() -> None:
    sources: dict[str, dict[str, str]] = json.loads(SOURCES_FILE.read_text())
    changed: list[dict[str, str]] = []

    for filename, info in sources.items():
        snapshot_path = SCHEMAS_DIR / filename
        url = info["url"]
        repo = info["repo"]

        try:
            upstream_content = fetch(url)
        except Exception as exc:
            print(f"::warning::Failed to fetch {url}: {exc}", file=sys.stderr)
            continue

        if not snapshot_path.exists():
            changed.append({"repo": repo, "reason": "no local snapshot found"})
            snapshot_path.write_text(upstream_content)
            continue

        local_content = snapshot_path.read_text()
        if upstream_content != local_content:
            changed.append({"repo": repo, "reason": "schema content has changed"})
            snapshot_path.write_text(upstream_content)

    if not changed:
        print("All upstream schemas are unchanged.")
        sys.exit(0)

    summary = "## Upstream schema changes detected\n\n"
    summary += "The following upstream convention schemas have changed:\n\n"
    for item in changed:
        summary += f"- **{item['repo']}**: {item['reason']}\n"
    summary += (
        "\nThe snapshots in `.github/upstream-schemas/` have been updated. "
        "Please review the upstream changes and update the corresponding "
        "convention modules in `src/zarr_cm/` if needed."
    )
    print(summary)
    sys.exit(1)


if __name__ == "__main__":
    main()
