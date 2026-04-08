"""
Compute CodeBLEU similarity between generated code (1st pass) and canonical solution.

Processes pipeline output CSVs, adds codebleu_1st_pass column, and saves results.
Can merge canonical_solution from HuggingFace datasets when missing in CSV.

Usage:
  python compute_codebleu.py --input-dir FED_AVG_CHECK --output-dir VIS/CodeBLEU/scores
  python compute_codebleu.py --process-all  # Process both FED_AVG_CHECK and FED_ERRORAVG_CHECK
"""

import argparse
import os

import pandas as pd

from codebleu import calc_codebleu

# Project root (parent of VIS)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIS_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(VIS_DIR)

def get_canonical_from_hf(dataset_name: str) -> pd.DataFrame:
    """Load canonical solutions from HuggingFace datasets."""
    from datasets import load_dataset

    if dataset_name == "HumanEval":
        ds = load_dataset("openai/openai_humaneval", split="test")
        df = ds.to_pandas()
        return df[["task_id", "canonical_solution"]]
    if dataset_name == "MBPP":
        ds = load_dataset("google-research-datasets/mbpp", "sanitized", split="train")
        df = ds.to_pandas()
        df["task_id"] = df["task_id"].astype(str)
        return df[["task_id", "code"]].rename(columns={"code": "canonical_solution"})
    if dataset_name == "DS1000":
        ds = load_dataset("xlangai/DS-1000", split="test")
        df = ds.to_pandas()
        df["task_id"] = [f"DS{str(i).zfill(4)}" for i in range(len(df))]
        return df[["task_id", "reference_code"]].rename(
            columns={"reference_code": "canonical_solution"}
        )
    raise ValueError(f"Unknown dataset: {dataset_name}")


def _bleu_fallback(ref: str, pred: str) -> float:
    """Fallback: simple n-gram overlap when CodeBLEU fails (e.g. tree-sitter compat)."""
    from collections import Counter
    def tokenize(s):
        return s.replace("\n", " ").replace("\r", " ").split()
    r_tok, p_tok = tokenize(ref), tokenize(pred)
    if not r_tok or not p_tok:
        return 0.0
    p_counts = Counter(p_tok)
    matches = sum((Counter(r_tok) & p_counts).values())
    return matches / len(p_tok) if p_tok else 0.0


def compute_codebleu_for_row(generated_code: str, canonical_solution: str) -> float | None:
    """
    Compute CodeBLEU score for a single (generated, canonical) pair.
    Returns float or None on failure. Falls back to simple BLEU if CodeBLEU raises.
    Exposed for pipeline integration.
    """
    gen = (generated_code or "").strip()
    canon = (canonical_solution or "").strip()
    if not gen or not canon:
        return None
    try:
        result = calc_codebleu([canon], [gen], lang="python")
        return float(result.get("codebleu", 0.0))
    except Exception:
        try:
            return _bleu_fallback(canon, gen)
        except Exception:
            return None


def load_csv_with_canonical(
    csv_path: str, dataset_name: str, canon_map: dict | None = None
) -> pd.DataFrame:
    """Load pipeline CSV and ensure canonical_solution column exists."""
    try:
        df = pd.read_csv(csv_path, on_bad_lines="skip")
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return df

    required = ["dataset", "task_id", "status"]
    for c in required:
        if c not in df.columns:
            df[c] = ""

    if "generated_code" not in df.columns:
        df["generated_code"] = ""
    if "dynamic_info" in df.columns:
        # Some CSVs nest generated_code inside dynamic_info
        def _extract_gen(row):
            gen = str(row.get("generated_code", "") or "").strip()
            if gen:
                return gen
            dinfo = str(row.get("dynamic_info", "") or "")
            if "'generated_code':" in dinfo or '"generated_code":' in dinfo:
                try:
                    import ast
                    d = ast.literal_eval(dinfo)
                    if isinstance(d, dict):
                        return str(d.get("generated_code", "") or "").strip()
                except Exception:
                    pass
            return gen
        df["generated_code"] = df.apply(_extract_gen, axis=1)
    df["generated_code"] = df["generated_code"].fillna("")
    df["task_id"] = df["task_id"].astype(str)

    if "canonical_solution" not in df.columns and canon_map is not None:
        canon_df = canon_map.get(dataset_name)
        if canon_df is not None:
            canon_df = canon_df.copy()
            canon_df["task_id"] = canon_df["task_id"].astype(str)
            df = df.merge(canon_df, on="task_id", how="left")

    if "canonical_solution" not in df.columns:
        df["canonical_solution"] = ""
    else:
        df["canonical_solution"] = df["canonical_solution"].fillna("")

    return df


def process_csv(
    csv_path: str,
    output_dir: str,
    model_label: str,
    dataset_name: str,
    canon_map: dict | None = None,
    suffix: str = "",
) -> str | None:
    """
    Process a single pipeline CSV: compute CodeBLEU, save augmented scores.
    Returns path to saved file or None on failure.
    """
    if not os.path.isfile(csv_path):
        return None

    df = load_csv_with_canonical(csv_path, dataset_name, canon_map)
    if df.empty or "generated_code" not in df.columns:
        return None

    scores = []
    for _, row in df.iterrows():
        gen = str(row.get("generated_code", "") or "")
        canon = str(row.get("canonical_solution", "") or "")
        score = compute_codebleu_for_row(gen, canon)
        scores.append(score if score is not None else float("nan"))

    df["codebleu_1st_pass"] = scores

    out_df = df[["dataset", "task_id", "status", "codebleu_1st_pass"]].copy()
    safe_label = model_label.lower().replace(" ", "_")
    safe_dataset = dataset_name.lower().replace(" ", "_")
    name = f"codebleu_scores_{safe_dataset}_{safe_label}"
    if suffix:
        name = f"{name}_{suffix}"
    out_path = os.path.join(output_dir, f"{name}.csv")
    os.makedirs(output_dir, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Compute CodeBLEU between generated and canonical code for pipeline outputs."
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Directory containing pipeline CSVs (e.g. FED_AVG_CHECK, FED_ERRORAVG_CHECK)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(SCRIPT_DIR, "scores"),
        help="Directory to save codebleu_scores_*.csv",
    )
    parser.add_argument(
        "--process-all",
        action="store_true",
        help="Process FED_AVG_CHECK, FED_ERRORAVG_CHECK (Train) and FED_AVG_CHECK_TT, FED_ERRORAVG_CHECK_TT (TT)",
    )
    args = parser.parse_args()

    if args.process_all:
        dirs_to_process = [
            (os.path.join(PROJECT_ROOT, "FED_AVG_CHECK"), ["baseline", "fedavg"], "train"),
            (os.path.join(PROJECT_ROOT, "FED_ERRORAVG_CHECK"), ["federroravg"], "train"),
            (os.path.join(PROJECT_ROOT, "FED_AVG_CHECK_TT"), ["baseline", "fedavg"], "tt"),
            (os.path.join(PROJECT_ROOT, "FED_ERRORAVG_CHECK_TT"), ["federroravg"], "tt"),
        ]
    elif args.input_dir:
        inp = os.path.abspath(args.input_dir)
        suffix = "tt" if "TT" in inp.upper() or "_TT" in inp else "train"
        if "FED_ERROR" in inp.upper():
            dirs_to_process = [(inp, ["federroravg"], suffix)]
        else:
            dirs_to_process = [(inp, ["baseline", "fedavg"], suffix)]
    else:
        parser.error("Provide --input-dir or --process-all")

    print("Loading canonical solutions from HuggingFace (if needed)...")
    canon_map = {
        "HumanEval": get_canonical_from_hf("HumanEval"),
        "MBPP": get_canonical_from_hf("MBPP"),
        "DS1000": get_canonical_from_hf("DS1000"),
    }

    file_map = {
        "baseline": {
            "HumanEval": "humaneval_pipeline_output.csv",
            "MBPP": "mbpp_pipeline_output.csv",
            "DS1000": "ds1000_pipeline_output.csv",
        },
        "fedavg": {
            "HumanEval": "humaneval_adapter_pipeline_output.csv",
            "MBPP": "mbpp_adapter_pipeline_output.csv",
            "DS1000": "ds1000_adapter_pipeline_output.csv",
        },
        "federroravg": {
            "HumanEval": "humaneval_adapter_pipeline_output.csv",
            "MBPP": "mbpp_adapter_pipeline_output.csv",
            "DS1000": "ds1000_adapter_pipeline_output.csv",
        },
    }

    output_dir = os.path.abspath(args.output_dir)
    saved = []
    for item in dirs_to_process:
        input_dir = item[0]
        models = item[1]
        suffix = item[2] if len(item) > 2 else ""
        for model in models:
            for dataset_name, fname in file_map[model].items():
                csv_path = os.path.join(input_dir, fname)
                out_path = process_csv(
                    csv_path, output_dir, model, dataset_name, canon_map, suffix=suffix
                )
                if out_path:
                    saved.append(out_path)
                    print(f"  Saved: {out_path}")

    print(f"\nDone. {len(saved)} files saved to {output_dir}")


if __name__ == "__main__":
    main()
