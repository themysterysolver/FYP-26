import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QWEN_DIR = os.path.join(ROOT, "Code generation", "Qwen")
STATIC_DIR = os.path.join(ROOT, "Hallucination detection", "static")
DYNAMIC_DIR = os.path.join(ROOT, "Hallucination detection", "dynamic")
OUT_DIR = os.path.join(ROOT, "APR", "repair_context_integration")


DATASETS: Dict[str, Dict[str, Any]] = {
    "DS1000": {
        "gen_csv": os.path.join(QWEN_DIR, "ds1k_gen.csv"),
        "task_id_column": "task_id",
        "code_column": "full_code",
        "ast_jsonl": os.path.join(STATIC_DIR, "AST", "ast_ds1000.jsonl"),
        "cfg_jsonl": os.path.join(STATIC_DIR, "CFG", "cfg_ds1000.jsonl"),
        "libapi_jsonl": os.path.join(STATIC_DIR, "LIB_API", "libapi_ds1000.jsonl"),
        "dyn_jsonl": os.path.join(DYNAMIC_DIR, "dynamic_ds1000.jsonl"),
    },
    "HumanEval": {
        "gen_csv": os.path.join(QWEN_DIR, "humaneval_gen.csv"),
        "task_id_column": "task_id",
        "code_column": "GENERATED_CODE",
        "ast_jsonl": os.path.join(STATIC_DIR, "AST", "ast_humaneval.jsonl"),
        "cfg_jsonl": os.path.join(STATIC_DIR, "CFG", "cfg_humaneval.jsonl"),
        "libapi_jsonl": os.path.join(STATIC_DIR, "LIB_API", "libapi_humaneval.jsonl"),
        "dyn_jsonl": os.path.join(DYNAMIC_DIR, "dynamic_humaneval.jsonl"),
    },
    "MBPP": {
        "gen_csv": os.path.join(QWEN_DIR, "mbpp_gen.csv"),
        "task_id_column": "task_id",
        "code_column": "GENERATED_CODE",
        "ast_jsonl": os.path.join(STATIC_DIR, "AST", "ast_mbpp.jsonl"),
        "cfg_jsonl": os.path.join(STATIC_DIR, "CFG", "cfg_mbpp.jsonl"),
        "libapi_jsonl": os.path.join(STATIC_DIR, "LIB_API", "libapi_mbpp.jsonl"),
        "dyn_jsonl": os.path.join(DYNAMIC_DIR, "dynamic_mbpp.jsonl"),
    },
}


def _first_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"\d+", text)
    if not match:
        return None
    return int(match.group(0))


def normalize_task_id(dataset: str, raw_task_id: Any) -> str:
    idx = _first_int(raw_task_id)
    if dataset == "DS1000":
        if idx is None:
            return str(raw_task_id).strip()
        return f"DS{idx:04d}"
    if dataset == "HumanEval":
        if idx is None:
            return str(raw_task_id).strip()
        return f"HumanEval/{idx}"
    if dataset == "MBPP":
        if idx is None:
            return str(raw_task_id).strip()
        return str(idx)
    return str(raw_task_id).strip()


def load_jsonl_index(path: str, dataset: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            key = normalize_task_id(dataset, obj.get("task_id"))
            index[key] = obj
    return index


def _clean_error_type(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _libapi_primary_error(libapi_row: Dict[str, Any]) -> Optional[str]:
    if not libapi_row:
        return None
    details = libapi_row.get("libapi_details") or []
    if isinstance(details, list) and details:
        first_type = details[0].get("type")
        if first_type:
            return str(first_type)
    ranking = [
        ("module_not_found", int(libapi_row.get("module_not_found", 0) or 0)),
        ("name_error", int(libapi_row.get("name_error", 0) or 0)),
        ("attribute_error", int(libapi_row.get("attribute_error", 0) or 0)),
        ("type_error", int(libapi_row.get("type_error", 0) or 0)),
    ]
    ranking.sort(key=lambda item: item[1], reverse=True)
    if ranking and ranking[0][1] > 0:
        return ranking[0][0]
    return None


def _cfg_primary_error(cfg_row: Dict[str, Any]) -> Optional[str]:
    if not cfg_row:
        return None
    if int(cfg_row.get("missing_return", 0) or 0) > 0:
        return "missing_return"
    if int(cfg_row.get("unreachable_code", 0) or 0) > 0:
        return "unreachable_code"
    return None


def derive_error_type(
    dynamic_row: Dict[str, Any],
    ast_row: Dict[str, Any],
    libapi_row: Dict[str, Any],
    cfg_row: Dict[str, Any],
) -> Tuple[str, str]:
    dyn_type = _clean_error_type(dynamic_row.get("error_type")) if dynamic_row else None
    dyn_subtype = _clean_error_type(dynamic_row.get("hallucination_subtype")) if dynamic_row else None

    if dyn_type and dyn_type not in {"none", "no_tests"}:
        if dyn_type == "logical" and dyn_subtype and dyn_subtype != "wrong_output":
            return dyn_subtype, "dynamic"
        return dyn_type, "dynamic"

    ast_type = _clean_error_type(ast_row.get("error_type")) if ast_row else None
    if ast_type:
        return ast_type, "ast"

    libapi_type = _libapi_primary_error(libapi_row or {})
    if libapi_type:
        return libapi_type, "libapi"

    cfg_type = _cfg_primary_error(cfg_row or {})
    if cfg_type:
        return cfg_type, "cfg"

    return "none", "none"


def _safe_int(value: Any) -> Optional[int]:
    num = _first_int(value)
    return num


def derive_error_line_number(
    ast_row: Dict[str, Any], libapi_row: Dict[str, Any], cfg_row: Dict[str, Any]
) -> Optional[int]:
    if ast_row:
        ast_line = _safe_int(ast_row.get("line"))
        if ast_line is not None:
            return ast_line

    if libapi_row:
        details = libapi_row.get("libapi_details") or []
        if isinstance(details, list):
            for detail in details:
                line = _safe_int(detail.get("line"))
                if line is not None:
                    return line

    if cfg_row:
        details = cfg_row.get("cfg_details") or []
        if isinstance(details, list):
            for detail in details:
                line = _safe_int(detail.get("start_line"))
                if line is None:
                    line = _safe_int(detail.get("line"))
                if line is not None:
                    return line
    return None


def _serialize_failure(failure: Dict[str, Any]) -> str:
    parts = [
        f"test_id={failure.get('test_id')}",
        f"type={failure.get('type')}",
        f"subtype={failure.get('subtype')}",
        f"message={failure.get('message')}",
        f"input={failure.get('input')}",
        f"expected={failure.get('expected')}",
        f"actual={failure.get('actual')}",
        f"source={failure.get('source')}",
    ]
    return " | ".join(parts)


def derive_error_stack_trace(dynamic_row: Dict[str, Any]) -> Optional[str]:
    if not dynamic_row:
        return None

    failures = dynamic_row.get("failures") or []
    if isinstance(failures, list) and failures:
        return _serialize_failure(failures[0])

    stderr = dynamic_row.get("stderr")
    if isinstance(stderr, str) and stderr.strip():
        return stderr.strip()

    stdout = dynamic_row.get("stdout")
    if isinstance(stdout, str) and stdout.strip():
        return stdout.strip()

    return None


def build_dataset_rows(dataset: str, cfg: Dict[str, Any]) -> pd.DataFrame:
    gen_df = pd.read_csv(cfg["gen_csv"])
    ast_idx = load_jsonl_index(cfg["ast_jsonl"], dataset)
    cfg_idx = load_jsonl_index(cfg["cfg_jsonl"], dataset)
    libapi_idx = load_jsonl_index(cfg["libapi_jsonl"], dataset)
    dyn_idx = load_jsonl_index(cfg["dyn_jsonl"], dataset)

    task_col = cfg["task_id_column"]
    code_col = cfg["code_column"]
    gen_df["dataset"] = dataset
    gen_df["task_id_raw"] = gen_df[task_col]
    gen_df["task_id_norm"] = gen_df[task_col].apply(lambda value: normalize_task_id(dataset, value))
    gen_df["generated_code"] = gen_df[code_col]

    output_rows: List[Dict[str, Any]] = []
    for row in gen_df.to_dict(orient="records"):
        key = row["task_id_norm"]
        ast_row = ast_idx.get(key, {})
        cfg_row = cfg_idx.get(key, {})
        libapi_row = libapi_idx.get(key, {})
        dyn_row = dyn_idx.get(key, {})

        error_type, error_source = derive_error_type(dyn_row, ast_row, libapi_row, cfg_row)
        error_line = derive_error_line_number(ast_row, libapi_row, cfg_row)
        error_stack_trace = derive_error_stack_trace(dyn_row)

        merged = {
            "dataset": dataset,
            "task_id": row["task_id_raw"],
            "task_id_normalized": key,
            "generated_code": row.get("generated_code"),
            "error_type": error_type,
            "error_line_number": error_line,
            "error_stack_trace": error_stack_trace,
            "error_stack_tract": error_stack_trace,
            "error_source": error_source,
            "dynamic_status": dyn_row.get("status"),
            "dynamic_error_type": dyn_row.get("error_type"),
            "dynamic_hallucination_subtype": dyn_row.get("hallucination_subtype"),
            "ast_error_type": ast_row.get("error_type"),
            "ast_line": ast_row.get("line"),
            "ast_message": ast_row.get("message"),
            "libapi_total_errors": libapi_row.get("total_libapi_errors"),
            "cfg_missing_return": cfg_row.get("missing_return"),
            "cfg_unreachable_code": cfg_row.get("unreachable_code"),
            "raw_dynamic_failures": json.dumps(dyn_row.get("failures", []), ensure_ascii=False),
            "raw_ast_details": json.dumps(ast_row.get("structural_details", []), ensure_ascii=False),
            "raw_cfg_details": json.dumps(cfg_row.get("cfg_details", []), ensure_ascii=False),
            "raw_libapi_details": json.dumps(libapi_row.get("libapi_details", []), ensure_ascii=False),
        }

        # Keep all original generation fields with a clear prefix.
        for col, value in row.items():
            if col in {"dataset", "task_id_raw", "task_id_norm", "generated_code"}:
                continue
            merged[f"gen_{col}"] = value
        output_rows.append(merged)

    return pd.DataFrame(output_rows)


def write_jsonl(df: pd.DataFrame, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for obj in df.to_dict(orient="records"):
            handle.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = [build_dataset_rows(dataset, cfg) for dataset, cfg in DATASETS.items()]
    merged_df = pd.concat(frames, ignore_index=True)

    jsonl_path = os.path.join(OUT_DIR, "repair_context_qwen.jsonl")
    csv_path = os.path.join(OUT_DIR, "repair_context_qwen.csv")
    write_jsonl(merged_df, jsonl_path)
    merged_df.to_csv(csv_path, index=False)

    print("Generated:")
    print(f"- {jsonl_path}")
    print(f"- {csv_path}")
    print(f"Total rows: {len(merged_df)}")
    print("\nField null rates:")
    for field in ["error_type", "error_line_number", "error_stack_trace"]:
        null_rate = float(merged_df[field].isna().mean()) if field in merged_df else 1.0
        print(f"- {field}: {null_rate:.4f}")

    print("\nRows per dataset:")
    for dataset, count in merged_df["dataset"].value_counts().sort_index().items():
        print(f"- {dataset}: {int(count)}")


if __name__ == "__main__":
    run()
