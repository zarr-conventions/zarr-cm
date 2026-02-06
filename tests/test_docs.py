from __future__ import annotations

import pytest
from pytest_examples import CodeExample, EvalExample, find_examples


@pytest.mark.parametrize("example", find_examples("docs/", "README.md"), ids=str)
def test_docs_examples(example: CodeExample, eval_example: EvalExample) -> None:
    if eval_example.update_examples:
        eval_example.run_print_update(example)
    else:
        eval_example.run_print_check(example)
