"""
Patch generation strategies: static-first, dynamic-first, hybrid.
"""
from __future__ import annotations

from typing import List

from ..input.schema import APRInput
from .hunks import (
    create_api_error_hunk,
    create_logic_error_hunk,
    create_missing_return_hunk,
    create_runtime_error_hunk,
    create_syntax_hunk,
    create_undefined_name_hunk,
)
from .schema import GeneratedPatch, Hunk, PatchGenerationRequest
from .utils import (
    build_patch,
    estimate_error_line,
    find_function_end_line,
    localize_error_by_traceback,
    strip_markdown_fences,
)


def generate_static_first_patch(request: PatchGenerationRequest) -> GeneratedPatch:
    """
    Prioritize static analysis errors. One hunk per error type,
    ordered by severity: syntax > undefined > import > logic.
    """
    apr = request["apr_input"]
    strategy = request.get("patch_strategy") or {}
    context_lines = request.get("context_lines", 3)
    include_suggestions = strategy.get("include_suggestions", True)

    code = strip_markdown_fences(apr.get("generated_code") or "")
    code_lines = code.split("\n")
    hunks: List[Hunk] = []

    static_ast = apr.get("static_ast") or {}
    static_cfg = apr.get("static_cfg") or {}
    static_lib = apr.get("static_library_api") or {}
    dynamic = apr.get("dynamic_analysis") or {}

    # 1. Syntax errors (critical - return immediately)
    if static_ast.get("status") == "syntax_error":
        loc = static_ast.get("error_location")
        if loc:
            hunk = create_syntax_hunk(code_lines, loc, static_ast, context_lines)
            hunks.append(hunk)
        return build_patch(apr, hunks, "syntax_error_found")

    # 2. Undefined names
    for undefined in static_ast.get("undefined_names") or []:
        hunk = create_undefined_name_hunk(
            code_lines,
            undefined,
            include_suggestion=include_suggestions,
            context_lines=context_lines,
        )
        hunks.append(hunk)

    # 3. Missing returns (heuristic: find function end line)
    for fn_name in static_cfg.get("missing_return_paths") or []:
        insert_line = find_function_end_line(code_lines, fn_name)
        if insert_line is not None:
            hunk = create_missing_return_hunk(
                code_lines, fn_name, insert_line, context_lines
            )
            hunks.append(hunk)

    # 4. API errors
    for api_err in static_lib.get("nonexistent_apis") or []:
        hunk = create_api_error_hunk(code_lines, api_err, context_lines)
        hunks.append(hunk)

    # 5. Dynamic fallback when no static hunks
    if not hunks and dynamic.get("status") != "success":
        hunk = _one_dynamic_hunk(apr, code_lines, context_lines)
        if hunk:
            hunks.append(hunk)

    return build_patch(apr, hunks, "static_first_complete")


def generate_dynamic_first_patch(request: PatchGenerationRequest) -> GeneratedPatch:
    """
    Use dynamic analysis failure to guide patching.
    Creates hunks around failing test execution paths.
    """
    apr = request["apr_input"]
    context_lines = request.get("context_lines", 3)
    code = strip_markdown_fences(apr.get("generated_code") or "")
    code_lines = code.split("\n")
    hunks: List[Hunk] = []

    dynamic = apr.get("dynamic_analysis") or {}
    status = dynamic.get("status")
    failure = dynamic.get("failure_details") or {}
    test_cases = apr.get("test_cases") or []
    hallucination_type = dynamic.get("hallucination_type") or "logic_error"

    if status == "assertion_failure":
        failing_test_id = failure.get("failing_test_id")
        failing_test = next(
            (t for t in test_cases if t.get("test_id") == failing_test_id),
            None,
        )
        if not failing_test and test_cases:
            failing_test = test_cases[0]
        expected_vs_actual = failure.get("expected_vs_actual")
        traceback = failure.get("traceback")
        error_line = localize_error_by_traceback(
            code_lines, traceback, failing_test
        )
        hunk = create_logic_error_hunk(
            code_lines,
            error_line,
            hallucination_type,
            expected_vs_actual,
            failing_test,
            context_lines,
        )
        hunks.append(hunk)
    elif status == "runtime_error":
        traceback = failure.get("traceback") or []
        error_line = (
            localize_error_by_traceback(code_lines, traceback, None)
            if traceback
            else estimate_error_line(code_lines, dynamic)
        )
        hunk = create_runtime_error_hunk(
            code_lines,
            error_line,
            failure.get("exception_type"),
            failure.get("exception_message"),
            context_lines,
        )
        hunks.append(hunk)

    return build_patch(apr, hunks, "dynamic_first_complete")


def generate_hybrid_patch(request: PatchGenerationRequest) -> GeneratedPatch:
    """
    Static-first, then append one dynamic hunk if dynamic_analysis failed.
    """
    apr = request["apr_input"]
    strategy = request.get("patch_strategy") or {}
    context_lines = request.get("context_lines", 3)
    include_suggestions = strategy.get("include_suggestions", True)

    code = strip_markdown_fences(apr.get("generated_code") or "")
    code_lines = code.split("\n")
    hunks: List[Hunk] = []

    static_ast = apr.get("static_ast") or {}
    static_cfg = apr.get("static_cfg") or {}
    static_lib = apr.get("static_library_api") or {}
    dynamic = apr.get("dynamic_analysis") or {}

    # 1. Syntax: return immediately
    if static_ast.get("status") == "syntax_error":
        loc = static_ast.get("error_location")
        if loc:
            hunks.append(
                create_syntax_hunk(code_lines, loc, static_ast, context_lines)
            )
        return build_patch(apr, hunks, "hybrid_syntax_error")

    # 2–4. Static hunks
    for undefined in static_ast.get("undefined_names") or []:
        hunks.append(
            create_undefined_name_hunk(
                code_lines,
                undefined,
                include_suggestion=include_suggestions,
                context_lines=context_lines,
            )
        )
    for fn_name in static_cfg.get("missing_return_paths") or []:
        insert_line = find_function_end_line(code_lines, fn_name)
        if insert_line is not None:
            hunks.append(
                create_missing_return_hunk(
                    code_lines, fn_name, insert_line, context_lines
                )
            )
    for api_err in static_lib.get("nonexistent_apis") or []:
        hunks.append(create_api_error_hunk(code_lines, api_err, context_lines))

    # 5. Dynamic add-on when status != success
    if dynamic.get("status") != "success":
        dyn_hunk = _one_dynamic_hunk(apr, code_lines, context_lines)
        if dyn_hunk:
            hunks.append(dyn_hunk)

    return build_patch(apr, hunks, "hybrid_complete")


def _one_dynamic_hunk(
    apr: APRInput,
    code_lines: List[str],
    context_lines: int,
) -> Hunk | None:
    """Produce a single dynamic hunk from dynamic_analysis."""
    dynamic = apr.get("dynamic_analysis") or {}
    status = dynamic.get("status")
    failure = dynamic.get("failure_details") or {}
    test_cases = apr.get("test_cases") or []
    hallucination_type = dynamic.get("hallucination_type") or "logic_error"

    if status == "assertion_failure":
        failing_test_id = failure.get("failing_test_id")
        failing_test = next(
            (t for t in test_cases if t.get("test_id") == failing_test_id),
            None,
        )
        if not failing_test and test_cases:
            failing_test = test_cases[0]
        expected_vs_actual = failure.get("expected_vs_actual")
        traceback = failure.get("traceback")
        error_line = localize_error_by_traceback(
            code_lines, traceback, failing_test
        )
        return create_logic_error_hunk(
            code_lines,
            error_line,
            hallucination_type,
            expected_vs_actual,
            failing_test,
            context_lines,
        )
    if status == "runtime_error":
        traceback = failure.get("traceback") or []
        error_line = (
            localize_error_by_traceback(code_lines, traceback, None)
            if traceback
            else estimate_error_line(code_lines, dynamic)
        )
        return create_runtime_error_hunk(
            code_lines,
            error_line,
            failure.get("exception_type"),
            failure.get("exception_message"),
            context_lines,
        )
    return None
