import ast
from typing import Dict, List, Optional

from .models import GeneratedTestCase, TestSpec


def _value_kind(value_expr: str) -> str:
    try:
        value = ast.literal_eval(value_expr)
    except (ValueError, SyntaxError):
        return "unknown"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, tuple):
        return "tuple"
    if isinstance(value, dict):
        return "dict"
    return "unknown"


def _split_top_level_args(args_expr: str) -> List[str]:
    text = (args_expr or "").strip()
    if not text:
        return []
    out: List[str] = []
    depth = 0
    token = []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            part = "".join(token).strip()
            if part:
                out.append(part)
            token = []
            continue
        token.append(ch)
    last = "".join(token).strip()
    if last:
        out.append(last)
    return out


def infer_test_domains(spec: TestSpec) -> Dict[str, object]:
    samples: List[Dict[str, object]] = []
    for t in spec.original_tests:
        arg_parts = _split_top_level_args(t.args_expr)
        kinds = [_value_kind(a) for a in arg_parts]
        samples.append({"case_id": t.case_id, "arg_parts": arg_parts, "arg_kinds": kinds})
    arg_arity = 0
    if samples:
        arg_arity = len(samples[0]["arg_parts"])  # type: ignore[index]
    return {
        "dataset": spec.dataset,
        "entry_point": spec.entry_point,
        "arg_arity": arg_arity,
        "samples": samples,
        "has_original_tests": len(spec.original_tests) > 0,
    }


def classify_case_shape(test: GeneratedTestCase) -> Dict[str, Optional[str]]:
    parts = _split_top_level_args(test.args_expr)
    if not parts:
        return {"equivalence_class": "no_args", "boundary_kind": None}
    primary = parts[0]
    try:
        value = ast.literal_eval(primary)
    except (ValueError, SyntaxError):
        return {"equivalence_class": "opaque_input", "boundary_kind": None}

    if isinstance(value, (int, float)):
        if value == 0:
            return {"equivalence_class": "numeric_zero", "boundary_kind": "zero"}
        if abs(value) == 1:
            return {"equivalence_class": "numeric_unit", "boundary_kind": "unit"}
        return {"equivalence_class": "numeric_regular", "boundary_kind": None}
    if isinstance(value, str):
        if len(value) == 0:
            return {"equivalence_class": "string_empty", "boundary_kind": "empty"}
        if len(value) == 1:
            return {"equivalence_class": "string_single_char", "boundary_kind": "single"}
        return {"equivalence_class": "string_regular", "boundary_kind": None}
    if isinstance(value, (list, tuple, dict)):
        size = len(value)
        if size == 0:
            return {"equivalence_class": "collection_empty", "boundary_kind": "empty"}
        if size == 1:
            return {"equivalence_class": "collection_single", "boundary_kind": "single"}
        return {"equivalence_class": "collection_regular", "boundary_kind": None}
    return {"equivalence_class": "other_type", "boundary_kind": None}
