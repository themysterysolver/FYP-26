"""
APRInput builder: merge generation + static + dynamic by (dataset, task_id)
and emit APRInput list, JSONL, or Parquet.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .adapters import (
    current_ast_to_ast_result,
    current_cfg_to_cfg_result,
    current_dynamic_to_dynamic_result,
    current_libapi_to_library_api_result,
)
from .alignment import compute_alignment_check
from .problem_context import (
    build_problem_context,
    get_canonical_solution,
    get_generated_code,
)
from .schema import APRInput

DETECTOR_VERSION = "0.2.1"

# Dataset label in detection outputs (DS1000) vs in APRInput (DS-1000)
DATASET_LABEL_TO_SOURCE: Dict[str, str] = {
    "MBPP": "MBPP",
    "HumanEval": "HumanEval",
    "DS1000": "DS-1000",
}


def _load_static_index(ast_path: str, cfg_path: str, lib_path: str) -> Dict[tuple, Dict[str, Any]]:
    """Load AST, CFG, LIB summary CSVs and index by (dataset, task_id)."""
    index: Dict[tuple, Dict[str, Any]] = {}
    for path, key in [(ast_path, "ast"), (cfg_path, "cfg"), (lib_path, "lib")]:
        if not path or not os.path.isfile(path):
            continue
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            d = row.get("dataset")
            t = row.get("task_id")
            if pd.isna(d) or pd.isna(t):
                continue
            k = (str(d).strip(), t if isinstance(t, str) else str(t))
            if k not in index:
                index[k] = {"ast": {}, "cfg": {}, "lib": {}}
            index[k][key] = row.to_dict()
    return index


def _load_dynamic_index(dynamic_paths: Dict[str, str]) -> Dict[tuple, Dict]:
    """Load dynamic JSONL per dataset and index by (dataset, task_id)."""
    index: Dict[tuple, Dict] = {}
    for dataset, path in dynamic_paths.items():
        if not path or not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = rec.get("task_id")
                if tid is None:
                    continue
                k = (dataset, tid if isinstance(tid, str) else str(tid))
                index[k] = rec
    return index


def _all_generation_rows(
    gen_paths: Dict[str, str],
) -> List[tuple]:
    """Yield (source_dataset, task_id, row_dict) from generation CSVs."""
    rows: List[tuple] = []
    for det_label, path in gen_paths.items():
        if not path or not os.path.isfile(path):
            continue
        df = pd.read_csv(path)
        source = DATASET_LABEL_TO_SOURCE.get(det_label, det_label)
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            for k, v in row_dict.items():
                if pd.isna(v):
                    row_dict[k] = None
            task_id = row_dict.get("task_id")
            if task_id is None:
                continue
            if not isinstance(task_id, str):
                task_id = str(task_id)
            rows.append((source, task_id, row_dict))
    return rows


def build_one_apr_input(
    source_dataset: str,
    task_id: str,
    row: Dict[str, Any],
    static_index: Dict[tuple, Dict[str, Any]],
    dynamic_index: Dict[tuple, Dict],
    detector_version: str = DETECTOR_VERSION,
) -> APRInput:
    """Build a single APRInput for one (source_dataset, task_id) row."""
    # Detection pipeline uses DS1000; APRInput uses DS-1000
    det_key = "DS1000" if source_dataset == "DS-1000" else source_dataset
    key = (det_key, task_id)

    generated_code = get_generated_code(det_key, row)
    canonical_solution = get_canonical_solution(source_dataset, row)
    problem_ctx = build_problem_context(source_dataset, row, task_id, generated_code, canonical_solution)
    test_cases = problem_ctx["test_cases"]
    test_case_ids = [tc.get("test_id") for tc in test_cases if tc.get("test_id")]

    static = static_index.get(key, {})
    ast_record = static.get("ast", {})
    cfg_record = static.get("cfg", {})
    lib_record = static.get("lib", {})
    dynamic_record = dynamic_index.get(key, {})

    static_ast = current_ast_to_ast_result(ast_record, generated_code)
    static_cfg = current_cfg_to_cfg_result(cfg_record)
    static_library_api = current_libapi_to_library_api_result(lib_record)
    dynamic_analysis = current_dynamic_to_dynamic_result(dynamic_record, test_case_ids=test_case_ids)

    alignment_check = compute_alignment_check(
        static_ast, static_cfg, static_library_api, dynamic_analysis
    )

    apr_task_id = f"{source_dataset}_{task_id}"

    return {
        "task_id": apr_task_id,
        "generated_code": generated_code,
        "canonical_solution": canonical_solution,
        "problem_description": problem_ctx["problem_description"],
        "function_signature": problem_ctx["function_signature"],
        "test_cases": test_cases,
        "static_ast": static_ast,
        "static_cfg": static_cfg,
        "static_library_api": static_library_api,
        "dynamic_analysis": dynamic_analysis,
        "alignment_check": alignment_check,
        "source_dataset": source_dataset,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "detector_version": detector_version,
    }


def build_apr_input(
    generation_csv_paths: Dict[str, str],
    ast_summary_path: str,
    cfg_summary_path: str,
    libapi_summary_path: str,
    dynamic_jsonl_paths: Dict[str, str],
    detector_version: str = DETECTOR_VERSION,
) -> List[APRInput]:
    """
    Build list of APRInput from generation CSVs and detection outputs.
    generation_csv_paths: {"MBPP": path, "HumanEval": path, "DS1000": path}
    dynamic_jsonl_paths: {"MBPP": path, "HumanEval": path, "DS1000": path}
    """
    static_index = _load_static_index(ast_summary_path, cfg_summary_path, libapi_summary_path)
    dynamic_index = _load_dynamic_index(dynamic_jsonl_paths)
    gen_rows = _all_generation_rows(generation_csv_paths)

    result: List[APRInput] = []
    for source_dataset, task_id, row in gen_rows:
        apr = build_one_apr_input(
            source_dataset, task_id, row,
            static_index, dynamic_index,
            detector_version=detector_version,
        )
        result.append(apr)
    return result


def write_apr_input_jsonl(apr_inputs: List[APRInput], path: str) -> None:
    """Write APRInput list to JSONL (one JSON object per line)."""
    with open(path, "w", encoding="utf-8") as f:
        for apr in apr_inputs:
            # Convert to JSON-serializable (same structure)
            f.write(json.dumps(apr, ensure_ascii=False) + "\n")


def write_apr_input_parquet(apr_inputs: List[APRInput], path: str) -> None:
    """Write APRInput list to Parquet (nested fields as JSON strings)."""
    from .schema import APR_INPUT_PARQUET_SCHEMA
    if APR_INPUT_PARQUET_SCHEMA is None:
        raise ImportError("pyarrow is required for Parquet output: pip install pyarrow")

    rows: List[Dict[str, Any]] = []
    for apr in apr_inputs:
        rows.append({
            "task_id": apr.get("task_id", ""),
            "generated_code": apr.get("generated_code", ""),
            "canonical_solution": apr.get("canonical_solution") or "",
            "problem_description": apr.get("problem_description", ""),
            "function_signature": apr.get("function_signature", ""),
            "test_cases": json.dumps(apr.get("test_cases") or []),
            "static_ast": json.dumps(apr.get("static_ast") or {}),
            "static_cfg": json.dumps(apr.get("static_cfg") or {}),
            "static_library_api": json.dumps(apr.get("static_library_api") or {}),
            "dynamic_analysis": json.dumps(apr.get("dynamic_analysis") or {}),
            "alignment_check": json.dumps(apr.get("alignment_check") or {}),
            "source_dataset": apr.get("source_dataset", ""),
            "timestamp": apr.get("timestamp", ""),
            "detector_version": apr.get("detector_version", ""),
        })
    df = pd.DataFrame(rows)
    import pyarrow as pa
    table = pa.Table.from_pandas(df, schema=APR_INPUT_PARQUET_SCHEMA, preserve_index=False)
    import pyarrow.parquet as pq
    pq.write_table(table, path)


def run_builder(
    generation_dir: Optional[str] = None,
    static_dir: Optional[str] = None,
    dynamic_dir: Optional[str] = None,
    output_path: Optional[str] = None,
    output_format: str = "jsonl",
) -> List[APRInput]:
    """
    Run builder with default paths under project root.
    generation_dir: dir containing mbpp_gen.csv, humaneval_gen.csv, ds1k_gen.csv
    static_dir: dir containing ast_summary.csv, cfg_summary.csv, libapi_summary.csv
    dynamic_dir: dir containing dynamic_mbpp.jsonl, dynamic_humaneval.jsonl, dynamic_ds1000.jsonl
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    generation_dir = generation_dir or os.path.join(root, "APR", "ANALYSIS")
    static_dir = static_dir or os.path.join(root, "APR", "ANALYSIS")
    dynamic_dir = dynamic_dir or os.path.join(root, "Hallucination detection", "dynamic")

    gen_paths = {
        "MBPP": os.path.join(generation_dir, "mbpp_gen.csv"),
        "HumanEval": os.path.join(generation_dir, "humaneval_gen.csv"),
        "DS1000": os.path.join(generation_dir, "ds1k_gen.csv"),
    }
    ast_path = os.path.join(static_dir, "ast_summary.csv")
    cfg_path = os.path.join(static_dir, "cfg_summary.csv")
    lib_path = os.path.join(static_dir, "libapi_summary.csv")
    dyn_paths = {
        "MBPP": os.path.join(dynamic_dir, "dynamic_mbpp.jsonl"),
        "HumanEval": os.path.join(dynamic_dir, "dynamic_humaneval.jsonl"),
        "DS1000": os.path.join(dynamic_dir, "dynamic_ds1000.jsonl"),
    }

    apr_inputs = build_apr_input(gen_paths, ast_path, cfg_path, lib_path, dyn_paths)

    if output_path:
        if output_format.lower() == "parquet":
            write_apr_input_parquet(apr_inputs, output_path)
        else:
            write_apr_input_jsonl(apr_inputs, output_path)

    return apr_inputs
