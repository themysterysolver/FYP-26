import ast
from typing import List

from .domain_inference import classify_case_shape
from .models import GeneratedTestCase, TestSpec


def _mutate_literal(expr: str, mode: str) -> str:
    try:
        value = ast.literal_eval(expr)
    except (ValueError, SyntaxError):
        return expr

    if isinstance(value, bool):
        return repr(not value)
    if isinstance(value, int):
        if mode == "bva_low":
            return repr(value - 1)
        if mode == "bva_high":
            return repr(value + 1)
        return repr(value)
    if isinstance(value, float):
        if mode == "bva_low":
            return repr(value - 0.001)
        if mode == "bva_high":
            return repr(value + 0.001)
        return repr(value)
    if isinstance(value, str):
        if mode == "bva_low":
            return repr("")
        if mode == "bva_high":
            return repr(value + "x")
        if mode == "ecp_invalid":
            return repr(None)
        return repr(value)
    if isinstance(value, list):
        if mode == "bva_low":
            return repr([])
        if mode == "bva_high":
            return repr(value + value[:1])
        if mode == "ecp_invalid":
            return repr(None)
        return repr(value)
    if isinstance(value, tuple):
        if mode == "bva_low":
            return repr(())
        if mode == "bva_high":
            return repr(value + value[:1])
        if mode == "ecp_invalid":
            return repr(None)
        return repr(value)
    if isinstance(value, dict):
        if mode == "bva_low":
            return repr({})
        if mode == "bva_high":
            copied = dict(value)
            copied["__extra__"] = 1
            return repr(copied)
        if mode == "ecp_invalid":
            return repr(None)
        return repr(value)
    return expr


def _replace_first_arg(args_expr: str, new_first_arg: str) -> str:
    text = args_expr.strip()
    if not text:
        return new_first_arg
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return f"{new_first_arg}, {text[i + 1:].strip()}"
        i += 1
    return new_first_arg


def _build_case_from_base(
    spec: TestSpec,
    base: GeneratedTestCase,
    case_id: str,
    mode: str,
    test_design_method: str,
    equivalence_class: str,
    boundary_kind: str,
) -> GeneratedTestCase:
    first_arg = base.args_expr.split(",", 1)[0].strip()
    mutated_first = _mutate_literal(first_arg, mode)
    new_args = _replace_first_arg(base.args_expr, mutated_first)
    call = f"{spec.entry_point}({new_args})"
    code = f"assert {call} == {base.expected_repr}"
    return GeneratedTestCase(
        case_id=case_id,
        code=code,
        expected_repr=base.expected_repr,
        args_expr=new_args,
        input_repr=new_args,
        test_design_method=test_design_method,
        equivalence_class=equivalence_class,
        boundary_kind=boundary_kind,
        source="generated",
    )


def generate_bva_tests(spec: TestSpec) -> List[GeneratedTestCase]:
    if not spec.entry_point:
        return []
    generated: List[GeneratedTestCase] = []
    for idx, base in enumerate(spec.original_tests[:3]):
        shape = classify_case_shape(base)
        eq_class = shape["equivalence_class"] or "derived_boundary"
        generated.append(
            _build_case_from_base(
                spec=spec,
                base=base,
                case_id=f"bva_{idx}_low",
                mode="bva_low",
                test_design_method="bva",
                equivalence_class=eq_class,
                boundary_kind="low",
            )
        )
        generated.append(
            _build_case_from_base(
                spec=spec,
                base=base,
                case_id=f"bva_{idx}_high",
                mode="bva_high",
                test_design_method="bva",
                equivalence_class=eq_class,
                boundary_kind="high",
            )
        )
    return generated


def generate_ecp_tests(spec: TestSpec) -> List[GeneratedTestCase]:
    if not spec.entry_point:
        return []
    generated: List[GeneratedTestCase] = []
    for idx, base in enumerate(spec.original_tests[:2]):
        generated.append(
            _build_case_from_base(
                spec=spec,
                base=base,
                case_id=f"ecp_{idx}_invalid",
                mode="ecp_invalid",
                test_design_method="ecp",
                equivalence_class="invalid_input_class",
                boundary_kind=None,
            )
        )
    return generated
