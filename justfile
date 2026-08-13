# Development tasks for zarr-cm.
#
# Requires `just` (https://just.systems) and `uv` (https://docs.astral.sh/uv/).
# Everything else is fetched on demand by uv, so no other setup is needed.
#
# The recipes that use the project environment all ask for the same dependency
# groups (`--all-groups`), so running them in any order never re-syncs .venv.
# `test-ci` is the one exception: CI starts from a clean environment per job,
# so it installs the test group alone rather than paying for the docs group.

coverage_args := "-ra --cov --cov-report=xml --cov-report=term --durations=20"

# PyPy is not expressible as a classifier, so `test-all` appends the one CI runs
# to the CPython versions read out of pyproject.toml.
pypy_version := "pypy3.11"

# List the available recipes
default:
    @just --list

# The package is reinstalled so that the hatch-vcs version recorded in the
# environment follows the current commit, which `test_version` checks.
[doc("Sync the local development environment (all dependency groups)")]
sync:
    uv sync --all-groups --reinstall-package zarr-cm

# Re-resolve uv.lock. Pass --upgrade to move pinned versions forward.
lock *args:
    uv lock {{ args }}

# Syncs first so the recorded version matches HEAD after a fresh commit.
[doc("Run every check that CI runs: lint, pylint, type check, tests")]
check: sync lint pylint typecheck test

# Run the prek hooks (ruff, prettier, pyright on src, ...) over all files
lint *args:
    uvx prek run --all-files --show-diff-on-failure {{ args }}

# Install the hooks into .git/hooks so they run on every commit
lint-install:
    uvx prek install

# Update the pinned hook revisions in .pre-commit-config.yaml
update-hooks *args:
    uvx prek update {{ args }}

# Pylint needs the package importable, so it runs against an install of it
# rather than as a hook. Slower than the prek hooks, hence not part of `lint`.
[doc("Run Pylint over the package")]
pylint *args:
    uv run --isolated --no-default-groups --with "pylint>=3.2" pylint zarr_cm {{ args }}

# Type check src/ and tests/ with pyright
typecheck *args:
    uv run --all-groups pyright {{ args }}

# Run the test suite
test *args:
    uv run --all-groups pytest {{ args }}

# Run the test suite with coverage
test-cov *args:
    uv run --all-groups pytest {{ coverage_args }} {{ args }}

# Run the test suite the way CI does, with only the test group installed
test-ci *args:
    uv run --no-default-groups --group test pytest {{ coverage_args }} {{ args }}

# Print the CPython versions this package claims to support, read out of the
# `Programming Language :: Python :: X.Y` classifiers in pyproject.toml.
python-versions:
    @uv run --no-project python -c 'import re,tomllib,pathlib;d=tomllib.loads(pathlib.Path("pyproject.toml").read_text());print(" ".join(c.split()[-1] for c in d["project"]["classifiers"] if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)))'

# The environment is isolated from .venv, so it can skip the docs group without
# forcing a re-sync the way the in-project recipes would.
[doc("Run the test suite against another Python version, in a throwaway environment")]
test-python version *args:
    uv run --isolated --no-default-groups --group test --python {{ version }} pytest {{ args }}

# uv downloads any interpreter that is not already installed. CI covers the
# ends of this range plus pypy; this runs the whole sweep locally.
[doc("Run the test suite against every supported Python version")]
test-all *args:
    #!/usr/bin/env bash
    set -euo pipefail
    for version in $(just python-versions) {{ pypy_version }}; do
        echo "--- Python $version ---"
        just test-python "$version" {{ args }}
    done

# Serve the docs locally with live reload
docs *args:
    uv run --all-groups mkdocs serve --clean {{ args }}

# Build the docs into site/
docs-build *args:
    uv run --all-groups mkdocs build --clean {{ args }}

# Build an sdist and a wheel into dist/
build *args:
    uv build {{ args }}

# Check the vendored convention schemas against upstream main
check-upstream:
    uv run --no-project python .github/scripts/check_upstream.py

# Remove build, docs, and tool cache artifacts
clean:
    rm -rf build dist site .coverage coverage.xml .pytest_cache .ruff_cache
    find . -name '__pycache__' -type d -prune -exec rm -rf {} +
