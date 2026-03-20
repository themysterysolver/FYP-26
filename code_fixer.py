"""
LLM Code Repair Pipeline
-------------------------
Uses Google Gemini 2.5 Flash to fix buggy code from patched_code.csv,
verifies fixes against benchmark test cases (DS1000, HumanEval, MBPP),
and outputs a structured training_data.csv.

Usage:
    export GEMINI_API_KEY="your-key-here"
    python code_fixer.py                 # proof-of-concept (1 per error type)
    python code_fixer.py --full          # full CSV (all hallucinated rows)
"""

import os
import sys
import re
import ast
import json
import csv
import time
import threading
import traceback
import argparse
from pathlib import Path

import pandas as pd
import numpy as np
import google.generativeai as genai

# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent
DATASET_DIR = PROJECT_ROOT / "Dataset used"
GENERATION_DIR = PROJECT_ROOT / "Code generation" / "Qwen"
APR_DIR = PROJECT_ROOT / "APR" / "DS-KG"

sys.path.insert(0, str(APR_DIR))
sys.path.insert(0, str(APR_DIR / "UTIL"))

from kg_context import get_repair_context

# ---------------------------------------------------------------------------
# Gemini setup
# ---------------------------------------------------------------------------

GEMINI_MODEL = "gemini-2.5-flash"
MAX_ATTEMPTS = 5
TIMEOUT_SECONDS = 10
API_RETRY_WAIT = 50


def init_gemini():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: Set the GEMINI_API_KEY environment variable.")
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)


def call_gemini(model, messages, max_retries=3):
    """Call the Gemini API with automatic rate-limit retry."""
    for retry in range(max_retries):
        try:
            response = model.generate_content(
                messages,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                ),
            )
            return response.text, None
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower():
                wait = API_RETRY_WAIT * (retry + 1)
                print(f"rate-limited, waiting {wait}s ... ", end="", flush=True)
                time.sleep(wait)
                continue
            return None, str(e)
    return None, "Rate limit exceeded after retries"


# ---------------------------------------------------------------------------
# Dataset loaders (cached)
# ---------------------------------------------------------------------------

_ds1000_df = None
_humaneval_df = None
_mbpp_df = None
_mbpp_gen_df = None


def load_ds1000():
    global _ds1000_df
    if _ds1000_df is None:
        _ds1000_df = pd.read_csv(DATASET_DIR / "ds1000.csv")
    return _ds1000_df


def load_humaneval():
    global _humaneval_df
    if _humaneval_df is None:
        _humaneval_df = pd.read_csv(DATASET_DIR / "humaneval.csv")
    return _humaneval_df


def load_mbpp():
    global _mbpp_df
    if _mbpp_df is None:
        _mbpp_df = pd.read_csv(DATASET_DIR / "mbpp.csv")
    return _mbpp_df


def load_mbpp_gen():
    global _mbpp_gen_df
    if _mbpp_gen_df is None:
        _mbpp_gen_df = pd.read_csv(GENERATION_DIR / "mbpp_gen.csv")
    return _mbpp_gen_df


def _parse_mbpp_tests(row) -> dict:
    """Extract test_list and test_imports from an MBPP dataframe row."""
    test_list_str = str(row["test_list"])
    test_list_str = test_list_str.replace("'\n '", "', '").replace('"\n "', '", "')
    test_list = ast.literal_eval(test_list_str)
    test_imports_raw = str(row.get("test_imports", "[]"))
    try:
        test_imports = ast.literal_eval(test_imports_raw)
    except Exception:
        test_imports = []
    return {"test_list": test_list, "test_imports": test_imports}


# ---------------------------------------------------------------------------
# Task-ID to test data mapping
# ---------------------------------------------------------------------------

def get_test_data(dataset: str, task_id: str) -> dict:
    """Return the test harness data needed to verify a fix.

    Falls back to the Qwen generation CSV for MBPP when the dataset
    CSV does not contain the task.
    Returns None if the task cannot be found anywhere.
    """
    dataset_upper = dataset.upper()

    if dataset_upper == "DS1000":
        df = load_ds1000()
        idx = int(task_id.replace("DS", ""))
        matches = df[df["metadata"].apply(
            lambda m: ast.literal_eval(m).get("problem_id") == idx
        )]
        if matches.empty:
            return None
        return {"code_context": matches.iloc[0]["code_context"]}

    elif dataset_upper == "HUMANEVAL":
        df = load_humaneval()
        matches = df[df["task_id"] == task_id]
        if matches.empty:
            return None
        row = matches.iloc[0]
        return {"test": row["test"], "entry_point": row["entry_point"]}

    elif dataset_upper == "MBPP":
        tid = int(task_id)
        df = load_mbpp()
        matches = df[df["task_id"] == tid]
        if not matches.empty:
            return _parse_mbpp_tests(matches.iloc[0])
        gen_df = load_mbpp_gen()
        gen_matches = gen_df[gen_df["task_id"] == tid]
        if not gen_matches.empty:
            return _parse_mbpp_tests(gen_matches.iloc[0])
        return None

    return None


# ---------------------------------------------------------------------------
# Test execution (adapted from dynamic_execution.py)
# ---------------------------------------------------------------------------

def _run_with_timeout(func, args, timeout=TIMEOUT_SECONDS):
    container = {"result": None, "exception": None}

    def wrapper():
        try:
            container["result"] = func(*args)
        except Exception as e:
            container["exception"] = e

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        return {"status": "failed", "error_type": "TimeoutError",
                "error_message": "Execution timed out"}
    if container["exception"] is not None:
        e = container["exception"]
        return {"status": "failed", "error_type": type(e).__name__,
                "error_message": str(e)}
    return container["result"]


def _verify_ds1000(code: str, code_context: str) -> dict:
    def inner(code, code_context):
        env = {}
        exec(code_context, env)
        env["test_execution"](code)
        return {"status": "passed", "error_type": "", "error_message": ""}
    return _run_with_timeout(inner, (code, code_context))


def _verify_humaneval(code: str, test_code: str, entry_point: str) -> dict:
    def inner(code, test_code, entry_point):
        env = {}
        exec(code, env)
        exec(test_code, env)
        if entry_point in env and "check" in env:
            env["check"](env[entry_point])
        else:
            raise NameError(f"'{entry_point}' or 'check' not found")
        return {"status": "passed", "error_type": "", "error_message": ""}
    return _run_with_timeout(inner, (code, test_code, entry_point))


def _verify_mbpp(code: str, test_list: list, test_imports: list) -> dict:
    def inner(code, test_list, test_imports):
        env = {}
        for imp in test_imports:
            if imp.strip():
                exec(imp, env)
        exec(code, env)
        for assertion in test_list:
            if assertion.strip():
                exec(assertion, env)
        return {"status": "passed", "error_type": "", "error_message": ""}
    return _run_with_timeout(inner, (code, test_list, test_imports))


def verify_fix(dataset: str, fixed_code: str, test_data: dict) -> dict:
    """Run the fixed code against benchmark tests."""
    dataset_upper = dataset.upper()
    try:
        if dataset_upper == "DS1000":
            return _verify_ds1000(fixed_code, test_data["code_context"])
        elif dataset_upper == "HUMANEVAL":
            return _verify_humaneval(fixed_code, test_data["test"],
                                     test_data["entry_point"])
        elif dataset_upper == "MBPP":
            return _verify_mbpp(fixed_code, test_data["test_list"],
                                test_data["test_imports"])
    except Exception as e:
        return {"status": "failed", "error_type": type(e).__name__,
                "error_message": str(e)}
    return {"status": "failed", "error_type": "UnknownDataset",
            "error_message": f"Unknown dataset: {dataset}"}


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

TRIPLE = "``" + "`"

def build_repair_prompt(
    buggy_code: str,
    patched_code: str,
    ast_info: str,
    lib_info: str,
    dynamic_info: str,
    kg_summary: str,
    dataset: str,
    previous_attempt_error: str = "",
) -> list[dict]:
    """Build a chat-style repair prompt for Gemini."""

    system_message = (
        "You are a precise Python debugger.\n"
        "You must fix ONLY the buggy region marked by "
        "<<<< [ERROR START] ... [ERROR FINISH] >>>>\n"
        "Preserve all code outside the marked region exactly.\n"
        "Return ONLY the complete corrected Python code inside a single "
        + TRIPLE + "python" + TRIPLE + " block.\n"
        "Do NOT include explanations, comments about your changes, or "
        "markdown outside the code block."
    )

    error_parts = []
    if ast_info and ast_info.strip() and ast_info.strip() != "nan":
        error_parts.append(f"- AST analysis: {ast_info}")
    if lib_info and lib_info.strip() and lib_info.strip() != "nan":
        error_parts.append(f"- Library/API analysis: {lib_info}")
    if dynamic_info and dynamic_info.strip() and dynamic_info.strip() != "nan":
        try:
            dyn = json.loads(dynamic_info)
            error_parts.append(
                f"- Runtime error: {dyn.get('error_type', '')}: "
                f"{dyn.get('error_message', '')}"
            )
        except (json.JSONDecodeError, TypeError):
            error_parts.append(f"- Runtime info: {dynamic_info}")
    error_analysis = "\n".join(error_parts) if error_parts else "No static analysis details available."

    user_prompt = (
        "Fix the following buggy Python code.\n\n"
        "## Buggy Code:\n"
        + TRIPLE + "python\n"
        + buggy_code.strip() + "\n"
        + TRIPLE + "\n\n"
        "## Patched Code (error region marked):\n"
        + TRIPLE + "\n"
        + patched_code.strip() + "\n"
        + TRIPLE + "\n\n"
        "## Error Analysis:\n"
        + error_analysis + "\n\n"
        "## KG-Based API Context:\n"
        + kg_summary + "\n\n"
        "## Instructions:\n"
        "- Fix ONLY the lines between <<<< [ERROR START] and [ERROR FINISH] >>>> markers.\n"
        "- Do NOT refactor, rename variables, or rewrite the function.\n"
        "- Remove the ERROR markers in the output.\n"
        "- Return the FULL corrected code in a single " + TRIPLE + "python" + TRIPLE + " block.\n"
    )

    if previous_attempt_error:
        user_prompt += (
            "\n## Previous Fix Attempt Failed:\n"
            "The last fix you generated still produced this error:\n"
            + previous_attempt_error + "\n"
            "Please try a different approach to fix the marked region.\n"
        )

    return [
        {"role": "user",
         "parts": ["[System]\n" + system_message + "\n\n[Task]\n" + user_prompt]}
    ]


def extract_python_code(response_text: str) -> str:
    """Pull the first python code block from the LLM response."""
    m = re.search(r"```python\s*\n(.*?)```", response_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", response_text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return response_text.strip()


# ---------------------------------------------------------------------------
# KG context helper
# ---------------------------------------------------------------------------

def safe_get_repair_context(patched_code: str, dynamic_info: str, lib_info: str) -> str:
    """Try to get KG context; return empty string on failure."""
    try:
        error_info = {}
        if dynamic_info and dynamic_info.strip() and dynamic_info.strip() != "nan":
            try:
                dyn = json.loads(dynamic_info)
                error_info["error_type"] = dyn.get("error_type", "")
                error_info["error_message"] = dyn.get("error_message", "")
            except (json.JSONDecodeError, TypeError):
                pass
        if lib_info and lib_info.strip() and lib_info.strip() != "nan":
            error_info["libapi_details"] = lib_info

        if not error_info:
            return "No KG suggestions available."

        ctx = get_repair_context(patched_code, error_info)
        summary = ctx.get("context_summary", "")
        return summary if summary else "No KG suggestions available."
    except Exception:
        return "No KG suggestions available."


# ---------------------------------------------------------------------------
# Primary error-type extraction from patched_code.csv
# ---------------------------------------------------------------------------

_ERROR_TYPE_RE = re.compile(
    r"(?:dynamic|ast|lib|cfg):\s*(\w+(?:Error)?)", re.IGNORECASE
)


def primary_error_type(error_types_str: str) -> str:
    """Extract the first concrete error class from the error_types column."""
    if not error_types_str or str(error_types_str) == "nan":
        return "Unknown"
    m = _ERROR_TYPE_RE.search(str(error_types_str))
    return m.group(1) if m else "Unknown"


# ---------------------------------------------------------------------------
# Example selection
# ---------------------------------------------------------------------------

TARGET_ERROR_TYPES = [
    "SyntaxError",
    "AttributeError",
    "TypeError",
    "NameError",
    "ModuleNotFoundError",
    "ValueError",
    "IndentationError",
    "UnboundLocalError",
]


def select_examples(patched_df: pd.DataFrame) -> pd.DataFrame:
    """Pick one row per target error type."""
    patched_df = patched_df.copy()
    patched_df["_primary_error"] = patched_df["error_types"].apply(primary_error_type)

    selected = []
    for etype in TARGET_ERROR_TYPES:
        candidates = patched_df[patched_df["_primary_error"] == etype]
        if candidates.empty:
            print(f"  WARNING: no examples found for {etype}, skipping")
            continue
        selected.append(candidates.iloc[0])

    result = pd.DataFrame(selected)
    result.drop(columns=["_primary_error"], inplace=True, errors="ignore")
    return result


# ---------------------------------------------------------------------------
# Main repair loop
# ---------------------------------------------------------------------------

def repair_row(model, row: pd.Series) -> dict:
    """Attempt to repair one buggy code sample.

    Returns a dict matching the training_data.csv schema.
    """
    dataset = str(row["dataset"])
    task_id = str(row["task_id"])
    buggy_code = str(row["generated_code"])
    patched_code = str(row["patched_code"])
    ast_info = str(row.get("ast_info", ""))
    lib_info = str(row.get("lib_info", ""))
    dynamic_info = str(row.get("dynamic_info", ""))
    error_type = primary_error_type(str(row.get("error_types", "")))

    print(f"\n{'='*60}")
    print(f"  Task: {task_id} | Dataset: {dataset} | Error: {error_type}")
    print(f"{'='*60}")

    test_data = get_test_data(dataset, task_id)
    if test_data is None:
        print(f"  SKIP: could not load test data for {dataset}/{task_id}")
        return {
            "task_id": task_id, "dataset": dataset,
            "buggy_code": buggy_code, "patched_code": patched_code,
            "fixed_code": "", "repair_passed": False,
            "attempts_taken": 0, "error_type": error_type,
        }

    kg_summary = safe_get_repair_context(patched_code, dynamic_info, lib_info)

    previous_error = ""
    fixed_code = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  Attempt {attempt}/{MAX_ATTEMPTS} ... ", end="", flush=True)

        messages = build_repair_prompt(
            buggy_code, patched_code,
            ast_info, lib_info, dynamic_info,
            kg_summary, dataset,
            previous_attempt_error=previous_error,
        )

        raw_text, api_err = call_gemini(model, messages)
        if api_err:
            print(f"API error: {api_err}")
            previous_error = f"API call failed: {api_err}"
            continue

        fixed_code = extract_python_code(raw_text)
        if not fixed_code:
            print("empty response")
            previous_error = "Model returned empty code."
            continue

        result = verify_fix(dataset, fixed_code, test_data)

        if result["status"] == "passed":
            print("PASSED")
            return {
                "task_id": task_id, "dataset": dataset,
                "buggy_code": buggy_code, "patched_code": patched_code,
                "fixed_code": fixed_code, "repair_passed": True,
                "attempts_taken": attempt, "error_type": error_type,
            }

        err_msg = f"{result['error_type']}: {result['error_message']}"
        print(f"FAILED ({err_msg[:80]})")
        previous_error = err_msg

    print(f"  EXHAUSTED all {MAX_ATTEMPTS} attempts for {task_id}")
    return {
        "task_id": task_id, "dataset": dataset,
        "buggy_code": buggy_code, "patched_code": patched_code,
        "fixed_code": fixed_code, "repair_passed": False,
        "attempts_taken": MAX_ATTEMPTS, "error_type": error_type,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LLM Code Repair Pipeline")
    parser.add_argument("--full", action="store_true",
                        help="Process the entire patched_code.csv (expensive)")
    args = parser.parse_args()

    model = init_gemini()

    patched_df = pd.read_csv(PROJECT_ROOT / "patched_code.csv")
    patched_df = patched_df[patched_df["status"] == "hallucinated"]
    print(f"Loaded {len(patched_df)} hallucinated rows from patched_code.csv")

    if args.full:
        work_df = patched_df
        print("Mode: FULL -- processing all rows")
    else:
        work_df = select_examples(patched_df)
        print(f"Mode: PROOF-OF-CONCEPT -- selected {len(work_df)} examples "
              f"(1 per error type)")

    results = []
    for idx, row in work_df.iterrows():
        record = repair_row(model, row)
        results.append(record)

    out_path = PROJECT_ROOT / "training_data.csv"
    out_df = pd.DataFrame(results)
    col_order = [
        "task_id", "dataset", "buggy_code", "patched_code",
        "fixed_code", "repair_passed", "attempts_taken", "error_type",
    ]
    out_df = out_df[[c for c in col_order if c in out_df.columns]]
    out_df.to_csv(out_path, index=False, quoting=csv.QUOTE_ALL)

    passed = out_df["repair_passed"].sum()
    total = len(out_df)
    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed}/{total} repairs passed")
    print(f"  Output : {out_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
