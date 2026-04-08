"""
Error Types: Baseline vs FedAvg vs FedErrorAvg (Train)
Generates CSVs with columns: error_type | baseline_count | fedavg_count | federroravg_count | reduction
- One CSV per dataset (HumanEval, MBPP, DS1000)
- One combined CSV for all datasets
Uses FED_AVG_CHECK (baseline + FedAvg) and FED_ERRORAVG_CHECK (FedErrorAvg).
"""

import ast
import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR_FEDAVG = os.path.join(PROJECT_ROOT, "FED_AVG_CHECK")
DATA_DIR_FEDERROR = os.path.join(PROJECT_ROOT, "FED_ERRORAVG_CHECK")
OUTPUT_DIR = BASE_DIR

DATASETS = {
    "HumanEval": (
        os.path.join(DATA_DIR_FEDAVG, "humaneval_pipeline_output.csv"),
        os.path.join(DATA_DIR_FEDAVG, "humaneval_adapter_pipeline_output.csv"),
        os.path.join(DATA_DIR_FEDERROR, "humaneval_adapter_pipeline_output.csv"),
    ),
    "MBPP": (
        os.path.join(DATA_DIR_FEDAVG, "mbpp_pipeline_output.csv"),
        os.path.join(DATA_DIR_FEDAVG, "mbpp_adapter_pipeline_output.csv"),
        os.path.join(DATA_DIR_FEDERROR, "mbpp_adapter_pipeline_output.csv"),
    ),
    "DS1000": (
        os.path.join(DATA_DIR_FEDAVG, "ds1000_pipeline_output.csv"),
        os.path.join(DATA_DIR_FEDAVG, "ds1000_adapter_pipeline_output.csv"),
        os.path.join(DATA_DIR_FEDERROR, "ds1000_adapter_pipeline_output.csv"),
    ),
}


def load_csv_for_errors(path):
    cols = ["dataset", "task_id", "status", "dynamic_info", "ast_info"]
    try:
        return pd.read_csv(path, usecols=cols)
    except Exception:
        return pd.read_csv(path, usecols=cols, on_bad_lines="skip")


def extract_error_type(row):
    if row["status"] == "passed":
        return None
    err = None
    try:
        dinfo = ast.literal_eval(str(row.get("dynamic_info", "{}")))
        err = dinfo.get("error_type", "") or None
    except (ValueError, SyntaxError):
        pass
    if not err:
        try:
            ainfo = ast.literal_eval(str(row.get("ast_info", "{}")))
            ast_errs = ainfo.get("ast_errors", [])
            if ast_errs:
                err = ast_errs[0].get("type", "SyntaxError")
        except (ValueError, SyntaxError):
            pass
    return err or "Other"


def main():
    all_rows = []

    for dataset_name, (baseline_path, fedavg_path, federror_path) in DATASETS.items():
        df_bl = load_csv_for_errors(baseline_path)
        df_fa = load_csv_for_errors(fedavg_path)
        df_fe = load_csv_for_errors(federror_path)

        ids_b = set(df_bl["task_id"].unique())
        ids_fa = set(df_fa["task_id"].unique())
        ids_fe = set(df_fe["task_id"].unique())
        common_ids = ids_b & ids_fa & ids_fe

        df_bl = df_bl[df_bl["task_id"].isin(common_ids)]
        df_fa = df_fa[df_fa["task_id"].isin(common_ids)]
        df_fe = df_fe[df_fe["task_id"].isin(common_ids)]

        df_bl["error_type"] = df_bl.apply(extract_error_type, axis=1)
        df_fa["error_type"] = df_fa.apply(extract_error_type, axis=1)
        df_fe["error_type"] = df_fe.apply(extract_error_type, axis=1)

        bl_counts = df_bl[df_bl["error_type"].notna()]["error_type"].value_counts()
        fa_counts = df_fa[df_fa["error_type"].notna()]["error_type"].value_counts()
        fe_counts = df_fe[df_fe["error_type"].notna()]["error_type"].value_counts()

        all_types = sorted(set(bl_counts.index) | set(fa_counts.index) | set(fe_counts.index))

        rows = []
        for et in all_types:
            bl = bl_counts.get(et, 0)
            fa = fa_counts.get(et, 0)
            fe = fe_counts.get(et, 0)
            reduction = max(0, bl - fe)
            rows.append({
                "error_type": et,
                "baseline_count": bl,
                "fedavg_count": fa,
                "federroravg_count": fe,
                "reduction": reduction,
            })
            all_rows.append({
                "dataset": dataset_name,
                "error_type": et,
                "baseline_count": bl,
                "fedavg_count": fa,
                "federroravg_count": fe,
                "reduction": reduction,
            })

        df_ds = pd.DataFrame(rows)
        safe_name = dataset_name.lower()
        out_path = os.path.join(OUTPUT_DIR, f"error_types_{safe_name}.csv")
        df_ds.to_csv(out_path, index=False)
        print(f"  - error_types_{safe_name}.csv ({len(rows)} rows)")

    df_all = pd.DataFrame(all_rows)
    all_path = os.path.join(OUTPUT_DIR, "error_types_all.csv")
    df_all.to_csv(all_path, index=False)
    print(f"  - error_types_all.csv ({len(all_rows)} rows)")

    # Aggregated "all" table: error_type | baseline | fedavg | federroravg | reduction (summed across datasets)
    agg = df_all.groupby("error_type").agg(
        baseline_count=("baseline_count", "sum"),
        fedavg_count=("fedavg_count", "sum"),
        federroravg_count=("federroravg_count", "sum"),
    ).reset_index()
    agg["reduction"] = (agg["baseline_count"] - agg["federroravg_count"]).clip(lower=0).astype(int)
    agg = agg.sort_values("error_type")
    agg_path = os.path.join(OUTPUT_DIR, "error_types_combined.csv")
    agg.to_csv(agg_path, index=False)
    print(f"  - error_types_combined.csv (aggregated across datasets)")

    print("Done. Outputs saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
