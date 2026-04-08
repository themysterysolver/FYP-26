"""
Stage breakdown bar graphs: AST, LIB_API, Dynamic.
Produces passed vs error counts per dataset for each stage, saved to subfolders.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
HALLUC_DIR = os.path.join(PROJECT_ROOT, "Hallucination detection")


def plot_and_save(datasets, passed, error, title, output_dir, error_label="Error"):
    """Create grouped bar chart and save to output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    x = range(len(datasets))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar([i - width / 2 for i in x], error, width, label=error_label, color="#e74c3c")
    bars2 = ax.bar([i + width / 2 for i in x], passed, width, label="Passed", color="#2ecc71")

    ax.set_ylabel("Count")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend()

    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax.annotate(
                f"{int(h)}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )
    for bar in bars2:
        h = bar.get_height()
        if h > 0:
            ax.annotate(
                f"{int(h)}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "passed_error_by_dataset.png"), dpi=150)
    plt.close()


def process_ast(base_dir):
    """Process AST stage."""
    csv_path = os.path.join(HALLUC_DIR, "static", "AST", "ast_summary.csv")
    output_dir = os.path.join(base_dir, "AST")
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(csv_path)
    passed_mask = (
        (df["ast_parsed"] == True)
        & (df["syntax_error"] == 0)
        & (df["indentation_error"] == 0)
        & (df["structural_error"] == 0)
    )
    df["status"] = passed_mask.map({True: "passed", False: "error"})

    counts = df.groupby(["dataset", "status"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["passed", "error"], fill_value=0)

    datasets = counts.index.tolist()
    passed = counts["passed"].tolist()
    error = counts["error"].tolist()

    summary = pd.DataFrame({
        "dataset": datasets,
        "passed": passed,
        "error": error,
        "total": [p + e for p, e in zip(passed, error)],
    })
    summary.to_csv(os.path.join(output_dir, "stage_summary.csv"), index=False)
    plot_and_save(
        datasets, passed, error,
        "AST: Passed vs Error Count by Dataset",
        output_dir,
    )
    return output_dir


def process_libapi(base_dir):
    """Process LIB_API stage."""
    csv_path = os.path.join(HALLUC_DIR, "static", "LIB_API", "libapi_summary.csv")
    output_dir = os.path.join(base_dir, "LIB_API")
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(csv_path)
    passed_mask = df["total_libapi_errors"] == 0
    df["status"] = passed_mask.map({True: "passed", False: "error"})

    counts = df.groupby(["dataset", "status"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["passed", "error"], fill_value=0)

    datasets = counts.index.tolist()
    passed = counts["passed"].tolist()
    error = counts["error"].tolist()

    summary = pd.DataFrame({
        "dataset": datasets,
        "passed": passed,
        "error": error,
        "total": [p + e for p, e in zip(passed, error)],
    })
    summary.to_csv(os.path.join(output_dir, "stage_summary.csv"), index=False)
    plot_and_save(
        datasets, passed, error,
        "LIB_API: Passed vs Error Count by Dataset",
        output_dir,
    )
    return output_dir


def process_dynamic(base_dir):
    """Process Dynamic stage."""
    csv_path = os.path.join(HALLUC_DIR, "dynamic", "dynamic_execution_results.csv")
    output_dir = os.path.join(base_dir, "DYNAMIC")
    os.makedirs(output_dir, exist_ok=True)

    df = pd.read_csv(csv_path, usecols=["dataset", "status"])
    counts = df.groupby(["dataset", "status"]).size().unstack(fill_value=0)
    if "passed" not in counts.columns:
        counts["passed"] = 0
    if "failed" not in counts.columns:
        counts["failed"] = 0

    datasets = counts.index.tolist()
    passed = counts["passed"].tolist()
    error = counts["failed"].tolist()

    summary = pd.DataFrame({
        "dataset": datasets,
        "passed": passed,
        "failed": error,
        "total": [p + e for p, e in zip(passed, error)],
    })
    summary.to_csv(os.path.join(output_dir, "stage_summary.csv"), index=False)
    plot_and_save(
        datasets, passed, error,
        "Dynamic: Passed vs Failed Count by Dataset",
        output_dir,
        error_label="Failed",
    )
    return output_dir


def main():
    dirs = [
        process_ast(BASE_DIR),
        process_libapi(BASE_DIR),
        process_dynamic(BASE_DIR),
    ]
    print("Done. Outputs saved to:")
    for d in dirs:
        print(f"  {d}/")
        print(f"    - passed_error_by_dataset.png")
        print(f"    - stage_summary.csv")


if __name__ == "__main__":
    main()
