from __future__ import annotations

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples


# Scope to the user-facing docs with runnable examples, named explicitly rather
# than recursing all of docs/ (which may hold docs whose ``python`` fences are
# illustrative, not runnable). Add new runnable doc files here explicitly.
@pytest.mark.parametrize(
    "example", list(find_examples("docs/index.md", "README.md")), ids=str
)
def test_docs_examples(example: CodeExample, eval_example: EvalExample) -> None:
    if eval_example.update_examples:
        eval_example.run_print_update(example)
    else:
        eval_example.run_print_check(example)
