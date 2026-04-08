"""
Error types occurrence CSV: extract all error types from ast_info, cfg_info, lib_info, dynamic_info,
count occurrences per dataset, produce CSV with Total column and Total row.
"""

import ast
import json
import os
import pandas as pd
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
FAULT_CSV = os.path.join(PROJECT_ROOT, "Hallucination detection", "Fault Information", "fault_information.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "error_types_by_dataset.csv")
DATASETS_ORDER = ["DS1000", "HumanEval", "MBPP"]


def safe_parse_json(s):
    """Parse JSON or Python literal."""
    if not s or (isinstance(s, str) and str(s).strip() in ("", "nan", "[]", "{}")):
        return None
    s = str(s).strip()
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        pass
    return None


def extract_error_types_from_row(row):
    """Extract all error type strings from a hallucinated row. Returns list of (possibly duplicated) error types."""
    types = []
    dataset = row.get("dataset", "")

    # AST: {"type": "SyntaxError", ...}
    ast_info = safe_parse_json(row.get("ast_info"))
    if ast_info and isinstance(ast_info, dict):
        t = ast_info.get("type")
        if t and str(t).strip():
            types.append(str(t).strip())

    # CFG: [{'type': 'missing_return', ...}, ...]
    cfg_info = safe_parse_json(row.get("cfg_info"))
    if cfg_info and isinstance(cfg_info, list):
        for item in cfg_info:
            if isinstance(item, dict):
                t = item.get("type")
                if t and str(t).strip():
                    types.append(str(t).strip())

    # LIB: list of dicts with "type" key (name_error, attribute_error, etc.)
    lib_info = safe_parse_json(row.get("lib_info"))
    if lib_info and isinstance(lib_info, list):
        for item in lib_info:
            if isinstance(item, dict):
                t = item.get("type")
                if t and str(t).strip():
                    types.append(str(t).strip())

    # Dynamic: {"error_type": "AssertionError", ...}
    dyn_info = safe_parse_json(row.get("dynamic_info"))
    if dyn_info and isinstance(dyn_info, dict):
        t = dyn_info.get("error_type")
        if t and str(t).strip():
            types.append(str(t).strip())

    return dataset, types


def main():
    df = pd.read_csv(FAULT_CSV)
    hallucinated = df[df["status"] == "hallucinated"]

    # Count: error_type -> {dataset: count}
    counts = defaultdict(lambda: defaultdict(int))

    for _, row in hallucinated.iterrows():
        dataset, error_types = extract_error_types_from_row(row)
        if dataset not in DATASETS_ORDER:
            continue
        for et in error_types:
            counts[et][dataset] += 1

    # Build table: rows = error types (sorted), cols = DS1000, HumanEval, MBPP, Total
    all_types = sorted(counts.keys())
    rows = []

    for et in all_types:
        row_data = {"Error_Type": et}
        row_total = 0
        for ds in DATASETS_ORDER:
            c = counts[et][ds]
            row_data[ds] = c
            row_total += c
        row_data["Total"] = row_total
        rows.append(row_data)

    # Total row: sum of each column
    total_row = {"Error_Type": "Total"}
    for ds in DATASETS_ORDER:
        total_row[ds] = sum(r[ds] for r in rows)
    total_row["Total"] = sum(r["Total"] for r in rows)
    rows.append(total_row)

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUTPUT_CSV, index=False)
    print("Saved to:", OUTPUT_CSV)
    print()
    print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
