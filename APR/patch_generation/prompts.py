"""
LLM repair prompt template and test case formatting.
"""
from __future__ import annotations

from typing import Any, List, Optional

from ..input.schema import APRInput, TestCase
from .schema import GeneratedPatch

try:
    from ..DS_KG.engine import DSKGEngine
    from .kg_integration import (
        build_kg_context,
        extract_error_signatures,
        query_kg_for_errors,
    )
    KG_AVAILABLE = True
except ImportError:
    DSKGEngine = None  # type: ignore
    KG_AVAILABLE = False


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


REPAIR_PROMPT_ERROR_LINE = """Fix the error in the code below.

## Error
Line {error_line}: {error_message}

## Problem
{problem_description}

## Code with Error Marked
```python
{patched_code}
```

## Instructions
- Fix the marked block at line {error_line}
- Remove all marker lines (<<<<<<<, =======, >>>>>>>)
- Return the corrected code
"""


REPAIR_PROMPT_ERROR_LINE_WITH_KG = """Fix the error in the code below using the provided API documentation.

## API Documentation
{kg_context}

## Error
Line {error_line}: {error_message}

## Problem
{problem_description}

## Code with Error Marked
```python
{patched_code}
```

## Instructions
- Refer to API Documentation above for correct usage
- Fix the marked block at line {error_line}
- Remove all marker lines (<<<<<<<, =======, >>>>>>>)
- Return only the corrected code
"""


REPAIR_PROMPT_TEMPLATE_WITH_KG = """Fix the code by resolving all [ERROR START/END] blocks using the provided API documentation.

## API Documentation
{kg_context}

## Problem
{problem_description}

## Function Signature
{function_signature}

## Code with Errors Marked
```python
{patched_code}
```

## Instructions
- Refer to API Documentation above for correct usage
- Replace each <<<<<<< [ERROR START: X] ... >>>>>>> [ERROR END: X] block with correct code
- Remove all marker lines (<<<<<<<, =======, >>>>>>>)
- Preserve all other code exactly
- Ensure the fixed code passes: {test_cases_summary}
"""


# Error types that use the simple prompt (non-logic errors)
SIMPLE_ERROR_TYPES = {
    "SYNTAX_ERROR",
    "UNDEFINED_NAME",
    "RUNTIME_ERROR",
    "API_ERROR",
    "MISSING_RETURN",
}


def _use_simple_prompt(patch: GeneratedPatch) -> bool:
    """Determine if all hunks are simple (non-logic) error types."""
    hunks = patch.get("hunks") or []
    if not hunks:
        return False
    return all(
        hunk.get("error_type") in SIMPLE_ERROR_TYPES
        for hunk in hunks
    )


def _get_primary_error_for_simple(
    apr_input: APRInput,
    patch: GeneratedPatch,
) -> tuple[int, str]:
    """Extract primary error line and message for simple prompt."""
    hunks = patch.get("hunks") or []
    if not hunks:
        return (1, "Unknown error")
    
    first_hunk = hunks[0]
    line = (first_hunk.get("location") or {}).get("line_start", 1)
    
    # Try to get message from various sources
    error_type = first_hunk.get("error_type", "")
    fix_suggestion = first_hunk.get("fix_suggestion")
    
    if fix_suggestion:
        message = fix_suggestion
    elif error_type == "SYNTAX_ERROR":
        message = (apr_input.get("static_ast") or {}).get("error_message") or "Syntax error"
    elif error_type in ("RUNTIME_ERROR", "UNDEFINED_NAME"):
        failure_details = (apr_input.get("dynamic_analysis") or {}).get("failure_details") or {}
        exc_msg = failure_details.get("exception_message")
        if exc_msg:
            message = exc_msg
        else:
            message = error_type.replace("_", " ").title()
    else:
        message = error_type.replace("_", " ").title()
    
    return (line, message)


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
    template: str | None = None,
    auto_select: bool = True,
    kg_engine: Optional[Any] = None,  # DSKGEngine
    kg_context_budget: int = 800,
) -> str:
    """
    Build the full repair prompt string for an LLM.
    
    If auto_select=True and template is None, automatically chooses:
    - REPAIR_PROMPT_ERROR_LINE for simple errors (syntax, runtime, name, API)
    - REPAIR_PROMPT_TEMPLATE for logic errors (wrong output)
    
    If kg_engine is provided, queries KG for relevant API documentation
    and uses KG-enhanced templates.
    
    Args:
        apr_input: Full APR input with code and analysis
        patch: Generated patch with error markers
        template: Override template (optional)
        auto_select: Auto-select template based on error types
        kg_engine: Optional DSKGEngine for API documentation
        kg_context_budget: Token budget for KG context (default 800)
    
    Returns:
        Formatted repair prompt string
    """
    # Query KG if available
    kg_context = ""
    if kg_engine is not None and KG_AVAILABLE:
        try:
            signatures = extract_error_signatures(apr_input, patch)
            kg_entries = query_kg_for_errors(kg_engine, signatures)
            if kg_entries:
                kg_context = build_kg_context(kg_entries, signatures, kg_context_budget)
        except Exception as e:
            # Gracefully fallback if KG query fails
            print(f"Warning: KG query failed: {e}")
            kg_context = ""
    
    # Select template
    if template is None and auto_select:
        use_simple = _use_simple_prompt(patch)
        
        # Use KG templates if we have context
        if kg_context:
            template = REPAIR_PROMPT_ERROR_LINE_WITH_KG if use_simple else REPAIR_PROMPT_TEMPLATE_WITH_KG
        else:
            template = REPAIR_PROMPT_ERROR_LINE if use_simple else REPAIR_PROMPT_TEMPLATE
    elif template is None:
        # Default to KG template if we have context
        template = REPAIR_PROMPT_TEMPLATE_WITH_KG if kg_context else REPAIR_PROMPT_TEMPLATE
    
    # Fill template placeholders
    if template in (REPAIR_PROMPT_ERROR_LINE, REPAIR_PROMPT_ERROR_LINE_WITH_KG):
        error_line, error_message = _get_primary_error_for_simple(apr_input, patch)
        if kg_context and template == REPAIR_PROMPT_ERROR_LINE_WITH_KG:
            return template.format(
                kg_context=kg_context,
                error_line=error_line,
                error_message=error_message,
                problem_description=apr_input.get("problem_description") or "",
                patched_code=patch.get("patched_code") or "",
            )
        else:
            return template.format(
                error_line=error_line,
                error_message=error_message,
                problem_description=apr_input.get("problem_description") or "",
                patched_code=patch.get("patched_code") or "",
            )
    else:
        # Full template
        if kg_context and template == REPAIR_PROMPT_TEMPLATE_WITH_KG:
            return template.format(
                kg_context=kg_context,
                problem_description=apr_input.get("problem_description") or "",
                function_signature=apr_input.get("function_signature") or "",
                patched_code=patch.get("patched_code") or "",
                test_cases_summary=format_test_cases(apr_input.get("test_cases")),
            )
        else:
            return template.format(
                problem_description=apr_input.get("problem_description") or "",
                function_signature=apr_input.get("function_signature") or "",
                patched_code=patch.get("patched_code") or "",
                test_cases_summary=format_test_cases(apr_input.get("test_cases")),
            )
