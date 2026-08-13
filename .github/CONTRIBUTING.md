See the [Scientific Python Developer Guide][spc-dev-intro] for a detailed
description of best practices for developing scientific packages.

[spc-dev-intro]: https://learn.scientific-python.org/development/

# Quick development

Development tasks are defined in the [`justfile`](../justfile) at the repository
root. You need two tools:

- [`just`](https://just.systems), the command runner
- [`uv`](https://docs.astral.sh/uv/), which manages Python and every dependency

Everything else is fetched on demand, so there is nothing else to install. Run
`just` on its own to list the recipes:

```console
$ just              # list all recipes
$ just sync         # create the development environment in .venv
$ just check        # everything CI runs: lint, pylint, type check, tests
```

CI runs these same recipes, so a green `just check` locally means the same
commands passed with the same flags.

# Testing

```console
$ just test                 # the test suite
$ just test -k spatial      # arguments are passed through to pytest
$ just test-cov             # with a coverage report
$ just test-python 3.14     # against one other Python, in a throwaway env
$ just test-all             # against every supported Python (uv downloads them)
```

# Linting and type checking

```console
$ just lint          # the prek hooks over all files
$ just lint-install  # install them as a git pre-commit hook
$ just typecheck     # pyright over src and tests
$ just pylint        # Pylint, which needs the package installed
```

Hooks are run by [prek](https://prek.j178.dev), a drop-in replacement for
pre-commit that reads the same `.pre-commit-config.yaml`. Refresh the pinned
hook revisions with `just update-hooks`.

# Building docs

```console
$ just docs        # serve locally with live reload
$ just docs-build  # build into site/
```

# Dependencies

`uv.lock` is committed, so everyone resolves the same dependency versions. After
editing dependencies in `pyproject.toml`, run `just lock` and commit the result
— CI fails if the lockfile is out of date. `just lock --upgrade` moves the
pinned versions forward.
