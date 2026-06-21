"""PEP 695 ``type`` aliases for the JSON value types (Python >= 3.12 only).

This module is imported by :mod:`zarr_cm._core` *only* on Python 3.12+. It is
kept separate because the ``type`` statement is a syntax error on 3.11, so it
cannot live behind a runtime ``if`` in a module that 3.11 must import.

Using the native ``type`` statement (rather than ``typing_extensions.TypeAliasType``)
matters for two reasons:

* pydantic can resolve a *recursive* alias only when it is a real
  ``TypeAliasType`` -- an implicit ``X = ... "X" ...`` union makes
  ``model_rebuild()`` raise ``RecursionError`` for any model that embeds a
  convention ``TypedDict`` (which uses ``JsonValue`` as ``extra_items``).
* pyright resolves the native ``type`` form's recursion cleanly across module
  boundaries, whereas it degrades a ``TypeAliasType``-constructed recursive
  alias to ``Sequence[Unknown]`` / ``Mapping[str, Unknown]`` project-wide.

The 3.11 fallback in ``_core`` uses ``TypeAliasType`` (fixes pydantic at
runtime); the project's own type checking runs at ``pythonVersion = 3.12`` so it
exercises this clean definition.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

# This module is imported only on Python 3.12+ (guarded in zarr_cm._core), so the
# PEP 695 ``type`` statement is safe here even though the package floor is 3.11.
# pylint: disable=using-generic-type-syntax-in-unsupported-version
JsonPrimitive = bool | int | float | str | None
type JsonValue = JsonPrimitive | Sequence[JsonValue] | Mapping[str, JsonValue]
type JsonDict = dict[str, JsonValue]
