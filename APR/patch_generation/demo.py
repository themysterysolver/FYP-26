"""
Demonstrate successful execution of the PatchGenerator module.
Run from repo root: python -m APR.patch_generation.demo
Prints valid patch output to the terminal.
"""
from __future__ import annotations

import json
import os
import sys


def _logic_error_example() -> dict:
    """Example: find_max logic error (assertion_failure) - uses RICH prompt."""
    return {
        "task_id": "MBPP_37_logic",
        "generated_code": """def find_max(numbers):
    max_val = 0
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val""",
        "problem_description": "Return the maximum value in the list.",
        "function_signature": "def find_max(numbers):",
        "test_cases": [
            {
                "test_id": "t1",
                "input_expression": "find_max([1, 2, 3])",
                "expected_output": 3,
            },
            {
                "test_id": "t2",
                "input_expression": "find_max([-5, -2, -10])",
                "expected_output": -2,
            },
        ],
        "static_ast": {"status": "success"},
        "static_cfg": {"status": "success", "missing_return_paths": []},
        "static_library_api": {"status": "success"},
        "dynamic_analysis": {
            "status": "assertion_failure",
            "hallucination_type": "logic_error",
            "failure_details": {
                "failing_test_id": "t2",
                "expected_vs_actual": {
                    "expected": -2,
                    "actual": 0,
                    "diff_string": "Expected -2, got 0",
                },
            },
        },
    }


def _syntax_error_example() -> dict:
    """Example: syntax error (missing colon) - uses SIMPLE prompt."""
    return {
        "task_id": "SYNTAX_42",
        "generated_code": """def calculate_sum(numbers)
    total = 0
    for n in numbers:
        total += n
    return total""",
        "problem_description": "Calculate the sum of numbers in a list.",
        "function_signature": "def calculate_sum(numbers):",
        "test_cases": [
            {
                "test_id": "t1",
                "input_expression": "calculate_sum([1, 2, 3])",
                "expected_output": 6,
            },
        ],
        "static_ast": {
            "status": "syntax_error",
            "error_type": "SyntaxError",
            "error_message": "invalid syntax. Perhaps you forgot a comma?",
            "error_location": {"line_start": 1, "line_end": 1, "column_start": 28, "column_end": 28},
        },
        "static_cfg": {"status": "build_failure"},
        "static_library_api": {"status": "success"},
        "dynamic_analysis": {"status": "runtime_error"},
    }


def _run_example(name: str, apr_input: dict, generator) -> None:
    """Run one example and show the patch and prompt type."""
    from APR.patch_generation import build_repair_prompt, validate_patch
    
    request = {
        "apr_input": apr_input,
        "patch_strategy": {
            "mode": "multi_hunk",
            "error_focus": "hybrid",
            "include_suggestions": True,
        },
        "context_lines": 3,
    }
    
    patch = generator.generate(request)
    valid = validate_patch(patch)
    prompt = build_repair_prompt(apr_input, patch)
    
    print("\n" + "=" * 70)
    print(f"EXAMPLE: {name}")
    print("=" * 70)
    
    meta = patch.get("metadata") or {}
    hunks = patch.get("hunks") or []
    error_types = [h.get("error_type") for h in hunks]
    
    print(f"Task ID:        {patch.get('task_id')}")
    print(f"Validation:     {'PASS' if valid else 'FAIL'}")
    print(f"Strategy:       {meta.get('strategy_used')}")
    print(f"Total hunks:    {meta.get('total_hunks')}")
    print(f"Error types:    {', '.join(error_types)}")
    
    # Determine prompt type
    from APR.patch_generation.prompts import _use_simple_prompt
    prompt_type = "SIMPLE (error-line)" if _use_simple_prompt(patch) else "RICH (test I/O)"
    print(f"Prompt type:    {prompt_type}")
    print()
    
    print("--- Patched code (first 15 lines) ---")
    patched = patch.get("patched_code") or ""
    for i, line in enumerate(patched.split("\n")[:15], 1):
        print(f"  {i:2d}| {line}")
    print()
    
    print("--- Repair prompt (first 400 chars) ---")
    print(prompt[:400])
    if len(prompt) > 400:
        print(f"... ({len(prompt) - 400} more chars)")
    print()


def main() -> None:
    # Ensure we can import from APR
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from APR.patch_generation import PatchGenerator
    
    print("\n" + "=" * 70)
    print("HYBRID REPAIR PROMPT DEMONSTRATION")
    print("Showcasing simple prompt vs rich prompt based on error type")
    print("=" * 70)

    generator = PatchGenerator()
    
    # Example 1: Syntax error -> Simple prompt
    _run_example(
        "Syntax Error (uses SIMPLE prompt)",
        _syntax_error_example(),
        generator,
    )
    
    # Example 2: Logic error -> Rich prompt
    _run_example(
        "Logic Error (uses RICH prompt)",
        _logic_error_example(),
        generator,
    )
    
    print("\n" + "=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nKey differences:")
    print("  - SIMPLE: Short prompt with 'Error at line N: <message>'")
    print("  - RICH:   Full prompt with TEST/EXPECTED/ACTUAL and test summary")
    print()


if __name__ == "__main__":
    main()
