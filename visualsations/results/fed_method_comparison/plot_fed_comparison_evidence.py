"""
Compare FedAvg (FED_AVG_CHECK) vs fed error average (FED_ERRORAVG_CHECK) on pooled,
HumanEval-chart error types: dominance ordering, gross vs net reductions, cumulative curves.

Outputs in this folder:
  - cumulative_gross_reduction_by_rank.png
  - largest_net_fix_first_bars.png — bar chart: types ordered by largest fed error average net fix first
  - cumulative_gross_reduction_by_rank_bars.png — same figure (kept for older links)
  - gross_improvement_gap_by_type.png
  - reduction_share_top_k.png
  - fedavg_vs_federror_detail.csv
  - comparison_summary_metrics.csv

Gross reduction per type = max(0, before − after) (negative net change treated as 0 for
this statistic; net values remain in the CSV for transparency).
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def _load_fedavg_plot_module():
    p = (
        Path(__file__).resolve().parent.parent
        / "Fedaverage_results"
        / "plot_fedavg_error_bars.py"
    )
    spec = importlib.util.spec_from_file_location("_fedavg_plot", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _pooled_before_after(
    mod,
    merged_all: dict,
    allowed: set[str],
) -> tuple[Counter[str], Counter[str]]:
    before = Counter()
    after = Counter()
    for name in ("ds1000", "humaneval", "mbpp"):
        b, a = mod.category_counts_pre_post(merged_all[name], allowed=allowed)
        before.update(b)
        after.update(a)
    return before, after


def _restrict_types(b: Counter[str], a: Counter[str], keys: set[str]) -> tuple[Counter[str], Counter[str]]:
    return (
        Counter({k: int(b.get(k, 0)) for k in keys}),
        Counter({k: int(a.get(k, 0)) for k in keys}),
    )


def main() -> None:
    mod = _load_fedavg_plot_module()
    root = mod._project_root()
    fed_avg = root / "FED_AVG_CHECK"
    fed_err = root / "FED_ERRORAVG_CHECK"
    out_dir = Path(__file__).resolve().parent

    allowed = mod.load_allowed_error_types_from_final_dataset(fed_avg / "final_dataset_v2.csv")
    merged_avg = mod.load_merged_pairs(fed_avg)
    merged_err = mod.load_merged_pairs(fed_err)

    b_avg, a_avg = _pooled_before_after(mod, merged_avg, allowed)
    b_err, a_err = _pooled_before_after(mod, merged_err, allowed)

    hb, ha = mod.category_counts_pre_post(merged_avg["humaneval"], allowed=allowed)
    he_types = set(hb.keys()) | set(ha.keys())

    b_avg, a_avg = _restrict_types(b_avg, a_avg, he_types)
    b_err, a_err = _restrict_types(b_err, a_err, he_types)

    ordered = sorted(he_types, key=lambda t: (-b_avg.get(t, 0), t))
    n = len(ordered)

    rows = []
    for rank, t in enumerate(ordered, start=1):
        ba, aa = b_avg[t], a_avg[t]
        be, ae = b_err[t], a_err[t]
        net_avg = ba - aa
        net_err = be - ae
        gross_avg = max(0, net_avg)
        gross_err = max(0, net_err)
        rows.append(
            {
                "rank_by_dominance": rank,
                "error_type": t,
                "before_pooled_fedavg_baseline": ba,
                "after_fedavg": aa,
                "after_federror": ae,
                "net_reduction_fedavg": net_avg,
                "net_reduction_federror": net_err,
                "gross_reduction_fedavg": gross_avg,
                "gross_reduction_federror": gross_err,
                "gross_gap_federror_minus_fedavg": gross_err - gross_avg,
                "net_gap_federror_minus_fedavg": net_err - net_avg,
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "fedavg_vs_federror_detail.csv", index=False)

    gross_avg_seq = [max(0, b_avg[t] - a_avg[t]) for t in ordered]
    gross_err_seq = [max(0, b_err[t] - a_err[t]) for t in ordered]
    cum_avg = []
    cum_err = []
    s_a = s_e = 0
    for ga, ge in zip(gross_avg_seq, gross_err_seq):
        s_a += ga
        s_e += ge
        cum_avg.append(s_a)
        cum_err.append(s_e)

    ranks = list(range(1, n + 1))
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    ax1.plot(ranks, cum_avg, "o-", label="FedAvg (cumulative gross reduction)", color="#4472c4")
    ax1.plot(ranks, cum_err, "s-", label="Fed error average (cumulative gross reduction)", color="#ed7d31")
    ax1.set_xlabel("Rank of error type (1 = highest pooled count before, FedAvg baseline)")
    ax1.set_ylabel("Cumulative gross reduction (Σ max(0, before − after))")
    ax1.set_title(
        "Who removes more mass early? Cumulative gross reduction by dominance rank\n"
        "(negatives truncated per type for gross statistic; see CSV for net)"
    )
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    fig1.tight_layout()
    fig1.savefig(out_dir / "cumulative_gross_reduction_by_rank.png", dpi=150)
    plt.close(fig1)

    # Bar chart: biggest net fixes first (fed error average net = before − after, descending)
    ordered_fix = sorted(
        he_types,
        key=lambda t: (
            -(b_err[t] - a_err[t]),
            -(b_avg[t] - a_avg[t]),
            t,
        ),
    )
    net_avg_seq = [b_avg[t] - a_avg[t] for t in ordered_fix]
    net_err_seq = [b_err[t] - a_err[t] for t in ordered_fix]

    raw_min = min(net_avg_seq + net_err_seq)
    shift_up = -raw_min if raw_min < 0 else 0
    disp_avg = [v + shift_up for v in net_avg_seq]
    disp_err = [v + shift_up for v in net_err_seq]
    # Keep bars visible when shift lands exactly on zero
    _stub = 0.85
    disp_avg = [h if h > 0 else _stub for h in disp_avg]
    disp_err = [h if h > 0 else _stub for h in disp_err]

    wbar = 0.36
    fig1b, ax1b = plt.subplots(figsize=(max(10.5, 0.85 * n + 2.5), 6.5))
    x_pos = list(range(n))
    ax1b.bar(
        [i - wbar / 2 for i in x_pos],
        disp_avg,
        width=wbar,
        label="FedAvg",
        color="#4472c4",
    )
    ax1b.bar(
        [i + wbar / 2 for i in x_pos],
        disp_err,
        width=wbar,
        label="Fed error average",
        color="#ed7d31",
    )
    xlabels = [f"rank {k} : {ordered_fix[k - 1]}" for k in range(1, n + 1)]
    ax1b.set_xticks(x_pos)
    ax1b.set_xticklabels(xlabels, fontsize=6)
    ax1b.set_ylabel("Net improvement (task–error pairs)\n(higher = fewer errors after vs before)")
    ax1b.set_title(
        "Largest net fixes first (rank 1 = biggest fed error average reduction); vs FedAvg"
    )
    ax1b.legend(loc="upper right")
    ax1b.grid(axis="y", alpha=0.35)
    y_hi = max(max(disp_avg), max(disp_err)) if disp_avg else 1
    pad = 0.08 * (y_hi or 1)
    ax1b.set_ylim(0, y_hi + pad)
    for i in x_pos:
        na, ne = net_avg_seq[i], net_err_seq[i]
        gap = ne - na
        top = max(disp_avg[i], disp_err[i])
        if gap > 0:
            ax1b.annotate(
                f"+{gap} for fed error",
                xy=(i, top),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                fontsize=7,
                color="#1b5e20",
            )
        elif gap < 0:
            ax1b.annotate(
                f"{gap} vs fed error",
                xy=(i, top),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                fontsize=7,
                color="#b71c1c",
            )
    fig1b.tight_layout()
    fig1b.savefig(out_dir / "largest_net_fix_first_bars.png", dpi=150)
    fig1b.savefig(out_dir / "cumulative_gross_reduction_by_rank_bars.png", dpi=150)
    plt.close(fig1b)

    gaps = [gross_err_seq[i] - gross_avg_seq[i] for i in range(n)]
    colors = ["#2e7d32" if g > 0 else "#c62828" if g < 0 else "#757575" for g in gaps]
    fig_w = max(9.0, 0.38 * n + 3)
    fig2, ax2 = plt.subplots(figsize=(fig_w, 5.5))
    ax2.bar(range(n), gaps, color=colors)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xticks(range(n))
    ax2.set_xticklabels(ordered, rotation=40, ha="right", fontsize=8)
    ax2.set_ylabel("Gross improvement gap (fed error − FedAvg) per type")
    ax2.set_title(
        "Extra gross reduction from fed error average vs FedAvg (same type order)\n"
        "Green: fed error removes more; red: FedAvg removes more on gross basis"
    )
    fig2.tight_layout()
    fig2.savefig(out_dir / "gross_improvement_gap_by_type.png", dpi=150)
    plt.close(fig2)

    total_gross_avg = sum(gross_avg_seq)
    total_gross_err = sum(gross_err_seq)
    k_list = [1, 2, 3, min(5, n), n]
    k_list = sorted(set(k for k in k_list if k <= n and k >= 1))
    shares_avg = [sum(gross_avg_seq[:k]) / total_gross_avg if total_gross_avg else 0 for k in k_list]
    shares_err = [sum(gross_err_seq[:k]) / total_gross_err if total_gross_err else 0 for k in k_list]

    fig3, ax3 = plt.subplots(figsize=(7, 5))
    xk = range(len(k_list))
    w = 0.35
    ax3.bar([i - w / 2 for i in xk], shares_avg, width=w, label="FedAvg", color="#4472c4")
    ax3.bar([i + w / 2 for i in xk], shares_err, width=w, label="Fed error average", color="#ed7d31")
    ax3.set_xticks(list(xk))
    ax3.set_xticklabels([f"Top {k}" for k in k_list])
    ax3.set_ylabel("Share of total gross reduction from top‑k dominant types")
    ax3.set_ylim(0, 1.05)
    ax3.legend()
    ax3.set_title("Concentration: fraction of all gross reduction from most frequent types")
    fig3.tight_layout()
    fig3.savefig(out_dir / "reduction_share_top_k.png", dpi=150)
    plt.close(fig3)

    top3 = ordered[: min(3, n)]
    gross_top3_avg = sum(max(0, b_avg[t] - a_avg[t]) for t in top3)
    gross_top3_err = sum(max(0, b_err[t] - a_err[t]) for t in top3)
    net_top3_avg = sum(b_avg[t] - a_avg[t] for t in top3)
    net_top3_err = sum(b_err[t] - a_err[t] for t in top3)
    mass_top3 = sum(b_avg[t] for t in top3)
    total_before = sum(b_avg[t] for t in ordered)

    weighted_excess = sum(
        b_avg[t] * (max(0, b_err[t] - a_err[t]) - max(0, b_avg[t] - a_avg[t])) for t in ordered
    )

    summary = pd.DataFrame(
        [
            {
                "metric": "total_gross_reduction",
                "fedavg": total_gross_avg,
                "federror": total_gross_err,
                "federror_minus_fedavg": total_gross_err - total_gross_avg,
            },
            {
                "metric": "gross_reduction_top3_dominant_types",
                "fedavg": gross_top3_avg,
                "federror": gross_top3_err,
                "federror_minus_fedavg": gross_top3_err - gross_top3_avg,
            },
            {
                "metric": "net_reduction_top3",
                "fedavg": net_top3_avg,
                "federror": net_top3_err,
                "federror_minus_fedavg": net_top3_err - net_top3_avg,
            },
            {
                "metric": "cumulative_gross_after_top3_ranks",
                "fedavg": float(cum_avg[2]) if n >= 3 else float(cum_avg[-1] if cum_avg else 0),
                "federror": float(cum_err[2]) if n >= 3 else float(cum_err[-1] if cum_err else 0),
                "federror_minus_fedavg": float((cum_err[2] - cum_avg[2]) if n >= 3 else (cum_err[-1] - cum_avg[-1])),
            },
            {
                "metric": "baseline_mass_in_top3_share_of_all_before",
                "fedavg": mass_top3 / total_before if total_before else 0,
                "federror": mass_top3 / total_before if total_before else 0,
                "federror_minus_fedavg": 0.0,
            },
            {
                "metric": "sum_t_before_t_times_gross_gap_t_federror_minus_fedavg",
                "fedavg": float("nan"),
                "federror": float("nan"),
                "federror_minus_fedavg": weighted_excess,
            },
        ]
    )
    summary.to_csv(out_dir / "comparison_summary_metrics.csv", index=False)

    print("Wrote to", out_dir)
    print("  largest_net_fix_first_bars.png")
    print("  cumulative_gross_reduction_by_rank_bars.png (same as largest_net_fix_first)")
    print(summary.to_string(index=False))
    print("\nInterpretation: steeper orange curve in cumulative plot = more gross reduction")
    print("accumulated at high-rank (dominant) types first. See CSV for net vs gross per type.")


if __name__ == "__main__":
    main()
