import ast
import re
from typing import Any, Dict, List, Optional

from .models import GeneratedTestCase, TestSpec


def _safe_literal_eval(raw: Any, fallback: Any) -> Any:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return fallback
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return fallback
    return raw if raw is not None else fallback


def _parse_mbpp_assert(expr: str) -> Optional[Dict[str, str]]:
    try:
        tree = ast.parse(expr.strip())
    except SyntaxError:
        return None
    if not tree.body or not isinstance(tree.body[0], ast.Assert):
        return None
    test = tree.body[0].test
    if not isinstance(test, ast.Compare):
        return None
    if len(test.ops) != 1 or len(test.comparators) != 1:
        return None
    if not isinstance(test.ops[0], ast.Eq):
        return None
    left = ast.unparse(test.left)
    right = ast.unparse(test.comparators[0])
    call_match = re.match(r"^\s*[A-Za-z_]\w*\((.*)\)\s*$", left)
    if not call_match:
        return None
    args_expr = call_match.group(1).strip()
    return {"args_expr": args_expr, "expected_repr": right}


def _extract_signature_name(signature: str) -> Optional[str]:
    match = re.search(r"def\s+([A-Za-z_]\w*)\s*\(", signature or "")
    return match.group(1) if match else None


def extract_mbpp_spec(row: Dict[str, Any], task_id: Any, code: str) -> TestSpec:
    entry_point = _extract_signature_name(str(row.get("function_signature", "")))
    raw_test_list = _safe_literal_eval(row.get("test_list", []), [])
    if isinstance(raw_test_list, str):
        raw_test_list = [raw_test_list]
    tests: List[GeneratedTestCase] = []
    for idx, raw_assert in enumerate(raw_test_list):
        if not isinstance(raw_assert, str):
            continue
        parsed = _parse_mbpp_assert(raw_assert)
        if not parsed:
            continue
        tests.append(
            GeneratedTestCase(
                case_id=f"orig_{idx}",
                code=raw_assert.strip(),
                expected_repr=parsed["expected_repr"],
                args_expr=parsed["args_expr"],
                input_repr=parsed["args_expr"],
                test_design_method="original",
                source="mbpp_test_list",
            )
        )
    return TestSpec(
        dataset="MBPP",
        task_id=task_id,
        entry_point=entry_point,
        code=code,
        prompt=str(row.get("prompt", "")),
        original_tests=tests,
        extra={"test_imports": _safe_literal_eval(row.get("test_imports", []), [])},
    )


def _extract_humaneval_asserts(test_block: str, entry_point: str) -> List[GeneratedTestCase]:
    try:
        tree = ast.parse(test_block or "")
    except SyntaxError:
        return []
    tests: List[GeneratedTestCase] = []
    idx = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        if not isinstance(node.test, ast.Compare):
            continue
        cmp_node = node.test
        if len(cmp_node.ops) != 1 or len(cmp_node.comparators) != 1:
            continue
        if not isinstance(cmp_node.ops[0], ast.Eq):
            continue
        left = ast.unparse(cmp_node.left)
        right = ast.unparse(cmp_node.comparators[0])
        prefix = f"candidate("
        if left.strip().startswith(prefix):
            args_expr = left.strip()[len(prefix):-1]
            call = f"{entry_point}({args_expr})"
        elif left.strip().startswith(f"{entry_point}("):
            args_expr = left[left.find("(") + 1:-1]
            call = left.strip()
        else:
            continue
        tests.append(
            GeneratedTestCase(
                case_id=f"orig_{idx}",
                code=f"assert {call} == {right}",
                expected_repr=right,
                args_expr=args_expr,
                input_repr=args_expr,
                test_design_method="original",
                source="humaneval_test_block",
            )
        )
        idx += 1
    return tests


def extract_humaneval_spec(row: Dict[str, Any], task_id: Any, code: str) -> TestSpec:
    entry_point = str(row.get("entry_point", "")).strip() or None
    tests = _extract_humaneval_asserts(str(row.get("test", "")), entry_point or "")
    return TestSpec(
        dataset="HumanEval",
        task_id=task_id,
        entry_point=entry_point,
        code=code,
        prompt=str(row.get("prompt", "")),
        original_tests=tests,
        extra={"test_block": str(row.get("test", ""))},
    )


def extract_ds1000_spec(row: Dict[str, Any], task_id: Any, code: str) -> TestSpec:
    metadata = _safe_literal_eval(row.get("metadata", "{}"), {})
    prompt = str(row.get("prompt", ""))
    code_context = str(row.get("code_context", ""))
    reference_code = str(row.get("reference_code", ""))
    return TestSpec(
        dataset="DS1000",
        task_id=task_id,
        entry_point="g",
        code=code,
        prompt=prompt,
        original_tests=[],
        extra={
            "metadata": metadata if isinstance(metadata, dict) else {},
            "code_context": code_context,
            "reference_code": reference_code,
            "test_case_cnt": (metadata or {}).get("test_case_cnt", 1) if isinstance(metadata, dict) else 1,
        },
    )
