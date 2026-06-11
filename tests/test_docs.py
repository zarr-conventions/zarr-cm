from __future__ import annotations

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples


# Scope to user-facing docs only. docs/superpowers/ holds planning/spec docs
# whose ``python`` fences are illustrative, not runnable; recursing all of
# docs/ would try to execute them. Add new runnable doc files here explicitly.
@pytest.mark.parametrize(
    "example", find_examples("docs/index.md", "README.md"), ids=str
)
def test_docs_examples(example: CodeExample, eval_example: EvalExample) -> None:
    if eval_example.update_examples:
        eval_example.run_print_update(example)
    else:
        eval_example.run_print_check(example)
