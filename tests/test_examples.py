from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
_SCRIPTS = sorted(_EXAMPLES_DIR.glob("*.py"))


def test_examples_dir_is_populated() -> None:
    assert len(_SCRIPTS) >= 5, f"expected >=5 example scripts, found {_SCRIPTS}"


@pytest.mark.parametrize("script", _SCRIPTS, ids=lambda p: p.stem)
def test_example_runs_clean(script: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"{script.name} exited {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert result.stdout.strip().endswith("OK")
