"""
CodeBLEU Fed Comparison: Baseline vs FedAvg vs FedErrorAvg (Train and TT)

Loads CodeBLEU scores from codebleu_scores_*.csv, compares across models,
produces summary CSVs and bar charts.

Run compute_codebleu.py --process-all first to generate scores.

Usage:
  python codebleu_fed_comparison.py
  python codebleu_fed_comparison.py --scores-dir VIS/CodeBLEU/scores
"""

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIS_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(VIS_DIR)
DEFAULT_SCORES_DIR = os.path.join(SCRIPT_DIR, "scores")
OUTPUT_DIR = SCRIPT_DIR

# Dataset -> (baseline_file, fedavg_file, federroravg_file) for train and tt
def get_score_paths(scores_dir: str, suffix: str) -> dict:
    """Return paths for baseline, fedavg, federroravg per dataset."""
    base = lambda d, m: os.path.join(scores_dir, f"codebleu_scores_{d}_{m}_{suffix}.csv")
    return {
        "HumanEval": (
            base("humaneval", "baseline"),
            base("humaneval", "fedavg"),
            base("humaneval", "federroravg"),
        ),
        "MBPP": (
            base("mbpp", "baseline"),
            base("mbpp", "fedavg"),
            base("mbpp", "federroravg"),
        ),
        "DS1000": (
            base("ds1000", "baseline"),
            base("ds1000", "fedavg"),
            base("ds1000", "federroravg"),
        ),
    }


def load_codebleu_df(path: str) -> pd.DataFrame | None:
    """Load CodeBLEU scores CSV. Returns None if file missing."""
    if not os.path.isfile(path):
        return None
    try:
        df = pd.read_csv(path, usecols=["dataset", "task_id", "status", "codebleu_1st_pass"])
        df["task_id"] = df["task_id"].astype(str)
        return df
    except Exception:
        return None


def compute_comparison(scores_dir: str, suffix: str):
    """Compute mean CodeBLEU per dataset for baseline, fedavg, federroravg."""
    paths = get_score_paths(scores_dir, suffix)
    results = []

    for dataset_name, (bl_path, fa_path, fe_path) in paths.items():
        df_b = load_codebleu_df(bl_path)
        df_fa = load_codebleu_df(fa_path)
        df_fe = load_codebleu_df(fe_path)

        if df_b is None or df_fa is None or df_fe is None:
            continue

        ids_b = set(df_b["task_id"].unique())
        ids_fa = set(df_fa["task_id"].unique())
        ids_fe = set(df_fe["task_id"].unique())
        common_ids = ids_b & ids_fa & ids_fe

        if not common_ids:
            continue

        df_b = df_b[df_b["task_id"].isin(common_ids)]
        df_fa = df_fa[df_fa["task_id"].isin(common_ids)]
        df_fe = df_fe[df_fe["task_id"].isin(common_ids)]

        mean_b = df_b["codebleu_1st_pass"].mean(skipna=True)
        mean_fa = df_fa["codebleu_1st_pass"].mean(skipna=True)
        mean_fe = df_fe["codebleu_1st_pass"].mean(skipna=True)

        results.append({
            "dataset": dataset_name,
            "baseline_codebleu": round(mean_b, 4) if pd.notna(mean_b) else None,
            "fedavg_codebleu": round(mean_fa, 4) if pd.notna(mean_fa) else None,
            "federroravg_codebleu": round(mean_fe, 4) if pd.notna(mean_fe) else None,
            "improvement_fedavg": round(mean_fa - (mean_b or 0), 4) if pd.notna(mean_fa) else None,
            "improvement_federroravg": round(mean_fe - (mean_b or 0), 4) if pd.notna(mean_fe) else None,
            "n_tasks": len(common_ids),
        })

    return results


def plot_comparison(results: list[dict], title: str, out_path: str) -> None:
    """Create bar chart comparing CodeBLEU across models."""
    if not results:
        return

    datasets = [r["dataset"] for r in results]
    baseline = [r["baseline_codebleu"] if r["baseline_codebleu"] is not None else 0 for r in results]
    fedavg = [r["fedavg_codebleu"] if r["fedavg_codebleu"] is not None else 0 for r in results]
    federror = [r["federroravg_codebleu"] if r["federroravg_codebleu"] is not None else 0 for r in results]

    x = range(len(datasets))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 5))
    bars1 = ax.bar([i - width for i in x], baseline, width, label="Baseline", color="#2ecc71")
    bars2 = ax.bar(x, fedavg, width, label="FedAvg", color="#3498db")
    bars3 = ax.bar([i + width for i in x], federror, width, label="FedErrorAvg", color="#9b59b6")

    ax.set_ylabel("Mean CodeBLEU")
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend()
    ax.set_ylim(0, 1.05)

    for bars in (bars1, bars2, bars3):
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.3f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Compare CodeBLEU across Baseline, FedAvg, FedErrorAvg (Train and TT)."
    )
    parser.add_argument(
        "--scores-dir",
        type=str,
        default=DEFAULT_SCORES_DIR,
        help="Directory containing codebleu_scores_*.csv files",
    )
    args = parser.parse_args()

    scores_dir = os.path.abspath(args.scores_dir)
    if not os.path.isdir(scores_dir):
        print(f"Scores directory not found: {scores_dir}")
        print("Run: python compute_codebleu.py --process-all")
        return

    # Train comparison
    results_train = compute_comparison(scores_dir, "train")
    if results_train:
        pd.DataFrame(results_train).to_csv(
            os.path.join(OUTPUT_DIR, "codebleu_summary_train.csv"), index=False
        )
        plot_comparison(
            results_train,
            "CodeBLEU: Baseline vs FedAvg vs FedErrorAvg by Dataset (Train)",
            os.path.join(OUTPUT_DIR, "codebleu_comparison_train.png"),
        )
        print("Train: saved codebleu_summary_train.csv, codebleu_comparison_train.png")
    else:
        print("Train: no data (missing score files?)")

    # TT comparison
    results_tt = compute_comparison(scores_dir, "tt")
    if results_tt:
        pd.DataFrame(results_tt).to_csv(
            os.path.join(OUTPUT_DIR, "codebleu_summary_tt.csv"), index=False
        )
        plot_comparison(
            results_tt,
            "CodeBLEU: Baseline vs FedAvg vs FedErrorAvg by Dataset (TT)",
            os.path.join(OUTPUT_DIR, "codebleu_comparison_tt.png"),
        )
        print("TT: saved codebleu_summary_tt.csv, codebleu_comparison_tt.png")
    else:
        print("TT: no data (missing score files?)")

    print(f"\nDone. Outputs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
