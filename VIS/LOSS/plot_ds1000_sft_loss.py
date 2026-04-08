"""
Plot DS1000 SFT training loss from CSV (output of extract_ds1000_sft_loss.py).

Usage:
  python plot_ds1000_sft_loss.py
  python plot_ds1000_sft_loss.py --csv path/to/ds1000_sft_training_loss.csv
"""

import argparse
import json
import os

import matplotlib.pyplot as plt
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(SCRIPT_DIR, "ds1000_sft_training_loss.csv")
DEFAULT_SUMMARY = os.path.join(SCRIPT_DIR, "ds1000_sft_run_summary.json")
DEFAULT_PNG = os.path.join(SCRIPT_DIR, "ds1000_sft_training_loss.png")


def load_epoch_boundaries(summary_path: str) -> list[int]:
    """Return optimizer steps at epoch boundaries (exclusive), e.g. [125, 250] for 3 epochs."""
    if not os.path.isfile(summary_path):
        return []
    with open(summary_path, encoding="utf-8") as f:
        s = json.load(f)
    spe = s.get("steps_per_epoch")
    ne = s.get("num_epochs")
    if not spe or not ne:
        return []
    return [spe * e for e in range(1, ne)]


def main() -> None:
    p = argparse.ArgumentParser(description="Plot DS1000 SFT training loss.")
    p.add_argument("--csv", default=DEFAULT_CSV)
    p.add_argument("--summary", default=DEFAULT_SUMMARY)
    p.add_argument("--out", default=DEFAULT_PNG)
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    if df.empty:
        raise SystemExit("CSV is empty.")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["step"], df["training_loss"], color="#1f77b4", linewidth=1.5, marker=".", markersize=4)

    boundaries = load_epoch_boundaries(args.summary)
    for b in boundaries:
        ax.axvline(b, color="0.75", linestyle="--", linewidth=1, zorder=0)

    ax.set_xlabel("Global step (logging every 5 steps)")
    ax.set_ylabel("Training loss")
    ax.set_title("DS1000 SFT — Qwen2.5-Coder-3B-Instruct + LoRA")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
