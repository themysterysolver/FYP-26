"""
APR module input type definitions (TypedDicts) and optional Parquet storage schema.
Matches the APRInput specification for fault localization, repair strategy, and verification.
"""
from __future__ import annotations

from typing import Any, List, Literal, Optional, TypedDict

# -----------------------------------------------------------------------------
# Source location (shared)
# -----------------------------------------------------------------------------


class SourceLocation(TypedDict, total=False):
    line_start: int  # 1-indexed
    line_end: int  # inclusive
    column_start: int  # 0-indexed
    column_end: int  # exclusive


# -----------------------------------------------------------------------------
# Test case (problem context)
# -----------------------------------------------------------------------------


class TestCase(TypedDict, total=False):
    test_id: str
    input_expression: str
    expected_output: Any
    comparison_mode: Literal["exact", "approx", "set", "sorted", "type_only"]
    is_edge_case: bool
    boundary_type: Optional[Literal["min", "max", "nominal", "robust"]]


# -----------------------------------------------------------------------------
# AST result
# -----------------------------------------------------------------------------


class FunctionDefInfo(TypedDict, total=False):
    name: str
    location: SourceLocation
    args: List[str]
    has_return: bool
    return_count: int


class NameErrorInfo(TypedDict, total=False):
    name: str
    location: SourceLocation
    suggestion: Optional[str]


class ImportInfo(TypedDict, total=False):
    module: str
    names: List[str]
    location: SourceLocation
    is_valid: bool


class ControlFlowNode(TypedDict, total=False):
    type: str  # "For", "While", "If", etc.
    location: SourceLocation


class ASTResult(TypedDict, total=False):
    status: Literal["success", "syntax_error", "parse_failure"]
    error_type: Optional[Literal["SyntaxError", "IndentationError", "TabError"]]
    error_message: Optional[str]
    error_location: Optional[SourceLocation]
    ast_dump: Optional[str]
    function_defs: List[FunctionDefInfo]
    undefined_names: List[NameErrorInfo]
    import_statements: List[ImportInfo]
    control_structures: List[ControlFlowNode]


# -----------------------------------------------------------------------------
# CFG result
# -----------------------------------------------------------------------------


class CFGNode(TypedDict, total=False):
    node_id: str
    location: SourceLocation
    statements: List[str]
    is_entry: bool
    is_exit: bool


class CFGEdge(TypedDict, total=False):
    from_node: str
    to_node: str
    condition: Optional[str]


class ComplexityMetrics(TypedDict, total=False):
    cyclomatic_complexity: int
    num_branches: int
    num_loops: int


class CFGResult(TypedDict, total=False):
    status: Literal["success", "build_failure"]
    nodes: List[CFGNode]
    edges: List[CFGEdge]
    unreachable_code: List[SourceLocation]
    missing_return_paths: List[str]
    infinite_loop_candidates: List[SourceLocation]
    complexity_metrics: ComplexityMetrics


# -----------------------------------------------------------------------------
# Library API result
# -----------------------------------------------------------------------------


class APICall(TypedDict, total=False):
    library: str
    method: str
    location: SourceLocation
    args_provided: List[str]
    kwargs_provided: List[str]


class DeprecatedAPI(TypedDict, total=False):
    call: APICall
    message: Optional[str]


class NonexistentAPI(TypedDict, total=False):
    call: APICall
    error_type: Literal["module_not_found", "attribute_error", "no_such_method"]
    suggestion: Optional[str]


class VersionMismatch(TypedDict, total=False):
    call: APICall
    message: Optional[str]


class MissingArg(TypedDict, total=False):
    call: APICall
    missing_param: str
    has_default: bool


class LibraryAPIResult(TypedDict, total=False):
    status: Literal["success", "api_errors_found"]
    api_calls: List[APICall]
    deprecated_apis: List[DeprecatedAPI]
    nonexistent_apis: List[NonexistentAPI]
    version_mismatches: List[VersionMismatch]
    missing_required_args: List[MissingArg]


# -----------------------------------------------------------------------------
# Dynamic result
# -----------------------------------------------------------------------------


class TestResult(TypedDict, total=False):
    test_id: str
    status: Literal["passed", "failed", "error", "timeout"]
    actual_output: Any
    stdout: Optional[str]
    stderr: Optional[str]
    execution_time_ms: float


class DiffInfo(TypedDict, total=False):
    expected: Any
    actual: Any
    diff_string: str


class FailureDetails(TypedDict, total=False):
    failing_test_id: str
    exception_type: Optional[str]
    exception_message: Optional[str]
    traceback: Optional[List[str]]
    expected_vs_actual: Optional[DiffInfo]


class DynamicResult(TypedDict, total=False):
    status: Literal[
        "success",
        "runtime_error",
        "assertion_failure",
        "timeout",
        "resource_exhaustion",
        "sandbox_failure",
    ]
    execution_time_ms: float
    memory_usage_mb: Optional[float]
    test_results: List[TestResult]
    failure_details: Optional[FailureDetails]
    hallucination_type: Optional[
        Literal[
            "none",
            "logic_error",
            "off_by_one",
            "type_mismatch",
            "api_misuse",
            "missing_edge_case",
            "infinite_loop",
            "resource_leak",
        ]
    ]


# -----------------------------------------------------------------------------
# Alignment check
# -----------------------------------------------------------------------------


class IndividualCheck(TypedDict, total=False):
    check_name: str
    passed: bool
    static_claim: Any
    dynamic_claim: Any
    discrepancy: Optional[str]


class AlignmentCheck(TypedDict, total=False):
    static_dynamic_agreement: bool
    checks: List[IndividualCheck]
    is_consistent: bool
    override_status: Optional[Literal["use_static", "use_dynamic", "manual_review"]]
    ground_truth_match: Optional[bool]


# -----------------------------------------------------------------------------
# Top-level APR input
# -----------------------------------------------------------------------------


class APRInput(TypedDict, total=False):
    task_id: str
    generated_code: str
    canonical_solution: Optional[str]
    problem_description: str
    function_signature: str
    test_cases: List[TestCase]
    static_ast: ASTResult
    static_cfg: CFGResult
    static_library_api: LibraryAPIResult
    dynamic_analysis: DynamicResult
    alignment_check: AlignmentCheck
    source_dataset: Literal["MBPP", "HumanEval", "DS-1000"]
    timestamp: str
    detector_version: str


# -----------------------------------------------------------------------------
# Parquet storage schema (nested structs as JSON strings for simplicity)
# -----------------------------------------------------------------------------

try:
    import pyarrow as pa
    APR_INPUT_PARQUET_SCHEMA = pa.schema([
        ("task_id", pa.string()),
        ("generated_code", pa.string()),
        ("canonical_solution", pa.string()),
        ("problem_description", pa.string()),
        ("function_signature", pa.string()),
        ("test_cases", pa.string()),  # JSON-serialized list of TestCase
        ("static_ast", pa.string()),
        ("static_cfg", pa.string()),
        ("static_library_api", pa.string()),
        ("dynamic_analysis", pa.string()),
        ("alignment_check", pa.string()),
        ("source_dataset", pa.string()),
        ("timestamp", pa.string()),
        ("detector_version", pa.string()),
    ])
except ImportError:
    APR_INPUT_PARQUET_SCHEMA = None
