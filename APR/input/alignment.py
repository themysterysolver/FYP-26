"""
Alignment check: cross-validate static and dynamic detection results.
Produces AlignmentCheck with static_dynamic_agreement, checks, is_consistent, override_status.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .schema import (
    AlignmentCheck,
    ASTResult,
    CFGResult,
    DynamicResult,
    IndividualCheck,
    LibraryAPIResult,
)


def compute_alignment_check(
    static_ast: ASTResult,
    static_cfg: CFGResult,
    static_library_api: LibraryAPIResult,
    dynamic_analysis: DynamicResult,
) -> AlignmentCheck:
    """
    Compute alignment between static and dynamic results.
    When inconsistent, override_status is set to "use_dynamic" so APR prefers execution truth.
    """
    checks: List[IndividualCheck] = []

    ast_status = static_ast.get("status", "success")
    dyn_status = dynamic_analysis.get("status", "success")
    dyn_failure_details = dynamic_analysis.get("failure_details") or {}
    dyn_exception_msg = (dyn_failure_details.get("exception_message") or "") or ""

    # 1. syntax_agreement
    static_has_syntax_error = ast_status in ("syntax_error", "parse_failure")
    dynamic_parse_failure = dyn_status in ("runtime_error", "sandbox_failure") and (
        "syntaxerror" in dyn_exception_msg.lower() or "indentationerror" in dyn_exception_msg.lower()
    )
    syntax_agreement = static_has_syntax_error == dynamic_parse_failure
    checks.append({
        "check_name": "syntax_agreement",
        "passed": syntax_agreement,
        "static_claim": ast_status,
        "dynamic_claim": "parse_failure" if dynamic_parse_failure else "executed",
        "discrepancy": None if syntax_agreement else "syntax vs dynamic parse mismatch",
    })

    # 2. undefined_name_agreement
    ast_undefined = static_ast.get("undefined_names") or []
    dynamic_name_error = "nameerror" in dyn_exception_msg.lower()
    undefined_agreement = (len(ast_undefined) > 0) == dynamic_name_error
    checks.append({
        "check_name": "undefined_name_agreement",
        "passed": undefined_agreement,
        "static_claim": len(ast_undefined),
        "dynamic_claim": "NameError" if dynamic_name_error else "none",
        "discrepancy": None if undefined_agreement else "undefined names vs NameError mismatch",
    })

    # 3. api_error_agreement
    lib_nonexistent = static_library_api.get("nonexistent_apis") or []
    dynamic_api_error = (
        "attributeerror" in dyn_exception_msg.lower()
        or "modulenotfounderror" in dyn_exception_msg.lower()
        or "importerror" in dyn_exception_msg.lower()
    )
    api_agreement = (len(lib_nonexistent) > 0) == dynamic_api_error
    checks.append({
        "check_name": "api_error_agreement",
        "passed": api_agreement,
        "static_claim": len(lib_nonexistent),
        "dynamic_claim": "API error" if dynamic_api_error else "none",
        "discrepancy": None if api_agreement else "library API vs dynamic API error mismatch",
    })

    # 4. return_path_agreement
    cfg_missing_returns = static_cfg.get("missing_return_paths") or []
    dynamic_none_return = dyn_status == "assertion_failure" and (
        "none" in dyn_exception_msg.lower() or "nonetype" in dyn_exception_msg.lower()
    )
    return_agreement = (len(cfg_missing_returns) > 0) == dynamic_none_return
    checks.append({
        "check_name": "return_path_agreement",
        "passed": return_agreement,
        "static_claim": cfg_missing_returns,
        "dynamic_claim": "None/return issue" if dynamic_none_return else "none",
        "discrepancy": None if return_agreement else "missing return paths vs dynamic None mismatch",
    })

    # 5. hallucination_presence
    static_has_error = (
        ast_status != "success"
        or (static_cfg.get("status") != "success")
        or (static_library_api.get("status") == "api_errors_found")
    )
    dynamic_has_failure = dyn_status not in ("success",)
    hallucination_agreement = static_has_error == dynamic_has_failure
    checks.append({
        "check_name": "hallucination_presence",
        "passed": hallucination_agreement,
        "static_claim": "error" if static_has_error else "no_syntax_errors",
        "dynamic_claim": dyn_status,
        "discrepancy": None if hallucination_agreement else "static vs dynamic issue presence mismatch",
    })

    all_passed = all(c.get("passed", False) for c in checks)
    static_dynamic_agreement = all_passed
    is_consistent = all_passed
    override_status: str | None = None
    if not is_consistent:
        override_status = "use_dynamic"

    return {
        "static_dynamic_agreement": static_dynamic_agreement,
        "checks": checks,
        "is_consistent": is_consistent,
        "override_status": override_status,
        "ground_truth_match": None,
    }
