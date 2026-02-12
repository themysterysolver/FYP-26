"""
Dynamic Code Hallucination detection with generated BVA/ECP tests.
"""
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from test_generation import (
    build_ds1000_oracle,
    build_humaneval_oracle,
    build_mbpp_oracle,
    extract_ds1000_spec,
    extract_humaneval_spec,
    extract_mbpp_spec,
    generate_bva_tests,
    generate_ecp_tests,
    infer_test_domains,
)

BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "Code generation", "Qwen"))

DATASETS = {
    "DS1000": {
        "path": os.path.join(BASE_DIR, "ds1k_gen.csv"),
        "code_column": "full_code",
        "task_id_column": "task_id",
        "output": "dynamic_ds1000.jsonl",
    },
    "HumanEval": {
        "path": os.path.join(BASE_DIR, "humaneval_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "dynamic_humaneval.jsonl",
    },
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "dynamic_mbpp.jsonl",
    },
}

OOM_INDICATORS = ("memoryerror", "killed", "cannot allocate", "out of memory")


def _extract_code(code: str) -> str:
    if not code or not isinstance(code, str):
        return (code or "").strip()
    if "```python" in code:
        return code.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in code:
        return code.split("```", 1)[1].split("```", 1)[0].strip()
    return code.strip()


def _is_oom(stderr: str) -> bool:
    return any(indicator in (stderr or "").lower() for indicator in OOM_INDICATORS)


def _execute_in_sandbox(code: str, harness: str, timeout: int = 5, script_prefix: str = "") -> Dict[str, Any]:
    extracted = _extract_code(code)
    full_script = script_prefix + "\n\n" + extracted + "\n\n" + harness
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as handle:
            handle.write(full_script)
            temp_path = handle.name

        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(temp_path),
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            if _is_oom(stderr):
                return {"status": "resource_error", "stderr": stderr, "stdout": stdout}
            return {"status": "crash", "stderr": stderr, "stdout": stdout}

        last_line = stdout.strip().split("\n")[-1].strip() if stdout.strip() else ""
        try:
            parsed = json.loads(last_line)
            if isinstance(parsed, list):
                return {"status": "success", "results": parsed}
            return {"status": "parse_error", "raw_output": last_line}
        except json.JSONDecodeError:
            return {"status": "parse_error", "raw_output": last_line or stdout}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "results": []}
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _classify_exception(error_msg: str) -> str:
    msg = (error_msg or "").lower()
    if "nameerror" in msg:
        return "undefined_name"
    if "typeerror" in msg:
        return "type_mismatch"
    if "indexerror" in msg or "keyerror" in msg:
        return "boundary_violation"
    if "zerodivisionerror" in msg:
        return "arithmetic_error"
    return "runtime_error"


def _classify_failures(execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    for item in execution_results:
        failed = item.get("passed") is False or bool(item.get("error"))
        if not failed:
            continue
        failure_type = "exception" if item.get("error") else "wrong_output"
        entry = {
            "test_id": item.get("test_id"),
            "type": failure_type,
            "subtype": _classify_exception(item.get("error", "")) if failure_type == "exception" else "wrong_output",
            "message": item.get("error"),
            "expected": item.get("expected"),
            "actual": item.get("output"),
            "input": item.get("input"),
            "test_design_method": item.get("test_design_method", "original"),
            "equivalence_class": item.get("equivalence_class"),
            "boundary_kind": item.get("boundary_kind"),
            "generated_test_id": item.get("generated_test_id"),
            "source": item.get("source"),
        }
        failures.append(entry)
    if not failures:
        return {
            "valid": True,
            "error_type": "none",
            "hallucination_subtype": None,
            "stage": "logical",
            "failures": [],
            "can_repair": True,
        }
    return {
        "valid": False,
        "error_type": "logical",
        "hallucination_subtype": failures[0]["subtype"],
        "stage": "logical",
        "failures": failures,
        "can_repair": True,
    }


def apply_handling(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    status = execution_result.get("status", "crash")
    out: Dict[str, Any] = {
        "status": status,
        "valid": False,
        "error_type": status,
        "hallucination_subtype": status,
        "stage": status,
        "failures": [],
        "can_repair": False,
    }
    if status == "timeout":
        out["suggestion"] = "human review"
        return out
    if status == "resource_error":
        out["stderr"] = execution_result.get("stderr", "")
        out["stdout"] = execution_result.get("stdout", "")
        return out
    if status == "parse_error":
        out["raw_output"] = execution_result.get("raw_output", "")
        out["can_repair"] = True
        return out
    if status == "crash":
        stderr = (execution_result.get("stderr") or "").lower()
        out["stderr"] = execution_result.get("stderr", "")
        out["stdout"] = execution_result.get("stdout", "")
        out["can_repair"] = "syntaxerror" in stderr or "indentationerror" in stderr
        return out
    if status == "no_tests":
        out["valid"] = None
        out["error_type"] = "no_tests"
        return out
    return out


def _build_sample_result(execution_result: Dict[str, Any], dataset: str, task_id: Any, flaky: bool = False) -> Dict[str, Any]:
    base = {"dataset": dataset, "task_id": task_id, "flaky": flaky}
    status = execution_result.get("status", "crash")
    if status != "success":
        return {**base, **apply_handling(execution_result)}
    oracle = _classify_failures(execution_result.get("results", []))
    return {**base, "status": "success", **oracle}


def _run_with_flakiness(code: str, harness: str, script_prefix: str, timeout: int) -> Tuple[Dict[str, Any], bool]:
    runs = [_execute_in_sandbox(code, harness, timeout=timeout, script_prefix=script_prefix) for _ in range(3)]
    valids: List[bool] = []
    for run in runs:
        if run.get("status") != "success":
            valids.append(False)
        else:
            valids.append(_classify_failures(run.get("results", [])).get("valid", False))
    true_count = sum(1 for val in valids if val)
    flaky = not (true_count == 0 or true_count == 3)
    desired = true_count >= 2
    for run in runs:
        if run.get("status") != "success":
            continue
        is_valid = _classify_failures(run.get("results", [])).get("valid", False)
        if is_valid == desired:
            return run, flaky
    return runs[0], flaky


def _prepare_dataset_oracle(dataset_name: str, row: Dict[str, Any], task_id: Any, code: str, enable_generated: bool) -> Dict[str, Any]:
    if dataset_name == "MBPP":
        spec = extract_mbpp_spec(row, task_id, code)
        infer_test_domains(spec)
        all_cases = list(spec.original_tests)
        if enable_generated:
            all_cases.extend(generate_bva_tests(spec))
            all_cases.extend(generate_ecp_tests(spec))
        if not all_cases:
            return {"status": "no_tests"}
        script_prefix, harness = build_mbpp_oracle(spec, all_cases)
        return {"status": "ready", "script_prefix": script_prefix, "harness": harness}

    if dataset_name == "HumanEval":
        spec = extract_humaneval_spec(row, task_id, code)
        infer_test_domains(spec)
        all_cases = list(spec.original_tests)
        if enable_generated:
            all_cases.extend(generate_bva_tests(spec))
            all_cases.extend(generate_ecp_tests(spec))
        if not all_cases:
            return {"status": "no_tests"}
        script_prefix, harness = build_humaneval_oracle(spec, all_cases)
        return {"status": "ready", "script_prefix": script_prefix, "harness": harness}

    if dataset_name == "DS1000":
        spec = extract_ds1000_spec(row, task_id, code)
        script_prefix, harness = build_ds1000_oracle(spec)
        if not harness:
            return {"status": "no_tests", "oracle_confidence": "low"}
        return {"status": "ready", "script_prefix": script_prefix, "harness": harness, "oracle_confidence": "high"}

    return {"status": "no_tests"}


def _method_stats(failures: List[Dict[str, Any]]) -> Dict[str, float]:
    counts = {"original": 0, "bva": 0, "ecp": 0}
    fail = {"original": 0, "bva": 0, "ecp": 0}
    for item in failures:
        method = str(item.get("test_design_method") or "original")
        if method not in counts:
            continue
        counts[method] += 1
        fail[method] += 1
    return {
        "original_total": counts["original"],
        "bva_total": counts["bva"],
        "ecp_total": counts["ecp"],
        "original_failures": fail["original"],
        "bva_failures": fail["bva"],
        "ecp_failures": fail["ecp"],
    }


def run_dynamic_pipeline(
    timeout: int = 5,
    run_flakiness_check: bool = False,
    enable_generated_tests: bool = True,
    datasets: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    configs = datasets or DATASETS
    summary_rows: List[Dict[str, Any]] = []
    out_dir = CURRENT_DIR

    for dataset_name, cfg in configs.items():
        csv_path = cfg["path"]
        if not os.path.isfile(csv_path):
            print(f"Skipping {dataset_name}: missing {csv_path}")
            continue
        print(f"Processing {dataset_name}...")
        df = pd.read_csv(csv_path)
        output_path = os.path.join(out_dir, cfg["output"])
        code_col = cfg["code_column"]
        task_col = cfg.get("task_id_column")

        with open(output_path, "w", encoding="utf-8") as handle:
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                task_id = row_dict.get(task_col, idx) if task_col else idx
                code = str(row_dict.get(code_col, ""))
                if not code or code == "nan":
                    record = _build_sample_result(
                        {"status": "crash", "stderr": "missing code", "stdout": ""},
                        dataset_name,
                        task_id,
                    )
                    record["error_type"] = "missing_code"
                    handle.write(json.dumps(record) + "\n")
                    summary_rows.append(
                        {
                            "dataset": dataset_name,
                            "task_id": task_id,
                            "valid": False,
                            "error_type": "missing_code",
                            "hallucination_subtype": "crash",
                            "can_repair": False,
                            "flaky": False,
                            "failure_count": 0,
                            "bva_total": 0,
                            "ecp_total": 0,
                            "bva_failures": 0,
                            "ecp_failures": 0,
                            "oracle_confidence": "none",
                        }
                    )
                    continue

                prepared = _prepare_dataset_oracle(dataset_name, row_dict, task_id, code, enable_generated_tests)
                if prepared.get("status") != "ready":
                    result = _build_sample_result({"status": "no_tests", "results": []}, dataset_name, task_id)
                    if prepared.get("oracle_confidence"):
                        result["oracle_confidence"] = prepared["oracle_confidence"]
                    handle.write(json.dumps(result) + "\n")
                    summary_rows.append(
                        {
                            "dataset": dataset_name,
                            "task_id": task_id,
                            "valid": None,
                            "error_type": "no_tests",
                            "hallucination_subtype": None,
                            "can_repair": False,
                            "flaky": False,
                            "failure_count": 0,
                            "bva_total": 0,
                            "ecp_total": 0,
                            "bva_failures": 0,
                            "ecp_failures": 0,
                            "oracle_confidence": prepared.get("oracle_confidence", "none"),
                        }
                    )
                    continue

                harness = str(prepared["harness"])
                script_prefix = str(prepared.get("script_prefix", ""))
                if run_flakiness_check:
                    execution_result, flaky = _run_with_flakiness(code, harness, script_prefix, timeout)
                else:
                    execution_result = _execute_in_sandbox(code, harness, timeout=timeout, script_prefix=script_prefix)
                    flaky = False

                result = _build_sample_result(execution_result, dataset_name, task_id, flaky=flaky)
                if prepared.get("oracle_confidence"):
                    result["oracle_confidence"] = prepared["oracle_confidence"]
                handle.write(json.dumps(result) + "\n")

                failures = result.get("failures", [])
                method_stats = _method_stats(failures)
                summary_rows.append(
                    {
                        "dataset": dataset_name,
                        "task_id": task_id,
                        "valid": result.get("valid"),
                        "error_type": result.get("error_type"),
                        "hallucination_subtype": result.get("hallucination_subtype"),
                        "can_repair": result.get("can_repair"),
                        "flaky": result.get("flaky"),
                        "failure_count": len(failures),
                        "bva_total": method_stats["bva_total"],
                        "ecp_total": method_stats["ecp_total"],
                        "bva_failures": method_stats["bva_failures"],
                        "ecp_failures": method_stats["ecp_failures"],
                        "oracle_confidence": result.get("oracle_confidence", "high"),
                    }
                )
        print(f"  Saved -> {output_path}")

    if summary_rows:
        summary_path = os.path.join(out_dir, "dynamic_summary.csv")
        pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
        print(f"Summary -> {summary_path}")
    print("Dynamic detection pipeline completed.")


if __name__ == "__main__":
    run_dynamic_pipeline(timeout=5, run_flakiness_check=False, enable_generated_tests=True)
