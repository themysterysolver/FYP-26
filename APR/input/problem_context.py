"""
Build problem context (problem_description, function_signature, test_cases, canonical_solution)
from generation CSV rows for MBPP, HumanEval, and DS-1000.
"""
from __future__ import annotations

import ast
import os
import sys
from typing import Any, Dict, List

from .schema import TestCase

# Allow importing from Hallucination detection/dynamic/test_generation
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DYNAMIC_DIR = os.path.join(_PROJECT_ROOT, "Hallucination detection", "dynamic")
if _DYNAMIC_DIR not in sys.path:
    sys.path.insert(0, _DYNAMIC_DIR)

try:
    from test_generation.spec_extraction import (
        extract_ds1000_spec,
        extract_humaneval_spec,
        extract_mbpp_spec,
    )
except ImportError:
    extract_mbpp_spec = None
    extract_humaneval_spec = None
    extract_ds1000_spec = None


def _normalize(s: str) -> str:
    return (s or "").strip()


def _expected_from_repr(repr_str: str) -> Any:
    """Best-effort parse expected_repr to a Python value for expected_output."""
    s = (repr_str or "").strip()
    if not s:
        return None
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return s


def _boundary_to_spec(boundary_kind: Any) -> str | None:
    if not boundary_kind or not isinstance(boundary_kind, str):
        return None
    k = boundary_kind.lower()
    if k in ("min", "max", "nominal", "robust"):
        return k
    return None


def build_test_cases_mbpp(row: Dict[str, Any], task_id: Any, code: str) -> List[TestCase]:
    if not extract_mbpp_spec:
        return []
    spec = extract_mbpp_spec(row, task_id, code)
    entry = spec.entry_point or "fn"
    cases: List[TestCase] = []
    for t in spec.original_tests:
        input_expr = f"{entry}({t.args_expr})" if t.args_expr else f"{entry}()"
        cases.append({
            "test_id": t.case_id,
            "input_expression": input_expr,
            "expected_output": _expected_from_repr(t.expected_repr),
            "comparison_mode": "exact",
            "is_edge_case": (t.test_design_method or "original") != "original",
            "boundary_type": _boundary_to_spec(t.boundary_kind),
        })
    return cases


def build_test_cases_humaneval(row: Dict[str, Any], task_id: Any, code: str) -> List[TestCase]:
    if not extract_humaneval_spec:
        return []
    spec = extract_humaneval_spec(row, task_id, code)
    entry = spec.entry_point or "fn"
    cases: List[TestCase] = []
    for t in spec.original_tests:
        input_expr = f"{entry}({t.args_expr})" if t.args_expr else f"{entry}()"
        cases.append({
            "test_id": t.case_id,
            "input_expression": input_expr,
            "expected_output": _expected_from_repr(t.expected_repr),
            "comparison_mode": "exact",
            "is_edge_case": (t.test_design_method or "original") != "original",
            "boundary_type": _boundary_to_spec(t.boundary_kind),
        })
    return cases


def build_test_cases_ds1000(row: Dict[str, Any], task_id: Any, code: str) -> List[TestCase]:
    if not extract_ds1000_spec:
        return []
    spec = extract_ds1000_spec(row, task_id, code)
    extra = spec.extra or {}
    test_case_cnt = extra.get("test_case_cnt", 1)
    try:
        test_case_cnt = int(test_case_cnt)
    except (TypeError, ValueError):
        test_case_cnt = 1
    if test_case_cnt < 1:
        test_case_cnt = 1
    cases: List[TestCase] = []
    for tid in range(1, test_case_cnt + 1):
        cases.append({
            "test_id": f"orig_{tid}",
            "input_expression": f"g(*_test_input)",
            "expected_output": None,
            "comparison_mode": "exact",
            "is_edge_case": False,
            "boundary_type": None,
        })
    return cases


def build_problem_context(
    source_dataset: str,
    row: Dict[str, Any],
    task_id: Any,
    code: str,
    canonical_solution: str | None,
) -> Dict[str, Any]:
    """
    Build problem_description, function_signature, test_cases for one sample.
    Returns dict with keys: problem_description, function_signature, test_cases.
    canonical_solution is passed through by the caller; not computed here.
    """
    problem_description = _normalize(str(row.get("prompt", "")))
    test_cases: List[TestCase] = []

    if source_dataset == "MBPP":
        function_signature = str(row.get("function_signature", "")).strip() or "def fn():"
        test_cases = build_test_cases_mbpp(row, task_id, code)
    elif source_dataset == "HumanEval":
        ep = str(row.get("entry_point", "")).strip()
        function_signature = f"def {ep}():" if ep else "def fn():"
        test_cases = build_test_cases_humaneval(row, task_id, code)
    elif source_dataset in ("DS1000", "DS-1000"):
        function_signature = "def g(*args):"
        test_cases = build_test_cases_ds1000(row, task_id, code)
    else:
        function_signature = "def fn():"

    if not function_signature.strip():
        function_signature = "def fn():"

    return {
        "problem_description": problem_description,
        "function_signature": function_signature,
        "test_cases": test_cases,
    }


def get_canonical_solution(source_dataset: str, row: Dict[str, Any]) -> str | None:
    """Get canonical solution string from row by dataset."""
    if source_dataset == "MBPP":
        return _normalize(str(row.get("code", ""))) or None
    if source_dataset == "HumanEval":
        return _normalize(str(row.get("canonical_solution", ""))) or None
    if source_dataset in ("DS1000", "DS-1000"):
        return _normalize(str(row.get("reference_code", ""))) or None
    return None


def get_generated_code(source_dataset: str, row: Dict[str, Any]) -> str:
    """Get raw generated code from row by dataset."""
    if source_dataset in ("DS1000", "DS-1000"):
        return str(row.get("full_code", ""))
    return str(row.get("GENERATED_CODE", ""))
