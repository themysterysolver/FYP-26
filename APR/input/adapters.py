"""
Adapters from current detection pipeline outputs (AST, CFG, LIB_API, dynamic)
to the APRInput spec types (ASTResult, CFGResult, LibraryAPIResult, DynamicResult).
"""
from __future__ import annotations

import ast
import json
from typing import Any, Dict, List


def _ensure_list(val: Any) -> List[Any]:
    """Parse CSV stringified list (e.g. '[]' or '[{...}]') to list."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return []
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        try:
            out = ast.literal_eval(s)
            return out if isinstance(out, list) else []
        except (ValueError, SyntaxError):
            pass
    return []

from .schema import (
    APICall,
    ASTResult,
    CFGResult,
    ComplexityMetrics,
    DiffInfo,
    DynamicResult,
    FailureDetails,
    LibraryAPIResult,
    NonexistentAPI,
    SourceLocation,
    TestResult,
)

# -----------------------------------------------------------------------------
# AST adapter
# -----------------------------------------------------------------------------


def _source_location(line: int, line_end: int | None = None, col_start: int = 0, col_end: int = 0) -> SourceLocation:
    return {
        "line_start": line,
        "line_end": line_end if line_end is not None else line,
        "column_start": col_start,
        "column_end": col_end,
    }


def current_ast_to_ast_result(record: Dict[str, Any], code: str | None = None) -> ASTResult:
    """Map current AST pipeline output to ASTResult."""
    ast_parsed = record.get("ast_parsed", False)
    error_type = record.get("error_type")
    line = record.get("line")
    message = record.get("message")

    if ast_parsed:
        status: str = "success"
        error_location = None
        ast_dump = None
        if code:
            try:
                import ast
                ast_dump = ast.dump(ast.parse(code))
            except Exception:
                pass
    else:
        if error_type in ("SyntaxError", "IndentationError", "TabError"):
            status = "syntax_error"
        else:
            status = "parse_failure"
        error_location = None
        if line is not None:
            error_location = _source_location(int(line))
        ast_dump = None

    return {
        "status": status,
        "error_type": error_type,
        "error_message": message,
        "error_location": error_location,
        "ast_dump": ast_dump,
        "function_defs": [],
        "undefined_names": [],
        "import_statements": [],
        "control_structures": [],
    }


# -----------------------------------------------------------------------------
# CFG adapter
# -----------------------------------------------------------------------------


def current_cfg_to_cfg_result(record: Dict[str, Any]) -> CFGResult:
    """Map current CFG pipeline output to CFGResult."""
    cfg_analyzed = record.get("cfg_analyzed", False)
    status = "success" if cfg_analyzed else "build_failure"

    unreachable_code: List[SourceLocation] = []
    missing_return_paths: List[str] = []

    for detail in _ensure_list(record.get("cfg_details")):
        if not isinstance(detail, dict):
            continue
        if detail.get("type") == "unreachable_code":
            unreachable_code.append(
                _source_location(
                    detail.get("start_line", 0),
                    detail.get("end_line"),
                )
            )
        elif detail.get("type") == "missing_return":
            fn = detail.get("function")
            if fn:
                missing_return_paths.append(fn)

    return {
        "status": status,
        "nodes": [],
        "edges": [],
        "unreachable_code": unreachable_code,
        "missing_return_paths": missing_return_paths,
        "infinite_loop_candidates": [],
        "complexity_metrics": {
            "cyclomatic_complexity": 0,
            "num_branches": 0,
            "num_loops": 0,
        },
    }


# -----------------------------------------------------------------------------
# Library API adapter
# -----------------------------------------------------------------------------


def current_libapi_to_library_api_result(record: Dict[str, Any]) -> LibraryAPIResult:
    """Map current LIB_API pipeline output to LibraryAPIResult."""
    libapi_details = _ensure_list(record.get("libapi_details"))
    total = record.get("total_libapi_errors", 0) or len(libapi_details)
    status = "api_errors_found" if total > 0 else "success"

    nonexistent_apis: List[NonexistentAPI] = []
    for err in libapi_details:
        if not isinstance(err, dict):
            continue
        line = err.get("line", 0)
        loc = _source_location(line) if line else {}
        t = err.get("type", "")
        if t == "module_not_found":
            error_type = "module_not_found"
            method = err.get("module", "?")
            library = (err.get("module") or "?").split(".")[0]
        elif t == "attribute_error":
            error_type = "attribute_error"
            library = err.get("object", "?")
            method = err.get("attribute", "?")
        elif t == "name_error":
            error_type = "attribute_error"
            library = "?"
            method = err.get("name", "?")
        elif t == "type_error":
            error_type = "no_such_method"
            library = "?"
            method = err.get("function", "?")
        else:
            error_type = "attribute_error"
            library = "?"
            method = "?"
        call: APICall = {"library": library, "method": method, "location": loc}
        nonexistent_apis.append({"call": call, "error_type": error_type, "suggestion": None})

    return {
        "status": status,
        "api_calls": [],
        "deprecated_apis": [],
        "nonexistent_apis": nonexistent_apis,
        "version_mismatches": [],
        "missing_required_args": [],
    }


# -----------------------------------------------------------------------------
# Dynamic adapter
# -----------------------------------------------------------------------------

# Map pipeline hallucination_subtype / error_type to spec hallucination_type
_HALLUCINATION_TYPE_MAP: Dict[str, str] = {
    "wrong_output": "logic_error",
    "undefined_name": "api_misuse",
    "type_mismatch": "type_mismatch",
    "boundary_violation": "off_by_one",
    "arithmetic_error": "logic_error",
    "runtime_error": "logic_error",
    "none": "none",
}


def _dynamic_status_to_spec(record: Dict[str, Any]) -> str:
    s = record.get("status", "crash")
    if s == "success":
        return "success" if record.get("valid") else "assertion_failure"
    if s == "timeout":
        return "timeout"
    if s == "resource_error":
        return "resource_exhaustion"
    if s in ("crash", "parse_error"):
        return "runtime_error"
    return "sandbox_failure"


def current_dynamic_to_dynamic_result(
    record: Dict[str, Any],
    test_case_ids: List[str] | None = None,
) -> DynamicResult:
    """Map current dynamic pipeline output to DynamicResult."""
    status = _dynamic_status_to_spec(record)
    failures: List[Dict[str, Any]] = record.get("failures", [])

    # Build test_results: passed tests + failed/error from failures
    test_results: List[TestResult] = []
    failed_ids = {f.get("test_id") for f in failures if f.get("test_id")}
    all_ids = list(test_case_ids) if test_case_ids else []
    for fid in failed_ids:
        if fid and fid not in all_ids:
            all_ids.append(fid)
    for tid in all_ids:
        fail = next((f for f in failures if f.get("test_id") == tid), None)
        if fail:
            tr_status = "error" if fail.get("type") == "exception" else "failed"
            test_results.append({
                "test_id": tid,
                "status": tr_status,
                "actual_output": fail.get("actual"),
                "stdout": None,
                "stderr": fail.get("message"),
                "execution_time_ms": 0.0,
            })
        else:
            test_results.append({
                "test_id": tid,
                "status": "passed",
                "actual_output": None,
                "stdout": None,
                "stderr": None,
                "execution_time_ms": 0.0,
            })

    failure_details: FailureDetails | None = None
    if failures:
        f0 = failures[0]
        failing_test_id = f0.get("test_id", "")
        exc_msg = f0.get("message")
        exc_type = None
        if exc_msg and ":" in str(exc_msg):
            exc_type = str(exc_msg).split(":", 1)[0].strip()
        expected_vs_actual = None
        if f0.get("type") == "wrong_output" or (f0.get("expected") is not None or f0.get("actual") is not None):
            expected_vs_actual = {
                "expected": f0.get("expected"),
                "actual": f0.get("actual"),
                "diff_string": f"{f0.get('expected')} vs {f0.get('actual')}",
            }
        failure_details = {
            "failing_test_id": failing_test_id,
            "exception_type": exc_type,
            "exception_message": exc_msg,
            "traceback": None,
            "expected_vs_actual": expected_vs_actual,
        }

    subtype = record.get("hallucination_subtype") or record.get("error_type") or "none"
    hallucination_type = _HALLUCINATION_TYPE_MAP.get(subtype, "logic_error")

    return {
        "status": status,
        "execution_time_ms": 0.0,
        "memory_usage_mb": None,
        "test_results": test_results,
        "failure_details": failure_details,
        "hallucination_type": hallucination_type,
    }
