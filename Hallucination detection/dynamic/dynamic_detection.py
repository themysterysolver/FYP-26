"""
Dynamic Code Hallucination detection: execute generated code in a sandbox,
run dataset-specific test oracles, and classify failures with repairability.
See PLAN.md for full design.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

import pandas as pd

# =========================
# PATH CONFIG
# =========================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "Code generation", "Qwen")
)

DATASETS = {
    "DS1000": {
        "path": os.path.join(BASE_DIR, "ds1k_gen.csv"),
        "code_column": "full_code",
        "task_id_column": None,
        "output": "dynamic_ds1000.jsonl",
        "test_columns": None,
    },
    "HumanEval": {
        "path": os.path.join(BASE_DIR, "humaneval_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "dynamic_humaneval.jsonl",
        "test_columns": ("test", "entry_point"),
    },
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "dynamic_mbpp.jsonl",
        "test_columns": ("test_list", "test_imports"),
    },
}

# OOM indicators in stderr
OOM_INDICATORS = ("memoryerror", "killed", "memory", "cannot allocate", "out of memory")

# =========================
# Step 1: Code extraction
# =========================


def _extract_code(code: str) -> str:
    """Strip markdown fences and extract executable Python."""
    if not code or not isinstance(code, str):
        return (code or "").strip()
    if "```python" in code:
        return code.split("```python")[1].split("```")[0].strip()
    if "```" in code:
        return code.split("```")[1].split("```")[0].strip()
    return code.strip()


# =========================
# Step 2: Harness generation
# =========================


def _generate_harness_mbpp(test_list: List[str], test_imports: Optional[List[str]] = None) -> str:
    """Build harness that exec's each assert string and prints JSON results."""
    imports_block = ""
    if test_imports and isinstance(test_imports, list) and len(test_imports) > 0:
        for imp in test_imports:
            if isinstance(imp, str) and imp.strip():
                imports_block += imp.strip() + "\n"
    if imports_block:
        imports_block += "\n"

    # Escape for embedding in a Python string
    escaped = json.dumps(test_list, ensure_ascii=False)
    return imports_block + """
import json
_test_list = """ + escaped + """
_results = []
for _i, _stmt in enumerate(_test_list):
    try:
        exec(_stmt)
        _results.append({"test_id": _i, "output": None, "error": None, "passed": True})
    except AssertionError as _e:
        _results.append({"test_id": _i, "output": None, "error": str(_e), "passed": False})
    except Exception as _e:
        _results.append({"test_id": _i, "output": None, "error": str(_e), "passed": False})
print(json.dumps(_results))
"""


def _generate_harness_humaneval(test_block: str, entry_point: str) -> str:
    """Build harness that exec's test block (which calls check(entry_point)); one result for the whole block."""
    # Encode test block so we can safely embed it and exec in subprocess
    test_encoded = json.dumps(test_block)
    return '''
import json
_tb = ''' + repr(test_encoded) + '''
try:
    exec(json.loads(_tb))
    _results = [{"test_id": 0, "output": None, "error": None, "passed": True}]
except AssertionError as _e:
    _results = [{"test_id": 0, "output": None, "error": str(_e), "passed": False}]
except Exception as _e:
    _results = [{"test_id": 0, "output": None, "error": str(_e), "passed": False}]
print(json.dumps(_results))
'''


def _parse_mbpp_test_list(raw: Any) -> List[str]:
    """Parse MBPP test_list (string or list) into list of assert strings."""
    if isinstance(raw, list):
        return [str(s).strip() for s in raw if s]
    if not isinstance(raw, str):
        return []
    s = raw.strip()
    if not s:
        return []
    try:
        parsed = ast.literal_eval(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if x]
    except (ValueError, SyntaxError):
        pass
    # Fallback: split by common pattern
    lines = [line.strip() for line in s.replace("', '", "\n").replace("'\\n", "\n").split("\n") if line.strip()]
    return [line.strip("'\"").strip() for line in lines if line.startswith("assert ")]


# =========================
# Step 3: Subprocess execution
# =========================


def _is_oom(stderr: str) -> bool:
    """Return True if stderr indicates memory exhaustion."""
    if not stderr:
        return False
    lower = stderr.lower()
    return any(ind in lower for ind in OOM_INDICATORS)


def _execute_in_sandbox(
    code: str,
    harness: str,
    timeout: int = 5,
    script_prefix: str = "",
) -> Dict[str, Any]:
    """
    Run code + harness in subprocess. Returns one of:
    { status: "success", results: [...] }
    { status: "timeout", results: [] }
    { status: "resource_error", stderr, stdout }
    { status: "crash", stderr, stdout }
    { status: "parse_error", raw_output }
    """
    extracted = _extract_code(code)
    full_script = script_prefix + "\n\n" + extracted + "\n\n" + harness
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(full_script)
            temp_path = f.name
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

        lines = stdout.strip().split("\n")
        last_line = lines[-1].strip() if lines else ""
        try:
            test_results = json.loads(last_line)
            if not isinstance(test_results, list):
                return {"status": "parse_error", "raw_output": last_line}
            return {"status": "success", "results": test_results}
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


# =========================
# Step 4: Oracle and handling
# =========================


def _classify_exception(error_msg: str) -> str:
    """Map exception message to hallucination subtype."""
    lower = (error_msg or "").lower()
    if "nameerror" in lower:
        return "undefined_name"
    if "typeerror" in lower:
        return "type_mismatch"
    if "indexerror" in lower or "keyerror" in lower:
        return "boundary_violation"
    if "zerodivisionerror" in lower:
        return "arithmetic_error"
    return "runtime_error"


def _compare_values(actual: Any, expected: Any, method: str = "exact") -> bool:
    """Flexible comparison for different data types."""
    if method == "exact":
        return actual == expected
    if method == "approx":
        try:
            return abs(float(actual) - float(expected)) < 0.001
        except (TypeError, ValueError):
            return False
    if method == "set":
        try:
            return set(actual) == set(expected)
        except TypeError:
            return False
    if method == "sorted":
        try:
            return sorted(actual) == sorted(expected)
        except TypeError:
            return False
    return False


def _classify_failures(
    execution_results: List[Dict],
    test_metadata: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build valid, error_type, hallucination_subtype, failures, can_repair from harness results."""
    failures = []
    for item in execution_results:
        test_id = item.get("test_id", len(failures))
        if item.get("error"):
            failures.append({
                "test_id": test_id,
                "type": "exception",
                "subtype": _classify_exception(item["error"]),
                "message": item["error"],
            })
        elif item.get("passed") is False:
            failures.append({
                "test_id": test_id,
                "type": "wrong_output",
                "expected": item.get("expected"),
                "actual": item.get("output"),
                "input": item.get("input"),
            })
    if not failures:
        return {
            "valid": True,
            "error_type": "none",
            "hallucination_subtype": None,
            "stage": "logical",
            "failures": [],
            "can_repair": True,
        }
    first = failures[0]
    subtype = first.get("subtype") if first.get("type") == "exception" else "wrong_output"
    return {
        "valid": False,
        "error_type": "logical",
        "hallucination_subtype": subtype,
        "stage": "logical",
        "failures": failures,
        "can_repair": True,
    }


def apply_handling(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """Map execution outcome to full result with can_repair, suggestion, hallucination_subtype."""
    status = execution_result.get("status", "crash")
    out = {
        "status": status,
        "valid": False,
        "error_type": status,
        "hallucination_subtype": status,
        "stage": status,
        "failures": [],
        "can_repair": False,
        "flaky": False,
    }
    if status == "timeout":
        out["can_repair"] = False
        out["suggestion"] = "human review"
        out["results"] = []
        return out
    if status == "resource_error":
        out["can_repair"] = False
        out["stderr"] = execution_result.get("stderr", "")
        out["stdout"] = execution_result.get("stdout", "")
        return out
    if status == "parse_error":
        out["can_repair"] = True
        out["raw_output"] = execution_result.get("raw_output", "")
        return out
    if status == "crash":
        stderr = (execution_result.get("stderr") or "").lower()
        out["stderr"] = execution_result.get("stderr", "")
        out["stdout"] = execution_result.get("stdout", "")
        if "syntaxerror" in stderr or "indentationerror" in stderr:
            out["can_repair"] = True
        else:
            out["can_repair"] = False
        return out
    if status == "no_tests":
        out["valid"] = None
        out["error_type"] = "no_tests"
        out["can_repair"] = False
        return out
    return out


def build_sample_result(
    execution_result: Dict[str, Any],
    dataset: str,
    task_id: Any,
    test_metadata: Optional[Dict] = None,
    flaky: bool = False,
) -> Dict[str, Any]:
    """Single entry point per sample: apply_handling for non-success, oracle for success."""
    status = execution_result.get("status", "crash")
    base = {
        "dataset": dataset,
        "task_id": task_id,
        "flaky": flaky,
    }
    if status != "success":
        handled = apply_handling(execution_result)
        return {**base, **handled}
    oracle = _classify_failures(execution_result.get("results", []), test_metadata)
    return {
        **base,
        "status": "success",
        "valid": oracle["valid"],
        "error_type": oracle["error_type"],
        "hallucination_subtype": oracle["hallucination_subtype"],
        "stage": oracle["stage"],
        "failures": oracle["failures"],
        "can_repair": oracle["can_repair"],
    }


# =========================
# Flakiness: 3x majority vote
# =========================


def _run_with_flakiness(
    code: str,
    harness: str,
    script_prefix: str,
    timeout: int,
) -> tuple[Dict[str, Any], bool]:
    """Run 3 times; return (majority execution_result, flaky)."""
    runs = []
    for _ in range(3):
        r = _execute_in_sandbox(code, harness, timeout=timeout, script_prefix=script_prefix)
        runs.append(r)
    valids = []
    for r in runs:
        if r.get("status") != "success":
            valids.append(False)
        else:
            cf = _classify_failures(r.get("results", []))
            valids.append(cf.get("valid", False))
    true_count = sum(1 for v in valids if v is True)
    false_count = sum(1 for v in valids if v is False)
    flaky = not (true_count == 3 or false_count == 3)
    if true_count >= 2:
        majority_valid = True
    else:
        majority_valid = False
    chosen = runs[0]
    for r in runs:
        if r.get("status") == "success":
            cf = _classify_failures(r.get("results", []))
            if cf.get("valid") == majority_valid:
                chosen = r
                break
    return chosen, flaky


# =========================
# Pipeline
# =========================


def run_dynamic_pipeline(
    timeout: int = 5,
    run_flakiness_check: bool = False,
    datasets: Optional[Dict[str, Dict]] = None,
) -> None:
    """Run dynamic detection on all configured datasets; write JSONL and optional summary CSV."""
    configs = datasets or DATASETS
    summary_rows = []
    out_dir = os.path.dirname(os.path.abspath(__file__))

    for dataset_name, cfg in configs.items():
        csv_path = cfg["path"]
        if not os.path.isfile(csv_path):
            print(f"Skipping {dataset_name}: file not found {csv_path}")
            continue
        df = pd.read_csv(csv_path)
        code_col = cfg["code_column"]
        task_col = cfg["task_id_column"]
        output_name = cfg["output"]
        test_columns = cfg.get("test_columns")
        output_path = os.path.join(out_dir, output_name)
        print(f"Processing {dataset_name}...")

        with open(output_path, "w", encoding="utf-8") as out_file:
            for idx, row in df.iterrows():
                task_id = row.get(task_col, idx) if task_col else idx
                code = str(row.get(code_col, ""))
                if not code or code == "nan":
                    record = build_sample_result(
                        {"status": "crash", "stderr": "missing code", "stdout": ""},
                        dataset_name,
                        task_id,
                    )
                    record["valid"] = False
                    record["error_type"] = "missing_code"
                    out_file.write(json.dumps(record) + "\n")
                    summary_rows.append({"dataset": dataset_name, "task_id": task_id, "valid": False, "error_type": "missing_code", "hallucination_subtype": "crash", "can_repair": False, "flaky": False})
                    continue

                if dataset_name == "DS1000" or test_columns is None:
                    record = build_sample_result(
                        {"status": "no_tests", "results": []},
                        dataset_name,
                        task_id,
                    )
                    out_file.write(json.dumps(record) + "\n")
                    summary_rows.append({"dataset": dataset_name, "task_id": task_id, "valid": None, "error_type": "no_tests", "hallucination_subtype": None, "can_repair": False, "flaky": False})
                    continue

                script_prefix = ""
                harness = ""
                if dataset_name == "MBPP":
                    test_list_raw = row.get("test_list", [])
                    test_imports_raw = row.get("test_imports", [])
                    test_list = _parse_mbpp_test_list(test_list_raw)
                    if not test_list:
                        record = build_sample_result(
                            {"status": "no_tests", "results": []},
                            dataset_name,
                            task_id,
                        )
                        out_file.write(json.dumps(record) + "\n")
                        summary_rows.append({"dataset": dataset_name, "task_id": task_id, "valid": None, "error_type": "no_tests", "hallucination_subtype": None, "can_repair": False, "flaky": False})
                        continue
                    test_imports = test_imports_raw if isinstance(test_imports_raw, list) else (ast.literal_eval(test_imports_raw) if isinstance(test_imports_raw, str) and test_imports_raw.strip() else [])
                    harness = _generate_harness_mbpp(test_list, test_imports)
                    if test_imports:
                        script_prefix = "\n".join(str(i).strip() for i in test_imports if i) or ""
                elif dataset_name == "HumanEval":
                    test_block = str(row.get("test", ""))
                    entry_point = str(row.get("entry_point", ""))
                    if not test_block or test_block == "nan":
                        record = build_sample_result(
                            {"status": "no_tests", "results": []},
                            dataset_name,
                            task_id,
                        )
                        out_file.write(json.dumps(record) + "\n")
                        summary_rows.append({"dataset": dataset_name, "task_id": task_id, "valid": None, "error_type": "no_tests", "hallucination_subtype": None, "can_repair": False, "flaky": False})
                        continue
                    harness = _generate_harness_humaneval(test_block, entry_point)
                    script_prefix = ""

                if run_flakiness_check:
                    execution_result, flaky = _run_with_flakiness(code, harness, script_prefix, timeout)
                else:
                    execution_result = _execute_in_sandbox(code, harness, timeout=timeout, script_prefix=script_prefix)
                    flaky = False

                record = build_sample_result(
                    execution_result,
                    dataset_name,
                    task_id,
                    flaky=flaky,
                )
                out_file.write(json.dumps(record) + "\n")
                summary_rows.append({
                    "dataset": dataset_name,
                    "task_id": task_id,
                    "valid": record.get("valid"),
                    "error_type": record.get("error_type"),
                    "hallucination_subtype": record.get("hallucination_subtype"),
                    "can_repair": record.get("can_repair"),
                    "flaky": record.get("flaky"),
                    "failure_count": len(record.get("failures", [])),
                })

        print(f"  Saved -> {output_path}")

    if summary_rows:
        summary_path = os.path.join(out_dir, "dynamic_summary.csv")
        pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
        print(f"Summary -> {summary_path}")
    print("Dynamic detection pipeline completed.")


if __name__ == "__main__":
    run_dynamic_pipeline(timeout=5, run_flakiness_check=False)
