#!/usr/bin/env python3
"""
LLM Code Fixing Pipeline
-------------------------
Takes patched_code.csv (with hallucination detection info) and uses
Qwen2.5-Coder-3B-Instruct to iteratively repair each code snippet,
validating against the original dataset test cases.

Output: code_fixing_results.csv
"""

import argparse
import ast
import json
import os
import re
import sys
import threading
import traceback
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 10
PROJECT_ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# 1. Model Loading
# ---------------------------------------------------------------------------

def load_model(model_id: str):
    """Load model and tokenizer with automatic device detection.

    Uses 4-bit quantization on CUDA, float16 on MPS, float32 on CPU.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)

    if torch.cuda.is_available():
        from transformers import BitsAndBytesConfig

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            low_cpu_mem_usage=True,
        )
        device = "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True,
        )
        device = "mps"
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            device_map="auto",
            low_cpu_mem_usage=True,
        )
        device = "cpu"

    print(f"Loaded {model_id} on {device}")
    return model, tokenizer, device


# ---------------------------------------------------------------------------
# 2. Data Loading
# ---------------------------------------------------------------------------

def load_datasets(dataset_dir: str) -> Dict[str, pd.DataFrame]:
    """Load MBPP, HumanEval, and DS1000 dataset CSVs."""
    dataset_dir = Path(dataset_dir)
    datasets = {}

    mbpp_path = dataset_dir / "mbpp.csv"
    if mbpp_path.exists():
        datasets["MBPP"] = pd.read_csv(mbpp_path)
        print(f"  MBPP:      {len(datasets['MBPP'])} rows")

    he_path = dataset_dir / "humaneval.csv"
    if he_path.exists():
        datasets["HumanEval"] = pd.read_csv(he_path)
        print(f"  HumanEval: {len(datasets['HumanEval'])} rows")

    ds_path = dataset_dir / "ds1000.csv"
    if ds_path.exists():
        datasets["DS1000"] = pd.read_csv(ds_path)
        print(f"  DS1000:    {len(datasets['DS1000'])} rows")

    return datasets


def get_test_data(row: pd.Series, datasets: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
    """Look up the test information for a row from its source dataset."""
    dataset_name = str(row.get("dataset", "")).strip()
    task_id = row.get("task_id")

    if dataset_name not in datasets:
        return None

    df = datasets[dataset_name]

    if dataset_name == "MBPP":
        match = df[df["task_id"] == int(task_id)] if not pd.isna(task_id) else pd.DataFrame()
        if match.empty:
            return None
        r = match.iloc[0]
        test_list_str = str(r.get("test_list", "[]"))
        test_imports_str = str(r.get("test_imports", "[]"))
        try:
            test_list_str_fixed = test_list_str.replace("'\n '", "', '").replace('"\n "', '", "')
            test_list = ast.literal_eval(test_list_str_fixed)
        except Exception:
            test_list = []
        try:
            test_imports = ast.literal_eval(test_imports_str)
        except Exception:
            test_imports = []
        return {
            "dataset": "MBPP",
            "prompt": str(r.get("prompt", "")),
            "test_list": test_list,
            "test_imports": test_imports,
        }

    elif dataset_name == "HumanEval":
        tid = str(task_id)
        match = df[df["task_id"].astype(str) == tid]
        if match.empty:
            return None
        r = match.iloc[0]
        return {
            "dataset": "HumanEval",
            "prompt": str(r.get("prompt", "")),
            "test": str(r.get("test", "")),
            "entry_point": str(r.get("entry_point", "")),
        }

    elif dataset_name == "DS1000":
        tid = task_id
        try:
            tid = int(float(tid))
        except (ValueError, TypeError):
            pass
        if "task_id" in df.columns:
            match = df[df["task_id"] == tid]
        else:
            match = df.iloc[tid: tid + 1] if isinstance(tid, int) and tid < len(df) else pd.DataFrame()
        if match.empty:
            return None
        r = match.iloc[0]
        return {
            "dataset": "DS1000",
            "prompt": str(r.get("prompt", "")),
            "code_context": str(r.get("code_context", "")),
        }

    return None


# ---------------------------------------------------------------------------
# 3. Prompt Construction
# ---------------------------------------------------------------------------

SYSTEM_MESSAGE = (
    "You are a STRICT patch-wise Python debugger.\n"
    "You are NOT allowed to refactor, redesign, or improve the code.\n"
    "You are ONLY allowed to modify code inside explicitly marked ERROR regions.\n"
    "You must preserve all existing variables, structure, and logic outside the marked region.\n"
    "You must NOT invent new variables unless absolutely required to fix the marked line.\n"
    "You must NOT modify code outside the marked region.\n"
    "You must return ONLY a single Python code block wrapped in ```python and ```.\n"
    "Do NOT include explanations."
)


def _truncate_test_cases(test_cases: str, max_cases: int = 5) -> str:
    """Keep at most *max_cases* test-case entries to stay within context limits."""
    try:
        cases = json.loads(test_cases)
        if isinstance(cases, list) and len(cases) > max_cases:
            cases = cases[:max_cases]
        return json.dumps(cases, indent=2)
    except Exception:
        lines = test_cases.strip().splitlines()
        return "\n".join(lines[:max_cases * 3])


def _get_kg_suggestions(patched_code: str, error_info: dict) -> Optional[str]:
    """Try to get KG suggestions; return None if KG module unavailable."""
    try:
        kg_path = PROJECT_ROOT / "APR" / "DS-KG"
        if not kg_path.exists():
            return None
        sys.path.insert(0, str(kg_path))
        from kg_context import get_repair_context
        ctx = get_repair_context(patched_code, error_info)
        suggestions = ctx.get("suggestions", [])
        if suggestions:
            return json.dumps(suggestions, indent=2)
    except Exception:
        pass
    return None


def build_repair_prompt(
    row: pd.Series,
    test_data: Optional[Dict[str, Any]],
    test_feedback: Optional[Dict[str, str]] = None,
) -> List[Dict[str, str]]:
    """Build the chat messages for the repair prompt.

    Two variants depending on error nature:
      - Logical (AssertionError): include failing test cases + problem statement
      - Structural/API: include AST/CFG/lib/dynamic info + error markers
    """
    patched_code = str(row.get("patched_code", row.get("generated_code", "")))
    dynamic_info = str(row.get("dynamic_info", ""))
    ast_info = str(row.get("ast_info", ""))
    cfg_info = str(row.get("cfg_info", ""))
    lib_info = str(row.get("lib_info", ""))
    error_types = str(row.get("error_types", ""))

    question = ""
    if test_data:
        question = test_data.get("prompt", "")

    # Determine if the error is logical (AssertionError / test-case mismatch)
    is_logical = False
    try:
        di = json.loads(dynamic_info) if dynamic_info and dynamic_info != "nan" else {}
    except Exception:
        di = {}
    if isinstance(di, dict) and di.get("error_type") == "AssertionError":
        is_logical = True
    if "AssertionError" in error_types or "AssertionError" in dynamic_info:
        is_logical = True

    # Incorporate test feedback from prior failed attempts
    feedback_block = ""
    if test_feedback:
        feedback_block = (
            "\n### Previous Fix Attempt Feedback:\n"
            f"- Status: {test_feedback.get('status', 'failed')}\n"
            f"- Error type: {test_feedback.get('error_type', '')}\n"
            f"- Error message: {test_feedback.get('error_message', '')}\n"
            "Use this feedback to guide your fix.\n"
        )

    if is_logical:
        test_cases_str = ""
        if isinstance(di, dict) and di.get("test_case"):
            test_cases_str = _truncate_test_cases(str(di["test_case"]))
        elif test_feedback and test_feedback.get("test_case"):
            test_cases_str = test_feedback["test_case"]

        user_prompt = f"""The following problem was answered incorrectly.

### Problem:
{question}

The implementation runs but fails test cases.

### Buggy Code:
{patched_code}

### Failing Test Cases (Input, Expected, Actual):
{test_cases_str}
{feedback_block}
### STRICT RULES:
- Modify ONLY the marked region if present.
- If no markers exist, modify the minimum number of lines required.
- Do NOT rewrite the whole function.
- Do NOT introduce new helper functions.
- Do NOT change function signature.
- Remove any ERROR markers in final output.
- Return ONLY corrected code inside a single ```python block.

Fix the logic."""
    else:
        error_context = ""
        if ast_info and ast_info != "nan":
            error_context += f"\nAST Errors:\n{ast_info}\n"
        if cfg_info and cfg_info != "nan":
            error_context += f"\nCFG Errors:\n{cfg_info}\n"
        if lib_info and lib_info != "nan":
            error_context += f"\nLibrary API Errors:\n{lib_info}\n"
        if dynamic_info and dynamic_info != "nan":
            error_context += f"\nRuntime Errors:\n{dynamic_info}\n"

        kg_context = ""
        kg_suggestions = _get_kg_suggestions(
            patched_code,
            {"error_type": error_types, "error_message": dynamic_info},
        )
        if kg_suggestions:
            kg_context = f"\nRelevant API Suggestions:\n{kg_suggestions}\n"

        user_prompt = f"""The following problem was answered incorrectly.

### Problem:
{question}

The code below contains errors.
Only the marked regions may be edited.

### Buggy Code:
{patched_code}

### Error Information:
{error_context}

### API Suggestions:
{kg_context}
{feedback_block}
### STRICT PATCH RULES:

1. ONLY modify lines between:
   <<<< [ERROR START] (...)
   ...
   [ERROR FINISH] (...) >>>>

2. Do NOT modify any other part of the code.
3. Do NOT introduce new variables unless required to fix that exact line.
4. Do NOT refactor.
5. Do NOT optimize.
6. Do NOT improve formatting.
7. Remove ERROR markers in the final output.
8. Return the FULL corrected code.
9. Output must be wrapped in one ```python code block.
10. No explanations.

Fix ONLY the marked region."""

    return [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": user_prompt.strip()},
    ]


# ---------------------------------------------------------------------------
# 4. LLM Code Generation
# ---------------------------------------------------------------------------

def extract_python_code(text: str) -> str:
    """Extract Python code from an LLM response (```python ... ``` blocks)."""
    pattern = r"```(?:python)?\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)

    if match:
        code = match.group(1).strip()
    else:
        code = text.strip()

    cleaned_lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        if re.match(r"^print\s*\(", stripped):
            continue
        if re.match(r"^#\s*(Assuming|Note:|TODO|FIXME|Correct|Use |The )", stripped):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def generate_fix(
    messages: List[Dict[str, str]],
    model,
    tokenizer,
    device: str,
    max_new_tokens: int = 512,
) -> str:
    """Run the LLM to produce a fix from chat *messages*."""
    import torch

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    gen_ids = outputs[0][len(inputs["input_ids"][0]):]
    raw_response = tokenizer.decode(gen_ids, skip_special_tokens=True)
    return extract_python_code(raw_response)


# ---------------------------------------------------------------------------
# 5. Test Evaluation
# ---------------------------------------------------------------------------

def _execute_with_timeout(func, args, timeout=TIMEOUT_SECONDS):
    """Run *func(args)* in a daemon thread; return result dict or timeout error."""
    result_container: Dict[str, Any] = {"result": None, "exception": None, "traceback": None}

    def wrapper():
        try:
            result_container["result"] = func(*args)
        except Exception as e:
            result_container["exception"] = e
            result_container["traceback"] = traceback.format_exc()

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return {
            "status": "failed",
            "error_type": "TimeoutError",
            "error_message": "Execution exceeded timeout (likely infinite loop or recursion)",
        }

    if result_container["exception"] is not None:
        e = result_container["exception"]
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
        }

    if result_container["result"] is not None:
        return result_container["result"]

    return {
        "status": "failed",
        "error_type": "UnknownError",
        "error_message": "Execution completed but no result returned",
    }


def _run_mbpp_test(fixed_code: str, test_list: List[str], test_imports: List[str]) -> Dict[str, str]:
    """Execute MBPP-style tests."""
    test_env: dict = {}
    for imp in test_imports:
        if imp.strip():
            exec(imp, test_env)
    exec(fixed_code, test_env)
    for assertion in test_list:
        if assertion.strip():
            exec(assertion, test_env)
    return {"status": "passed", "error_type": "", "error_message": ""}


def _run_humaneval_test(fixed_code: str, test_code: str, entry_point: str) -> Dict[str, str]:
    """Execute HumanEval-style tests."""
    test_env: dict = {}
    exec(fixed_code, test_env)
    exec(test_code, test_env)
    if entry_point in test_env and "check" in test_env:
        test_env["check"](test_env[entry_point])
    else:
        raise NameError(f"Entry point '{entry_point}' or 'check' function not found")
    return {"status": "passed", "error_type": "", "error_message": ""}


def _run_ds1000_test(fixed_code: str, code_context: str) -> Dict[str, str]:
    """Execute DS1000-style tests."""
    test_env: dict = {}
    exec(code_context, test_env)
    test_env["test_execution"](fixed_code)
    return {"status": "passed", "error_type": "", "error_message": ""}


def evaluate_fix(fixed_code: str, test_data: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Run the appropriate test suite for *fixed_code* and return a result dict.

    Returns dict with keys: status, error_type, error_message.
    """
    if not test_data:
        return {
            "status": "error",
            "error_type": "NoTestData",
            "error_message": "No test data found for this task",
        }

    dataset = test_data["dataset"]

    try:
        if dataset == "MBPP":
            return _execute_with_timeout(
                _run_mbpp_test,
                (fixed_code, test_data["test_list"], test_data["test_imports"]),
            )
        elif dataset == "HumanEval":
            return _execute_with_timeout(
                _run_humaneval_test,
                (fixed_code, test_data["test"], test_data["entry_point"]),
            )
        elif dataset == "DS1000":
            return _execute_with_timeout(
                _run_ds1000_test,
                (fixed_code, test_data["code_context"]),
            )
        else:
            return {
                "status": "error",
                "error_type": "UnsupportedDataset",
                "error_message": f"Unknown dataset: {dataset}",
            }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
        }


# ---------------------------------------------------------------------------
# 6. Iterative Repair Loop
# ---------------------------------------------------------------------------

def repair_row(
    row: pd.Series,
    test_data: Optional[Dict[str, Any]],
    model,
    tokenizer,
    device: str,
    max_attempts: int = 3,
) -> Dict[str, Any]:
    """Attempt up to *max_attempts* repair cycles for a single row.

    Returns a dict with: fixed_code, fix_status, fix_error_type,
    fix_error_message, attempts.
    """
    test_feedback: Optional[Dict[str, str]] = None

    for attempt in range(1, max_attempts + 1):
        # Build prompt (with optional feedback from prior attempt)
        messages = build_repair_prompt(row, test_data, test_feedback)

        # Generate fix
        try:
            fixed_code = generate_fix(messages, model, tokenizer, device)
        except Exception as e:
            return {
                "fixed_code": "",
                "fix_status": "error",
                "fix_error_type": type(e).__name__,
                "fix_error_message": f"Generation error: {e}",
                "attempts": attempt,
            }

        if not fixed_code.strip():
            test_feedback = {
                "status": "failed",
                "error_type": "EmptyOutput",
                "error_message": "Model returned empty code",
            }
            continue

        # Evaluate fix
        result = evaluate_fix(fixed_code, test_data)

        if result["status"] == "passed":
            return {
                "fixed_code": fixed_code,
                "fix_status": "passed",
                "fix_error_type": "",
                "fix_error_message": "",
                "attempts": attempt,
            }

        # Prepare feedback for next iteration
        test_feedback = {
            "status": result["status"],
            "error_type": result.get("error_type", ""),
            "error_message": result.get("error_message", ""),
            "test_case": result.get("test_case", ""),
        }

    # Exhausted all attempts
    return {
        "fixed_code": fixed_code if fixed_code else "",
        "fix_status": result.get("status", "failed") if result else "failed",
        "fix_error_type": result.get("error_type", "") if result else "",
        "fix_error_message": result.get("error_message", "") if result else "",
        "attempts": max_attempts,
    }


# ---------------------------------------------------------------------------
# 7. Results Collection / Output
# ---------------------------------------------------------------------------

ORIGINAL_COLUMNS = [
    "dataset", "status", "task_id", "ast_info", "cfg_info", "lib_info",
    "dynamic_info", "generated_code", "patched_code", "error_sources",
    "error_types", "error_lines",
]

RESULT_COLUMNS = [
    "fixed_code", "fix_status", "fix_error_type",
    "fix_error_message", "attempts", "model_used",
]


def print_summary(results_df: pd.DataFrame) -> None:
    """Print pass/fail summary statistics."""
    total = len(results_df)
    passed = (results_df["fix_status"] == "passed").sum()
    failed = (results_df["fix_status"] == "failed").sum()
    errors = (results_df["fix_status"] == "error").sum()

    print("\n" + "=" * 60)
    print("CODE FIXING RESULTS SUMMARY")
    print("=" * 60)
    print(f"  Total:   {total}")
    print(f"  Passed:  {passed}  ({passed / total * 100:.1f}%)" if total else "")
    print(f"  Failed:  {failed}  ({failed / total * 100:.1f}%)" if total else "")
    print(f"  Errors:  {errors}  ({errors / total * 100:.1f}%)" if total else "")

    if "dataset" in results_df.columns:
        print("\nPer-dataset breakdown:")
        for ds_name, grp in results_df.groupby("dataset"):
            n = len(grp)
            p = (grp["fix_status"] == "passed").sum()
            print(f"  {ds_name:12s}  {p}/{n} passed ({p / n * 100:.1f}%)" if n else "")
    print("=" * 60)


# ---------------------------------------------------------------------------
# 8. CLI / Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="LLM Code Fixing Pipeline — iteratively repair code with Qwen"
    )
    parser.add_argument("--input", default="patched_code.csv",
                        help="Path to patched_code.csv (default: patched_code.csv)")
    parser.add_argument("--output", default="code_fixing_results.csv",
                        help="Output CSV path (default: code_fixing_results.csv)")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B-Instruct",
                        help="HuggingFace model ID")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Max repair attempts per row (default: 3)")
    parser.add_argument("--dataset-dir", default="Dataset used/",
                        help="Directory containing dataset CSVs")
    parser.add_argument("--start-idx", type=int, default=None,
                        help="Start row index (0-based, inclusive)")
    parser.add_argument("--end-idx", type=int, default=None,
                        help="End row index (0-based, exclusive)")
    parser.add_argument("--resume", action="store_true",
                        help="Skip rows already present in the output file")
    return parser.parse_args()


def main():
    args = parse_args()

    # ---- Load model ----
    print(f"\n[1/4] Loading model: {args.model}")
    model, tokenizer, device = load_model(args.model)

    # ---- Load data ----
    print(f"\n[2/4] Loading data")
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"Input file not found: {input_path}")
    patched_df = pd.read_csv(input_path)
    print(f"  patched_code rows: {len(patched_df)}")

    datasets = load_datasets(args.dataset_dir)

    # ---- Determine row range ----
    start = args.start_idx if args.start_idx is not None else 0
    end = args.end_idx if args.end_idx is not None else len(patched_df)
    work_df = patched_df.iloc[start:end].copy()
    print(f"  Processing rows {start}..{end - 1} ({len(work_df)} rows)")

    # ---- Resume support ----
    already_done: set = set()
    output_path = Path(args.output)
    if args.resume and output_path.exists():
        done_df = pd.read_csv(output_path)
        for _, r in done_df.iterrows():
            already_done.add((str(r.get("dataset", "")), str(r.get("task_id", ""))))
        print(f"  Resuming — {len(already_done)} rows already processed")

    # ---- Process ----
    print(f"\n[3/4] Repairing code (max {args.max_attempts} attempts each)")
    results: List[Dict[str, Any]] = []

    for idx, (_, row) in enumerate(work_df.iterrows()):
        row_key = (str(row.get("dataset", "")), str(row.get("task_id", "")))
        if row_key in already_done:
            continue

        test_data = get_test_data(row, datasets)
        ds_label = row.get("dataset", "?")
        tid_label = row.get("task_id", "?")
        print(f"  [{idx + 1}/{len(work_df)}] {ds_label} / {tid_label} ... ", end="", flush=True)

        fix_result = repair_row(row, test_data, model, tokenizer, device, args.max_attempts)
        fix_result["model_used"] = args.model

        record = {}
        for col in ORIGINAL_COLUMNS:
            record[col] = row.get(col, "")
        record.update(fix_result)
        results.append(record)

        status_tag = fix_result["fix_status"]
        attempts = fix_result["attempts"]
        print(f"{status_tag} (attempt {attempts})")

        # Incremental save every 50 rows
        if len(results) % 50 == 0:
            _save_results(results, output_path, already_done, args.resume)

    # ---- Save final ----
    print(f"\n[4/4] Saving results to {args.output}")
    _save_results(results, output_path, already_done, args.resume)

    final_df = pd.read_csv(output_path) if output_path.exists() else pd.DataFrame(results)
    print_summary(final_df)


def _save_results(
    results: List[Dict[str, Any]],
    output_path: Path,
    already_done: set,
    resume: bool,
) -> None:
    """Write results to CSV, merging with existing file when resuming."""
    new_df = pd.DataFrame(results)
    if resume and output_path.exists():
        existing_df = pd.read_csv(output_path)
        combined = pd.concat([existing_df, new_df], ignore_index=True)
        combined.drop_duplicates(subset=["dataset", "task_id"], keep="last", inplace=True)
        combined.to_csv(output_path, index=False)
    else:
        new_df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
