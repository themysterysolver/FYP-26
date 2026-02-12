"""
Demonstrate successful execution of the PatchGenerator module.
Run from repo root: python -m APR.patch_generation.demo
Prints valid patch output to the terminal.
"""
from __future__ import annotations

import json
import os
import sys


def _spec_example_apr_input() -> dict:
    """Spec example: find_max logic error (assertion_failure)."""
    return {
        "task_id": "MBPP_37",
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


def main() -> None:
    # Ensure we can import from APR
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from APR.patch_generation import (
        PatchGenerator,
        build_repair_prompt,
        validate_patch,
    )

    # Use spec example so we always have a dynamic hunk
    apr_input = _spec_example_apr_input()
    request: PatchGenerationRequest = {
        "apr_input": apr_input,
        "patch_strategy": {
            "mode": "multi_hunk",
            "error_focus": "hybrid",
            "include_suggestions": True,
        },
        "context_lines": 3,
    }

    generator = PatchGenerator()
    patch = generator.generate(request)
    valid = validate_patch(patch)

    print("=" * 60)
    print("PatchGenerator module – execution demo")
    print("=" * 60)
    print(f"Validation: {'PASS' if valid else 'FAIL'}")
    print(f"patch_id:   {patch.get('patch_id')}")
    print(f"task_id:    {patch.get('task_id')}")
    meta = patch.get("metadata") or {}
    print(f"strategy:   {meta.get('strategy_used')}")
    print(f"total_hunks: {meta.get('total_hunks')}")
    print(f"critical_hunks: {meta.get('critical_hunks')}")
    print()
    print("--- Patched code (snippet) ---")
    patched = patch.get("patched_code") or ""
    lines = patched.split("\n")
    for i, line in enumerate(lines[:25], 1):
        print(f"  {i:2d}| {line}")
    if len(lines) > 25:
        print(f"  ... ({len(lines) - 25} more lines)")
    print()
    hunks = patch.get("hunks") or []
    if hunks:
        print("--- First hunk marked_representation ---")
        first = hunks[0]
        mr = first.get("marked_representation", "")
        for line in mr.split("\n")[:20]:
            print(f"  {line}")
        if len(mr.split("\n")) > 20:
            print("  ...")
    print()
    print("Repair prompt length:", len(build_repair_prompt(apr_input, patch)))
    print("=" * 60)
    print("Demo finished successfully.")


if __name__ == "__main__":
    main()
