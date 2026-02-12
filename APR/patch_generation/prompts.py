"""
LLM repair prompt template and test case formatting.
"""
from __future__ import annotations

from typing import Any, List

from ..input.schema import APRInput, TestCase
from .schema import GeneratedPatch


REPAIR_PROMPT_TEMPLATE = """Fix the code by resolving all [ERROR START/END] blocks.

## Problem
{problem_description}

## Function Signature
{function_signature}

## Code with Errors Marked
```python
{patched_code}
```

## Instructions
- Replace each <<<<<<< [ERROR START: X] ... >>>>>>> [ERROR END: X] block with correct code
- Remove all marker lines (<<<<<<<, =======, >>>>>>>)
- Preserve all other code exactly
- Ensure the fixed code passes: {test_cases_summary}
"""


def format_test_cases(test_cases: List[TestCase] | None) -> str:
    """Summarize test cases for the repair prompt."""
    if not test_cases:
        return "No test cases provided."
    parts = []
    for i, tc in enumerate(test_cases[:10], 1):
        tid = tc.get("test_id") or f"test_{i}"
        inp = tc.get("input_expression") or "?"
        expected = tc.get("expected_output")
        parts.append(f"  {tid}: {inp} -> {expected}")
    if len(test_cases) > 10:
        parts.append(f"  ... and {len(test_cases) - 10} more")
    return "\n".join(parts) if parts else "No test cases provided."


def build_repair_prompt(
    apr_input: APRInput,
    patch: GeneratedPatch,
    template: str = REPAIR_PROMPT_TEMPLATE,
) -> str:
    """Build the full repair prompt string for an LLM."""
    return template.format(
        problem_description=apr_input.get("problem_description") or "",
        function_signature=apr_input.get("function_signature") or "",
        patched_code=patch.get("patched_code") or "",
        test_cases_summary=format_test_cases(apr_input.get("test_cases")),
    )
