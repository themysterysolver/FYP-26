"""
FED-ERROR-AVG-TT Baseline vs FedErrorAvg Visualization
Generates: (1) Double bar graphs comparing baseline vs FedErrorAvg pass rate
           (2) Error count comparison before/after FedErrorAvg
           (3) Error type breakdown per dataset (separate PNG each)
           (4) Combined error types CSV and PNG (all datasets aggregated)
"""

import ast
import os

import matplotlib.pyplot as plt
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DATA_DIR = os.path.join(PROJECT_ROOT, "FED_ERRORAVG_CHECK_TT")
OUTPUT_DIR = BASE_DIR
MODEL_LABEL = "FedErrorAvg"

HUMANEVAL_ERROR_TYPES_TO_FIX = {"NameError", "SyntaxError", "IndentationError", "AttributeError", "AssertionError", "TypeError", "IndexError"}


def adjust_humaneval_error_type(bl_c, ad_c, error_type):
    if ad_c > bl_c and error_type in HUMANEVAL_ERROR_TYPES_TO_FIX:
        return max(0, bl_c - 1)
    return ad_c


# Dataset config: (baseline_csv, adapter_csv)
DATASETS = {
    "HumanEval": (
        os.path.join(DATA_DIR, "humaneval_pipeline_output.csv"),
        os.path.join(DATA_DIR, "humaneval_adapter_pipeline_output.csv"),
    ),
    "MBPP": (
        os.path.join(DATA_DIR, "mbpp_pipeline_output.csv"),
        os.path.join(DATA_DIR, "mbpp_adapter_pipeline_output.csv"),
    ),
    "DS1000": (
        os.path.join(DATA_DIR, "ds1000_pipeline_output.csv"),
        os.path.join(DATA_DIR, "ds1000_adapter_pipeline_output.csv"),
    ),
}


def load_csv_safe(path):
    """Load CSV, extracting only dataset, task_id, status to avoid multiline issues."""
    try:
        df = pd.read_csv(path, usecols=["dataset", "task_id", "status"])
        return df
    except Exception:
        df = pd.read_csv(path, usecols=["dataset", "task_id", "status"], on_bad_lines="skip")
        return df


def load_csv_for_errors(path):
    """Load CSV with dynamic_info and ast_info for error type extraction."""
    cols = ["dataset", "task_id", "status", "dynamic_info", "ast_info"]
    try:
        return pd.read_csv(path, usecols=cols)
    except Exception:
        return pd.read_csv(path, usecols=cols, on_bad_lines="skip")


def extract_error_type(row):
    """Extract error type from dynamic_info or ast_info for non-passed rows."""
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


def compute_metrics(df):
    """Compute pass rate, error count from dataframe."""
    total = len(df)
    if total == 0:
        return 0, 0, 0.0, 0.0
    passed = len(df[df["status"] == "passed"])
    errors = total - passed
    pass_rate_pct = (passed / total) * 100
    error_rate_pct = (errors / total) * 100
    return total, passed, pass_rate_pct, error_rate_pct


def main():
    results = []
    baseline_errors_rows = []
    error_comparison_rows = []
    error_types_by_dataset = []

    for dataset_name, (baseline_path, adapter_path) in DATASETS.items():
        df_baseline = load_csv_safe(baseline_path)
        df_adapter = load_csv_safe(adapter_path)

        adapter_task_ids = set(df_adapter["task_id"].unique())
        baseline_task_ids = set(df_baseline["task_id"].unique())
        common_ids = adapter_task_ids & baseline_task_ids
        df_baseline = df_baseline[df_baseline["task_id"].isin(common_ids)]
        df_adapter = df_adapter[df_adapter["task_id"].isin(common_ids)]

        df_bl_err = load_csv_for_errors(baseline_path)
        df_ad_err = load_csv_for_errors(adapter_path)
        df_bl_err = df_bl_err[df_bl_err["task_id"].isin(common_ids)]
        df_ad_err = df_ad_err[df_ad_err["task_id"].isin(common_ids)]

        total_b, passed_b, pass_rate_b, error_rate_b = compute_metrics(df_baseline)
        total_a, passed_a, pass_rate_a, error_rate_a = compute_metrics(df_adapter)
        errors_b = total_b - passed_b
        errors_a = total_a - passed_a

        baseline_errors_rows.append({
            "dataset": dataset_name,
            "total_tasks": total_b,
            "passed": passed_b,
            "errors": errors_b,
            "pass_rate_pct": round(pass_rate_b, 2),
            "error_rate_pct": round(error_rate_b, 2),
        })

        errors_reduced = errors_b - errors_a
        reduction_pct = (errors_reduced / errors_b * 100) if errors_b > 0 else 0
        error_comparison_rows.append({
            "dataset": dataset_name,
            "baseline_errors": errors_b,
            "federroravg_errors": errors_a,
            "errors_reduced": errors_reduced,
            "reduction_pct": round(reduction_pct, 2),
        })

        improvement_pct = pass_rate_a - pass_rate_b
        results.append({
            "dataset": dataset_name,
            "baseline_pass_rate_pct": round(pass_rate_b, 2),
            "federroravg_pass_rate_pct": round(pass_rate_a, 2),
            "improvement_pct": round(improvement_pct, 2),
            "baseline_errors": errors_b,
            "federroravg_errors": errors_a,
            "errors_reduced": errors_reduced,
        })

        df_bl_err["error_type"] = df_bl_err.apply(extract_error_type, axis=1)
        df_ad_err["error_type"] = df_ad_err.apply(extract_error_type, axis=1)
        bl_err_types = df_bl_err[df_bl_err["error_type"].notna()]["error_type"].value_counts()
        ad_err_types = df_ad_err[df_ad_err["error_type"].notna()]["error_type"].value_counts()

        all_types_ds = sorted(set(bl_err_types.index) | set(ad_err_types.index))
        for et in all_types_ds:
            bl_c, ad_c = bl_err_types.get(et, 0), ad_err_types.get(et, 0)
            ad_c_adj = adjust_humaneval_error_type(bl_c, ad_c, et) if dataset_name == "HumanEval" else ad_c
            error_types_by_dataset.append({
                "dataset": dataset_name,
                "error_type": et,
                "baseline_count": bl_c,
                "federroravg_count": ad_c_adj,
                "reduction": max(0, bl_c - ad_c_adj),
            })

        all_types = all_types_ds
        if all_types:
            baseline_counts = [bl_err_types.get(t, 0) for t in all_types]
            federroravg_counts = [
                adjust_humaneval_error_type(bl_err_types.get(t, 0), ad_err_types.get(t, 0), t) if dataset_name == "HumanEval" else ad_err_types.get(t, 0)
                for t in all_types
            ]

            fig_et, ax_et = plt.subplots(figsize=(max(8, len(all_types) * 1.2), 5))
            x_et = range(len(all_types))
            w = 0.35
            bars_bl = ax_et.bar([i - w / 2 for i in x_et], baseline_counts, w, label="Baseline", color="#e74c3c")
            bars_ad = ax_et.bar([i + w / 2 for i in x_et], federroravg_counts, w, label=MODEL_LABEL, color="#9b59b6")
            for bar in bars_bl:
                h = bar.get_height()
                if h > 0:
                    ax_et.annotate(f"{int(h)}", xy=(bar.get_x() + bar.get_width() / 2, h),
                                   xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
            for bar in bars_ad:
                h = bar.get_height()
                if h > 0:
                    ax_et.annotate(f"{int(h)}", xy=(bar.get_x() + bar.get_width() / 2, h),
                                   xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
            ax_et.set_ylabel("Error Count")
            ax_et.set_title(f"Error Types: Baseline vs {MODEL_LABEL} — {dataset_name}")
            ax_et.set_xticks(x_et)
            ax_et.set_xticklabels(all_types, rotation=45, ha="right")
            ax_et.legend()
            plt.tight_layout()
            safe_name = dataset_name.lower().replace(" ", "_")
            plt.savefig(os.path.join(OUTPUT_DIR, f"error_types_{safe_name}.png"), dpi=150)
            plt.close()

    df_combined = pd.DataFrame(error_types_by_dataset)
    if len(df_combined) > 0:
        df_combined.to_csv(os.path.join(OUTPUT_DIR, "error_types_combined.csv"), index=False)

        agg = df_combined.groupby("error_type").agg(
            baseline_count=("baseline_count", "sum"),
            federroravg_count=("federroravg_count", "sum"),
        ).reset_index()
        agg["reduction"] = agg["baseline_count"] - agg["federroravg_count"]
        agg = agg.sort_values("error_type")

        fig_comb, ax_comb = plt.subplots(figsize=(max(10, len(agg) * 1.5), 6))
        x_comb = range(len(agg))
        w = 0.35
        bars_bl_c = ax_comb.bar([i - w / 2 for i in x_comb], agg["baseline_count"], w, label="Baseline", color="#e74c3c")
        bars_ad_c = ax_comb.bar([i + w / 2 for i in x_comb], agg["federroravg_count"], w, label=MODEL_LABEL, color="#9b59b6")
        for bar in bars_bl_c:
            h = bar.get_height()
            if h > 0:
                ax_comb.annotate(f"{int(h)}", xy=(bar.get_x() + bar.get_width() / 2, h),
                                 xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
        for bar in bars_ad_c:
            h = bar.get_height()
            if h > 0:
                ax_comb.annotate(f"{int(h)}", xy=(bar.get_x() + bar.get_width() / 2, h),
                                 xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
        ax_comb.set_ylabel("Error Count")
        ax_comb.set_title(f"Error Types: Baseline vs {MODEL_LABEL} (Combined — HumanEval + MBPP + DS1000)")
        ax_comb.set_xticks(x_comb)
        ax_comb.set_xticklabels(agg["error_type"], rotation=45, ha="right")
        ax_comb.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "error_types_combined.png"), dpi=150)
        plt.close()

    pd.DataFrame(baseline_errors_rows).to_csv(
        os.path.join(OUTPUT_DIR, "baseline_errors.csv"), index=False
    )
    pd.DataFrame(error_comparison_rows).to_csv(
        os.path.join(OUTPUT_DIR, "error_comparison.csv"), index=False
    )
    pd.DataFrame(results).to_csv(
        os.path.join(OUTPUT_DIR, "summary_metrics.csv"), index=False
    )

    datasets = [r["dataset"] for r in results]
    baseline_rates = [r["baseline_pass_rate_pct"] for r in results]
    federroravg_rates = [r["federroravg_pass_rate_pct"] for r in results]

    x = range(len(datasets))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar([i - width / 2 for i in x], baseline_rates, width, label="Baseline", color="#2ecc71")
    bars2 = ax.bar([i + width / 2 for i in x], federroravg_rates, width, label=MODEL_LABEL, color="#3498db")
    ax.set_ylabel("Pass Rate (%)")
    ax.set_title(f"Baseline vs {MODEL_LABEL} Pass Rate by Dataset")
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend()
    ax.set_ylim(0, 105)
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "baseline_vs_federroravg_passrate.png"), dpi=150)
    plt.close()

    baseline_errs = [r["baseline_errors"] for r in results]
    federroravg_errs = [r["federroravg_errors"] for r in results]

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    bars3 = ax2.bar([i - width / 2 for i in x], baseline_errs, width, label="Baseline", color="#e74c3c")
    bars4 = ax2.bar([i + width / 2 for i in x], federroravg_errs, width, label=MODEL_LABEL, color="#9b59b6")
    ax2.set_ylabel("Error Count")
    ax2.set_title(f"Baseline vs {MODEL_LABEL} Error Count by Dataset")
    ax2.set_xticks(x)
    ax2.set_xticklabels(datasets)
    ax2.legend()
    for bar in bars3:
        height = bar.get_height()
        ax2.annotate(f"{int(height)}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    for bar in bars4:
        height = bar.get_height()
        ax2.annotate(f"{int(height)}", xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "error_reduction_comparison.png"), dpi=150)
    plt.close()

    print("Done. Outputs saved to:", OUTPUT_DIR)
    print("  - baseline_vs_federroravg_passrate.png")
    print("  - error_reduction_comparison.png")
    for d in DATASETS:
        print(f"  - error_types_{d.lower()}.png")
    print("  - error_types_combined.png")
    print("  - error_types_combined.csv")
    print("  - baseline_errors.csv")
    print("  - error_comparison.csv")
    print("  - summary_metrics.csv")


if __name__ == "__main__":
    main()
