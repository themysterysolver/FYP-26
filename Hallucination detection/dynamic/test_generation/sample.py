"""
Cross-dataset BVA/ECP showcase.

Runs on:
- Code generation/Qwen/ds1k_gen.csv
- Code generation/Qwen/humaneval_gen.csv
- Code generation/Qwen/mbpp_gen.csv

Usage:
    .venv/bin/python "Hallucination detection/dynamic/test_generation/sample.py"
    .venv/bin/python "Hallucination detection/dynamic/test_generation/sample.py" --limit 2
"""

import argparse
import ast
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from test_generation.case_generation import generate_bva_tests, generate_ecp_tests
from test_generation.models import GeneratedTestCase, TestSpec
from test_generation.oracle_emission import build_assert_harness, build_ds1000_oracle, build_humaneval_oracle, build_mbpp_oracle
from test_generation.spec_extraction import extract_ds1000_spec, extract_humaneval_spec, extract_mbpp_spec


def _extract_code(code: str) -> str:
    if not code or not isinstance(code, str):
        return (code or "").strip()
    if "```python" in code:
        return code.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in code:
        return code.split("```", 1)[1].split("```", 1)[0].strip()
    return code.strip()


def _execute_in_sandbox(code: str, script_prefix: str, harness: str, timeout: int = 8) -> Dict[str, Any]:
    full_script = (script_prefix or "") + "\n\n" + _extract_code(code) + "\n\n" + harness
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(full_script)
            temp_path = handle.name
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(temp_path),
        )
        if proc.returncode != 0:
            return {"status": "crash", "stderr": proc.stderr, "stdout": proc.stdout, "results": []}
        out = (proc.stdout or "").strip().split("\n")
        payload = json.loads(out[-1]) if out else []
        if not isinstance(payload, list):
            return {"status": "parse_error", "raw": out[-1] if out else "", "results": []}
        return {"status": "success", "results": payload}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "results": []}
    except Exception as exc:  # noqa: BLE001
        return {"status": "driver_error", "error": f"{type(exc).__name__}: {exc}", "results": []}
    finally:
        if temp_path and os.path.isfile(temp_path):
            os.unlink(temp_path)


def _read_rows(path: str, limit: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            if idx >= limit:
                break
            rows.append(row)
    return rows


def _fallback_mbpp_tests(raw_test_list: str) -> List[GeneratedTestCase]:
    text = str(raw_test_list or "")
    if not text:
        return []
    candidates = [line.strip(" '\"") for line in text.replace("\\n", "\n").split("\n")]
    out: List[GeneratedTestCase] = []
    idx = 0
    for line in candidates:
        if not line.startswith("assert "):
            continue
        try:
            node = ast.parse(line).body[0]
            if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
                continue
            if len(node.test.ops) != 1 or len(node.test.comparators) != 1:
                continue
            if not isinstance(node.test.ops[0], ast.Eq):
                continue
            left = ast.unparse(node.test.left)
            right = ast.unparse(node.test.comparators[0])
            match = re.match(r"^[A-Za-z_]\w*\((.*)\)$", left.strip())
            args_expr = match.group(1) if match else ""
            out.append(
                GeneratedTestCase(
                    case_id=f"orig_fb_{idx}",
                    code=line,
                    expected_repr=right,
                    args_expr=args_expr,
                    input_repr=args_expr,
                    test_design_method="original",
                    source="mbpp_fallback",
                )
            )
            idx += 1
        except Exception:  # noqa: BLE001
            continue
    return out


def _pick_useful_rows(dataset: str, rows: List[Dict[str, Any]], target: int) -> List[Tuple[int, Dict[str, Any]]]:
    picked_success: List[Tuple[int, Dict[str, Any]]] = []
    picked_fallback: List[Tuple[int, Dict[str, Any]]] = []
    for idx, row in enumerate(rows):
        code, prefix, harness, task_id, generated_counts = _prepare_oracle(dataset, row, idx)
        if dataset == "DS1000":
            useful = bool(harness)
        else:
            useful = (generated_counts["original"] + generated_counts["bva"] + generated_counts["ecp"]) > 0
        if not useful:
            continue

        # Prefer rows that actually execute so output is meaningful.
        probe_result = {"status": "no_tests", "results": []}
        if harness:
            probe_result = _execute_in_sandbox(code, prefix, harness, timeout=6)
        if probe_result.get("status") == "success":
            picked_success.append((idx, row))
        else:
            picked_fallback.append((idx, row))

        if len(picked_success) >= target:
            break
    if len(picked_success) < target:
        needed = target - len(picked_success)
        picked_success.extend(picked_fallback[:needed])
    return picked_success


def _run_static_fallback_demo() -> None:
    """
    Guaranteed meaningful demo when dataset rows are unstable.
    """
    print("\n[Static fallback demo]")
    demo_code = """
def g(x):
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, int):
        return x
    return x
""".strip()
    spec = TestSpec(
        dataset="DEMO",
        task_id="STATIC_DEMO",
        entry_point="g",
        code=demo_code,
        prompt="Static fallback demo for BVA/ECP proof",
        original_tests=[
            GeneratedTestCase(
                case_id="orig_0",
                code='assert g("abc") == "abc"',
                expected_repr='"abc"',
                args_expr='"abc"',
                input_repr='"abc"',
                test_design_method="original",
                source="static_demo",
            ),
            GeneratedTestCase(
                case_id="orig_1",
                code="assert g(5) == 5",
                expected_repr="5",
                args_expr="5",
                input_repr="5",
                test_design_method="original",
                source="static_demo",
            ),
        ],
    )
    bva = generate_bva_tests(spec)
    ecp = generate_ecp_tests(spec)
    all_cases = list(spec.original_tests) + bva + ecp
    namespace: Dict[str, Any] = {}
    exec(spec.code, namespace, namespace)
    demo_results: List[Dict[str, Any]] = []
    for case in all_cases:
        try:
            exec(case.code, namespace, namespace)
            demo_results.append(
                {
                    "test_id": case.case_id,
                    "passed": True,
                    "error": None,
                    "test_design_method": case.test_design_method,
                }
            )
        except Exception as exc:  # noqa: BLE001
            demo_results.append(
                {
                    "test_id": case.case_id,
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "test_design_method": case.test_design_method,
                }
            )
    observed = _case_counts(demo_results)
    print("  status: success")
    print(
        "  generated_cases: "
        f"original={len(spec.original_tests)}, bva={len(bva)}, ecp={len(ecp)}"
    )
    print(
        "  observed_results: "
        f"original={observed['original']['passed']}/{observed['original']['total']} passed, "
        f"bva={observed['bva']['passed']}/{observed['bva']['total']} passed, "
        f"ecp={observed['ecp']['passed']}/{observed['ecp']['total']} passed"
    )
    failures = [r for r in demo_results if not bool(r.get("passed"))]
    if failures:
        first = failures[0]
        print(
            "  first_failure:",
            f"{first.get('test_id')} | {first.get('test_design_method')} | {first.get('error')}",
        )
    print("\n  Explanation:")
    print("  - Original tests use baseline inputs and expected outputs, so they usually pass here.")
    print("  - BVA tests mutate inputs to boundary neighbors (for example, 5 -> 4 or 6).")
    print("  - In this demo, expected values stay from original tests, so boundary-mutated asserts can fail.")
    print("  - That failure is useful: it proves BVA cases were generated and actually executed.")
    print("  - ECP tests use different input classes (for example, valid value vs None).")
    print("  - Mixed ECP pass/fail outcomes show ECP generation and execution also worked.")


def _case_counts(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    summary = {
        "original": {"total": 0, "passed": 0, "failed": 0},
        "bva": {"total": 0, "passed": 0, "failed": 0},
        "ecp": {"total": 0, "passed": 0, "failed": 0},
    }
    for row in results:
        method = str(row.get("test_design_method") or "original")
        if method not in summary:
            continue
        summary[method]["total"] += 1
        if bool(row.get("passed")):
            summary[method]["passed"] += 1
        else:
            summary[method]["failed"] += 1
    return summary


def _print_sample_summary(
    dataset: str,
    task_id: Any,
    result: Dict[str, Any],
    generated_counts: Dict[str, int],
) -> Dict[str, Any]:
    observed_summary = _case_counts(result.get("results", []))
    failures = [item for item in result.get("results", []) if not bool(item.get("passed"))]

    print(f"  - task_id: {task_id}")
    print(f"    status: {result.get('status')}")
    print(
        "    generated_cases: "
        f"original={generated_counts['original']}, "
        f"bva={generated_counts['bva']}, "
        f"ecp={generated_counts['ecp']}"
    )
    print(
        "    observed_results: "
        f"original={observed_summary['original']['passed']}/{observed_summary['original']['total']} passed, "
        f"bva={observed_summary['bva']['passed']}/{observed_summary['bva']['total']} passed, "
        f"ecp={observed_summary['ecp']['passed']}/{observed_summary['ecp']['total']} passed"
    )
    if failures:
        first = failures[0]
        print(
            "    first_failure: "
            f"{first.get('test_id')} | {first.get('test_design_method')} | {first.get('error')}"
        )

    return {
        "dataset": dataset,
        "task_id": task_id,
        "status": result.get("status"),
        "generated_counts": generated_counts,
        "observed_summary": observed_summary,
        "failure_count": len(failures),
    }


def _prepare_oracle(dataset: str, row: Dict[str, Any], idx: int) -> Tuple[str, str, str, Any, Dict[str, int]]:
    if dataset == "MBPP":
        code = str(row.get("GENERATED_CODE", ""))
        task_id = row.get("task_id", idx)
        spec = extract_mbpp_spec(row, task_id, code)
        if not spec.original_tests:
            spec.original_tests = _fallback_mbpp_tests(str(row.get("test_list", "")))
        bva = generate_bva_tests(spec)
        ecp = generate_ecp_tests(spec)
        all_cases: List[GeneratedTestCase] = list(spec.original_tests) + bva + ecp
        generated_counts = {"original": len(spec.original_tests), "bva": len(bva), "ecp": len(ecp)}
        if not all_cases:
            return code, "", build_assert_harness([]), task_id, generated_counts
        script_prefix, harness = build_mbpp_oracle(spec, all_cases)
        return code, script_prefix, harness, task_id, generated_counts

    if dataset == "HumanEval":
        code = str(row.get("GENERATED_CODE", ""))
        task_id = row.get("task_id", idx)
        spec = extract_humaneval_spec(row, task_id, code)
        bva = generate_bva_tests(spec)
        ecp = generate_ecp_tests(spec)
        all_cases = list(spec.original_tests) + bva + ecp
        generated_counts = {"original": len(spec.original_tests), "bva": len(bva), "ecp": len(ecp)}
        if not all_cases:
            return code, "", build_assert_harness([]), task_id, generated_counts
        script_prefix, harness = build_humaneval_oracle(spec, all_cases)
        return code, script_prefix, harness, task_id, generated_counts

    code = str(row.get("full_code", ""))
    task_id = row.get("task_id", idx)
    spec = extract_ds1000_spec(row, task_id, code)
    script_prefix, harness = build_ds1000_oracle(spec)
    generated_counts = {"original": 0, "bva": 0, "ecp": 0}
    return code, script_prefix, harness, task_id, generated_counts


def run_showcase(limit: int) -> None:
    dataset_paths = {
        "DS1000": os.path.join(ROOT_DIR, "Code generation", "Qwen", "ds1k_gen.csv"),
        "HumanEval": os.path.join(ROOT_DIR, "Code generation", "Qwen", "humaneval_gen.csv"),
        "MBPP": os.path.join(ROOT_DIR, "Code generation", "Qwen", "mbpp_gen.csv"),
    }

    final_rows: List[Dict[str, Any]] = []
    print("BVA/ECP terminal showcase")
    print(f"row_limit_per_dataset: {limit}")

    for dataset, csv_path in dataset_paths.items():
        # Read a wider window, then pick rows that actually carry BVA/ECP/oracle signal.
        rows = _read_rows(csv_path, max(limit * 20, 40))
        selected = _pick_useful_rows(dataset, rows, limit)
        print(f"\n[{dataset}] rows_loaded={len(rows)} selected={len(selected)}")
        if not selected:
            print("  - no suitable rows found")
        for idx, row in selected:
            code, prefix, harness, task_id, generated_counts = _prepare_oracle(dataset, row, idx)
            if not harness:
                result = {"status": "no_tests", "results": []}
            else:
                result = _execute_in_sandbox(code, prefix, harness, timeout=8)
            payload = _print_sample_summary(dataset, task_id, result, generated_counts)
            final_rows.append(payload)

    aggregate = {
        "total_samples": len(final_rows),
        "with_failures": sum(1 for x in final_rows if x["failure_count"] > 0),
        "datasets": {
            name: sum(1 for x in final_rows if x["dataset"] == name) for name in dataset_paths
        },
    }
    print("\naggregate_summary:")
    print(json.dumps(aggregate, ensure_ascii=False))

    # This proves both generation paths are active in this run.
    bva_seen = any(x["generated_counts"]["bva"] > 0 for x in final_rows)
    ecp_seen = any(x["generated_counts"]["ecp"] > 0 for x in final_rows)
    bva_observed = any(x["observed_summary"]["bva"]["total"] > 0 for x in final_rows)
    ecp_observed = any(x["observed_summary"]["ecp"]["total"] > 0 for x in final_rows)
    print(f"BVA_working: {bva_seen}")
    print(f"ECP_working: {ecp_seen}")
    print(f"BVA_observed_execution: {bva_observed}")
    print(f"ECP_observed_execution: {ecp_observed}")

    if not (bva_observed and ecp_observed):
        _run_static_fallback_demo()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1, help="Rows to process per dataset for showcase")
    args = parser.parse_args()
    run_showcase(limit=max(args.limit, 1))


if __name__ == "__main__":
    main()
