"""Pooled per-type error charts: absolute (before − after) and fractional reduction."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


def _apply_restrict(
    before: Counter[str],
    after: Counter[str],
    restrict_types: set[str] | None,
) -> tuple[Counter[str], Counter[str]]:
    if restrict_types is None:
        return before, after
    return (
        Counter({k: int(before.get(k, 0)) for k in restrict_types}),
        Counter({k: int(after.get(k, 0)) for k in restrict_types}),
    )


def write_per_type_delta_figures(
    before: Counter[str],
    after: Counter[str],
    out_dir: Path,
    *,
    restrict_types: set[str] | None = None,
    shade_top_n_dominant: int = 3,
) -> None:
    """
    Write two PNGs into out_dir:
    - per_type_absolute_change_pooled.png
    - per_type_fractional_reduction_pooled.png

    If restrict_types is set, only those error names are shown (counts still pooled
    across ds1000 + humaneval + mbpp). Types are sorted by pooled *before* count
    (descending) so the most frequent types appear first.

    shade_top_n_dominant: light band behind the first N bars (by that order).
    """
    before, after = _apply_restrict(before, after, restrict_types)

    all_types = set(before.keys()) | set(after.keys())
    ordered = sorted(all_types, key=lambda t: (-before.get(t, 0), t))

    abs_vals = [before[t] - after[t] for t in ordered]
    colors_abs = ["#2e7d32" if v >= 0 else "#c62828" for v in abs_vals]
    n = len(ordered)
    fig_w = max(11.0, 0.42 * n + 3)
    fig1, ax1 = plt.subplots(figsize=(fig_w, 5.5))
    if shade_top_n_dominant > 0 and n > 0:
        k = min(shade_top_n_dominant, n)
        ax1.axvspan(-0.5, k - 0.5, color="#9e9e9e", alpha=0.12, zorder=0)
    ax1.bar(range(n), abs_vals, color=colors_abs, zorder=1)
    ax1.axhline(0, color="black", linewidth=0.7)
    ax1.set_xticks(range(n))
    ax1.set_xticklabels(ordered, rotation=40, ha="right", fontsize=8)
    ax1.set_ylabel("Before − after (task–error-type pairs)")
    ax1.set_title("Per-type absolute change (pooled; HumanEval chart types only)")
    fig1.tight_layout()
    fig1.savefig(out_dir / "per_type_absolute_change_pooled.png", dpi=150)
    plt.close(fig1)

    frac_types = [t for t in ordered if before.get(t, 0) > 0]
    frac_vals = [(before[t] - after[t]) / before[t] for t in frac_types]
    colors_frac = ["#2e7d32" if v >= 0 else "#c62828" for v in frac_vals]
    nf = len(frac_types)
    fig_w2 = max(10.0, 0.42 * nf + 3)
    fig2, ax2 = plt.subplots(figsize=(fig_w2, 5.5))
    if shade_top_n_dominant > 0 and nf > 0:
        dominant = set(ordered[: min(shade_top_n_dominant, len(ordered))])
        idxs = [i for i, t in enumerate(frac_types) if t in dominant]
        if idxs:
            ax2.axvspan(min(idxs) - 0.5, max(idxs) + 0.5, color="#9e9e9e", alpha=0.12, zorder=0)
    ax2.bar(range(nf), frac_vals, color=colors_frac, zorder=1)
    ax2.axhline(0, color="black", linewidth=0.7)
    ax2.set_xticks(range(nf))
    ax2.set_xticklabels(frac_types, rotation=40, ha="right", fontsize=8)
    ax2.set_ylabel("Fractional reduction (before − after) / before")
    if frac_vals:
        lo, hi = min(frac_vals), max(frac_vals)
        span = hi - lo if hi != lo else 1.0
        pad = 0.08 * span
        ax2.set_ylim(lo - pad, hi + pad)
    ax2.set_title("Per-type fractional reduction (pooled; HumanEval chart types only)")
    fig2.tight_layout()
    fig2.savefig(out_dir / "per_type_fractional_reduction_pooled.png", dpi=150)
    plt.close(fig2)


def write_comparison_absolute_delta(
    before_avg: Counter[str],
    after_avg: Counter[str],
    before_err: Counter[str],
    after_err: Counter[str],
    restrict_types: set[str],
    out_dir: Path,
    *,
    sort_by: Counter[str],
    shade_top_n_dominant: int = 3,
) -> None:
    """
    Grouped bars: per type, FedAvg vs fed error average absolute reduction (before − after).
    Types and order follow `sort_by` (typically FedAvg pooled *before*), restricted to restrict_types.
    """
    ordered = sorted(
        restrict_types,
        key=lambda t: (-sort_by.get(t, 0), t),
    )
    n = len(ordered)
    w = 0.35
    x = range(n)
    d_avg = [before_avg.get(t, 0) - after_avg.get(t, 0) for t in ordered]
    d_err = [before_err.get(t, 0) - after_err.get(t, 0) for t in ordered]

    fig_w = max(11.0, 0.5 * n + 4)
    fig, ax = plt.subplots(figsize=(fig_w, 5.5))
    if shade_top_n_dominant > 0 and n > 0:
        k = min(shade_top_n_dominant, n)
        ax.axvspan(-0.5, k - 0.5, color="#9e9e9e", alpha=0.12, zorder=0)
    ax.bar(
        [i - w / 2 for i in x],
        d_avg,
        width=w,
        label="FedAvg",
        color="#4472c4",
        zorder=1,
    )
    ax.bar(
        [i + w / 2 for i in x],
        d_err,
        width=w,
        label="Fed error average",
        color="#ed7d31",
        zorder=1,
    )
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(list(x))
    ax.set_xticklabels(ordered, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Before − after (task–error-type pairs)")
    ax.set_title(
        "Absolute reduction by type: FedAvg vs fed error average (pooled; HumanEval chart types)"
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "per_type_absolute_delta_vs_fedavg.png", dpi=150)
    plt.close(fig)
