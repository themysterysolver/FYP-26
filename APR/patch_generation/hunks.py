"""
Hunk creation: build marked error regions for syntax, undefined names, logic, runtime, API, missing return.
"""
from __future__ import annotations

from typing import Any, List

from ..input.schema import (
    ASTResult,
    DiffInfo,
    NameErrorInfo,
    NonexistentAPI,
    SourceLocation,
    TestCase,
)
from .schema import Hunk


def _error_type_upper(label: str) -> str:
    """Normalize error type to UPPER_SNAKE_CASE."""
    return label.strip().upper().replace(" ", "_").replace("-", "_")


def create_syntax_hunk(
    code_lines: List[str],
    location: SourceLocation,
    ast_result: ASTResult,
    context_lines: int = 3,
) -> Hunk:
    """Mark unparseable code region with structural fix suggestion."""
    line_start = max(1, location.get("line_start", 1))
    line_end = min(len(code_lines), location.get("line_end", line_start))
    start_idx = max(0, line_start - 1)
    end_idx = min(len(code_lines), line_end)

    original = code_lines[start_idx:end_idx]
    ctx_before = code_lines[max(0, start_idx - context_lines) : start_idx]
    ctx_after = code_lines[end_idx : min(len(code_lines), end_idx + context_lines)]

    error_msg = (ast_result.get("error_message") or "syntax error").strip()
    col_start = location.get("column_start", 0)
    col_end = location.get("column_end", 0)

    fix_comment = f"# FIX: {error_msg}"
    fix_line_col = f"# Line {line_start}, column {col_start}"
    fix_hint = "# Check: missing colon, bracket mismatch, indentation"
    fix_placeholder = "pass  # TODO: Fix syntax error"

    marked_lines = [
        *ctx_before,
        "<<<<<<< [ERROR START: SYNTAX_ERROR]",
        *original,
        "=======",
        fix_comment,
        fix_line_col,
        fix_hint,
        fix_placeholder,
        ">>>>>>> [ERROR END: SYNTAX_ERROR]",
        *ctx_after,
    ]
    marked = "\n".join(marked_lines)

    return {
        "hunk_id": "hunk_syntax_0",
        "error_type": "SYNTAX_ERROR",
        "location": {
            "line_start": line_start,
            "line_end": line_end,
            "column_start": col_start,
            "column_end": col_end,
        },
        "original_lines": original,
        "marked_representation": marked,
        "severity": "critical",
        "fix_suggestion": f"Fix: {error_msg}",
    }


def create_undefined_name_hunk(
    code_lines: List[str],
    undefined: NameErrorInfo,
    include_suggestion: bool = True,
    context_lines: int = 3,
) -> Hunk:
    """Mark usage of undefined variable; suggest import or definition."""
    loc = undefined.get("location") or {}
    line_start = loc.get("line_start", 1)
    line_idx = max(0, line_start - 1)
    name = undefined.get("name", "?")

    original = [code_lines[line_idx]] if line_idx < len(code_lines) else ["# error line missing"]
    ctx_before = code_lines[max(0, line_idx - context_lines) : line_idx]
    ctx_after = code_lines[line_idx + 1 : min(len(code_lines), line_idx + context_lines + 1)]

    suggestion = undefined.get("suggestion") if include_suggestion else None
    fix_code = f"import {suggestion}" if suggestion else f"{name} = None  # TODO: Define"
    comment = f"# Undefined: '{name}'"
    if suggestion:
        comment += f", did you mean '{suggestion}'?"

    marked_lines = [
        *ctx_before,
        "<<<<<<< [ERROR START: UNDEFINED_NAME]",
        *original,
        "=======",
        comment,
        fix_code,
        ">>>>>>> [ERROR END: UNDEFINED_NAME]",
        *ctx_after,
    ]
    marked = "\n".join(marked_lines)

    return {
        "hunk_id": f"hunk_undef_{name}",
        "error_type": "UNDEFINED_NAME",
        "location": {
            "line_start": line_start,
            "line_end": line_start,
            "column_start": loc.get("column_start", 0),
            "column_end": loc.get("column_end", 0),
        },
        "original_lines": original,
        "marked_representation": marked,
        "severity": "critical",
        "fix_suggestion": suggestion,
    }


def create_logic_error_hunk(
    code_lines: List[str],
    error_line: int,
    hallucination_type: str,
    diff_info: DiffInfo | None,
    failing_test: TestCase | dict[str, Any] | None,
    context_lines: int = 3,
) -> Hunk:
    """Mark region causing wrong output; include test case in comment."""
    err_type = _error_type_upper(hallucination_type or "logic_error")
    line_idx = max(0, error_line - 1)
    loc = {
        "line_start": error_line,
        "line_end": error_line + 1,
        "column_start": 0,
        "column_end": len(code_lines[line_idx]) if line_idx < len(code_lines) else 0,
    }

    original = (
        [code_lines[line_idx]]
        if line_idx < len(code_lines)
        else ["# Error line not found"]
    )
    ctx_before = code_lines[max(0, line_idx - context_lines) : line_idx]
    ctx_after = code_lines[line_idx + 1 : min(len(code_lines), line_idx + context_lines + 1)]

    fix_lines = []
    if failing_test:
        inp = failing_test.get("input_expression") or failing_test.get("test_id", "")
        fix_lines.append(f"# TEST: {inp}")
    if diff_info:
        fix_lines.append(f"# EXPECTED: {diff_info.get('expected')}")
        fix_lines.append(f"# ACTUAL: {diff_info.get('actual')}")
        ds = (diff_info.get("diff_string") or "")[:100]
        if ds:
            fix_lines.append(f"# DIFF: {ds}")
    fix_lines.append(f"pass  # TODO: Fix {hallucination_type or 'logic_error'}")

    marked_lines = [
        *ctx_before,
        f"<<<<<<< [ERROR START: {err_type}]",
        *original,
        "=======",
        *fix_lines,
        f">>>>>>> [ERROR END: {err_type}]",
        *ctx_after,
    ]
    marked = "\n".join(marked_lines)

    return {
        "hunk_id": f"hunk_logic_{error_line}",
        "error_type": err_type,
        "location": loc,
        "original_lines": original,
        "marked_representation": marked,
        "severity": "major",
        "fix_suggestion": None,
    }


def create_runtime_error_hunk(
    code_lines: List[str],
    error_line: int,
    exception_type: str | None,
    exception_message: str | None,
    context_lines: int = 3,
) -> Hunk:
    """Mark region where runtime exception occurred."""
    line_idx = max(0, error_line - 1)
    loc = {
        "line_start": error_line,
        "line_end": error_line + 1,
        "column_start": 0,
        "column_end": len(code_lines[line_idx]) if line_idx < len(code_lines) else 0,
    }

    original = (
        [code_lines[line_idx]]
        if line_idx < len(code_lines)
        else ["# Error line not found"]
    )
    ctx_before = code_lines[max(0, line_idx - context_lines) : line_idx]
    ctx_after = code_lines[line_idx + 1 : min(len(code_lines), line_idx + context_lines + 1)]

    fix_lines = []
    if exception_type:
        fix_lines.append(f"# Exception: {exception_type}")
    if exception_message:
        fix_lines.append(f"# {exception_message[:200]}")
    fix_lines.append("pass  # TODO: Fix runtime error")

    marked_lines = [
        *ctx_before,
        "<<<<<<< [ERROR START: RUNTIME_ERROR]",
        *original,
        "=======",
        *fix_lines,
        ">>>>>>> [ERROR END: RUNTIME_ERROR]",
        *ctx_after,
    ]
    marked = "\n".join(marked_lines)

    return {
        "hunk_id": f"hunk_runtime_{error_line}",
        "error_type": "RUNTIME_ERROR",
        "location": loc,
        "original_lines": original,
        "marked_representation": marked,
        "severity": "critical",
        "fix_suggestion": exception_message,
    }


def create_api_error_hunk(
    code_lines: List[str],
    api_error: NonexistentAPI,
    context_lines: int = 3,
) -> Hunk:
    """Mark nonexistent or invalid API usage."""
    call = api_error.get("call") or {}
    loc = call.get("location") or {}
    line_start = loc.get("line_start", 1)
    line_idx = max(0, line_start - 1)
    lib = call.get("library", "?")
    method = call.get("method", "?")
    err_type = (api_error.get("error_type") or "attribute_error").upper().replace("-", "_")

    original = [code_lines[line_idx]] if line_idx < len(code_lines) else ["# error line missing"]
    ctx_before = code_lines[max(0, line_idx - context_lines) : line_idx]
    ctx_after = code_lines[line_idx + 1 : min(len(code_lines), line_idx + context_lines + 1)]

    suggestion = api_error.get("suggestion")
    fix_code = f"# Fix: {lib}.{method}" + (f" -> {suggestion}" if suggestion else "")

    marked_lines = [
        *ctx_before,
        f"<<<<<<< [ERROR START: API_ERROR]",
        *original,
        "=======",
        fix_code,
        "pass  # TODO: Fix API usage",
        ">>>>>>> [ERROR END: API_ERROR]",
        *ctx_after,
    ]
    marked = "\n".join(marked_lines)

    return {
        "hunk_id": f"hunk_api_{line_start}",
        "error_type": "API_ERROR",
        "location": {
            "line_start": line_start,
            "line_end": line_start,
            "column_start": loc.get("column_start", 0),
            "column_end": loc.get("column_end", 0),
        },
        "original_lines": original,
        "marked_representation": marked,
        "severity": "major",
        "fix_suggestion": suggestion,
    }


def create_missing_return_hunk(
    code_lines: List[str],
    function_name: str,
    insert_line: int,
    context_lines: int = 3,
) -> Hunk:
    """Mark location where a return is missing (best-effort; insert_line from heuristic)."""
    line_idx = max(0, insert_line - 1)
    loc = {
        "line_start": insert_line,
        "line_end": insert_line + 1,
        "column_start": 0,
        "column_end": 0,
    }

    original = (
        [code_lines[line_idx]]
        if line_idx < len(code_lines)
        else ["# end of function"]
    )
    ctx_before = code_lines[max(0, line_idx - context_lines) : line_idx]
    ctx_after = code_lines[line_idx + 1 : min(len(code_lines), line_idx + context_lines + 1)]

    marked_lines = [
        *ctx_before,
        "<<<<<<< [ERROR START: MISSING_RETURN]",
        *original,
        "=======",
        f"# Missing return in '{function_name}'",
        "return None  # TODO: Return correct value",
        ">>>>>>> [ERROR END: MISSING_RETURN]",
        *ctx_after,
    ]
    marked = "\n".join(marked_lines)

    return {
        "hunk_id": f"hunk_missing_return_{function_name}",
        "error_type": "MISSING_RETURN",
        "location": loc,
        "original_lines": original,
        "marked_representation": marked,
        "severity": "major",
        "fix_suggestion": f"Add return in {function_name}",
    }
