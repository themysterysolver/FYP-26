"""
Hallucination and Passed Count Bar Graph
Reads fault_information.csv, produces grouped bar chart of hallucination vs passed counts per dataset.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
FAULT_CSV = os.path.join(PROJECT_ROOT, "Hallucination detection", "Fault Information", "fault_information.csv")
OUTPUT_DIR = BASE_DIR


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = pd.read_csv(FAULT_CSV, usecols=["dataset", "status"])
    counts = df.groupby(["dataset", "status"]).size().unstack(fill_value=0)

    if "hallucinated" not in counts.columns:
        counts["hallucinated"] = 0
    if "passed" not in counts.columns:
        counts["passed"] = 0

    datasets = counts.index.tolist()
    hallucinated = counts["hallucinated"].tolist()
    passed_counts = counts["passed"].tolist()

    summary = pd.DataFrame({
        "dataset": datasets,
        "hallucinated": hallucinated,
        "passed": passed_counts,
        "total": [h + p for h, p in zip(hallucinated, passed_counts)],
    })
    summary.to_csv(os.path.join(OUTPUT_DIR, "hallucination_passed_summary.csv"), index=False)

    x = range(len(datasets))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar([i - width / 2 for i in x], hallucinated, width, label="Hallucinated", color="#e74c3c")
    bars2 = ax.bar([i + width / 2 for i in x], passed_counts, width, label="Passed", color="#2ecc71")

    ax.set_ylabel("Count")
    ax.set_title("Hallucination and Pass Count by Dataset")
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
    plt.savefig(os.path.join(OUTPUT_DIR, "hallucination_passed_by_dataset.png"), dpi=150)
    plt.close()

    print("Done. Outputs saved to:", OUTPUT_DIR)
    print("  - hallucination_passed_by_dataset.png")
    print("  - hallucination_passed_summary.csv")


if __name__ == "__main__":
    main()
