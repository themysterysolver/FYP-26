import json
from typing import List, Tuple

from .models import GeneratedTestCase, TestSpec


def _json_case(test: GeneratedTestCase) -> str:
    payload = {
        "case_id": test.case_id,
        "stmt": test.code,
        "test_design_method": test.test_design_method,
        "equivalence_class": test.equivalence_class,
        "boundary_kind": test.boundary_kind,
        "input_repr": test.input_repr,
        "expected_repr": test.expected_repr,
        "source": test.source,
    }
    return json.dumps(payload, ensure_ascii=False)


def build_assert_harness(test_cases: List[GeneratedTestCase]) -> str:
    serialized = "[" + ",".join(_json_case(tc) for tc in test_cases) + "]"
    return """
import json
_cases = """ + serialized + """
_results = []
for _i, _case in enumerate(_cases):
    try:
        exec(_case["stmt"])
        _results.append({
            "test_id": _case["case_id"],
            "passed": True,
            "error": None,
            "output": None,
            "expected": _case.get("expected_repr"),
            "input": _case.get("input_repr"),
            "test_design_method": _case.get("test_design_method"),
            "equivalence_class": _case.get("equivalence_class"),
            "boundary_kind": _case.get("boundary_kind"),
            "generated_test_id": _case["case_id"],
            "source": _case.get("source"),
        })
    except AssertionError as _e:
        _results.append({
            "test_id": _case["case_id"],
            "passed": False,
            "error": str(_e) or "AssertionError",
            "output": None,
            "expected": _case.get("expected_repr"),
            "input": _case.get("input_repr"),
            "test_design_method": _case.get("test_design_method"),
            "equivalence_class": _case.get("equivalence_class"),
            "boundary_kind": _case.get("boundary_kind"),
            "generated_test_id": _case["case_id"],
            "source": _case.get("source"),
        })
    except Exception as _e:
        _results.append({
            "test_id": _case["case_id"],
            "passed": False,
            "error": f"{type(_e).__name__}: {_e}",
            "output": None,
            "expected": _case.get("expected_repr"),
            "input": _case.get("input_repr"),
            "test_design_method": _case.get("test_design_method"),
            "equivalence_class": _case.get("equivalence_class"),
            "boundary_kind": _case.get("boundary_kind"),
            "generated_test_id": _case["case_id"],
            "source": _case.get("source"),
        })
print(json.dumps(_results))
"""


def build_mbpp_oracle(spec: TestSpec, all_cases: List[GeneratedTestCase]) -> Tuple[str, str]:
    test_imports = spec.extra.get("test_imports", []) if spec.extra else []
    imports_block = ""
    if isinstance(test_imports, list):
        imports_block = "\n".join(str(i).strip() for i in test_imports if str(i).strip())
    script_prefix = imports_block
    harness = build_assert_harness(all_cases)
    return script_prefix, harness


def build_humaneval_oracle(spec: TestSpec, all_cases: List[GeneratedTestCase]) -> Tuple[str, str]:
    return "", build_assert_harness(all_cases)


def build_ds1000_oracle(spec: TestSpec) -> Tuple[str, str]:
    code_context = str(spec.extra.get("code_context", ""))
    if "generate_test_case" not in code_context or "exec_test" not in code_context:
        return "", ""
    test_case_cnt = spec.extra.get("test_case_cnt", 1)
    try:
        test_case_cnt = int(test_case_cnt)
    except (TypeError, ValueError):
        test_case_cnt = 1
    if test_case_cnt < 1:
        test_case_cnt = 1
    harness = """
import json
_results = []
for _tid in range(1, """ + str(test_case_cnt + 1) + """):
    try:
        _test_input, _ans = generate_test_case(_tid)
        _result = g(*_test_input)
        _ok = bool(exec_test(_result, _ans))
        _results.append({
            "test_id": f"orig_{_tid}",
            "passed": _ok,
            "error": None if _ok else "oracle_mismatch",
            "output": repr(_result),
            "expected": repr(_ans),
            "input": repr(_test_input),
            "test_design_method": "original",
            "equivalence_class": "dataset_oracle",
            "boundary_kind": None,
            "generated_test_id": f"orig_{_tid}",
            "source": "ds1000_code_context",
        })
    except Exception as _e:
        _results.append({
            "test_id": f"orig_{_tid}",
            "passed": False,
            "error": f"{type(_e).__name__}: {_e}",
            "output": None,
            "expected": None,
            "input": None,
            "test_design_method": "original",
            "equivalence_class": "dataset_oracle",
            "boundary_kind": None,
            "generated_test_id": f"orig_{_tid}",
            "source": "ds1000_code_context",
        })
print(json.dumps(_results))
"""
    return code_context, harness
