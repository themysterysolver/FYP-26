"""
FedAvg pipeline error comparison: baseline vs adapter CSVs in FED_AVG_CHECK.
MBPP: only tasks present in mbpp_adapter_pipeline_output.csv (207-task eval split).

Outputs PNG bar charts into this directory.
"""
from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# --- Same as Pipeline construction/AST+DYNMAIC+LIB_API/extract_by_error_type.py ---


def _normalize(s: str) -> str:
    t = s.split(":")[-1].strip() if ":" in s else s.strip()
    return t.replace(" ", "")


def _extract_error_types_from_row(row: pd.Series) -> str:
    et = row.get("error_types", "")
    if et is not None and str(et).strip() and str(et) != "nan":
        return str(et)
    parts = []
    dinfo = row.get("dynamic_info", "")
    if dinfo is not None and isinstance(dinfo, str) and dinfo.strip():
        try:
            d = ast.literal_eval(dinfo)
            if isinstance(d, dict):
                etype = d.get("error_type", "")
                if etype and str(etype).strip():
                    parts.append(str(etype))
        except (ValueError, SyntaxError):
            pass
    ainfo = row.get("ast_info", "")
    if ainfo is not None and isinstance(ainfo, str) and ainfo.strip():
        try:
            a = ast.literal_eval(ainfo)
            if isinstance(a, dict) and a.get("ast_parsed") is False:
                parts.append("SyntaxError")
            else:
                ast_errors = a.get("ast_errors", []) if isinstance(a, dict) else []
                for err in ast_errors:
                    etype = err.get("type", "") if isinstance(err, dict) else ""
                    if etype:
                        parts.append(etype)
        except (ValueError, SyntaxError):
            pass
    return ",".join(parts) if parts else ""


def _named_error_labels(error_types_str: str) -> set[str]:
    """One label per distinct normalized error token (no 'other' bucket)."""
    if not error_types_str or not str(error_types_str).strip():
        return set()
    parts = [p.strip() for p in str(error_types_str).split(",")]
    labels: set[str] = set()
    for p in parts:
        t = _normalize(p)
        if t:
            labels.add(t)
    return labels


def _row_cats(row: pd.Series) -> set[str]:
    s = _extract_error_types_from_row(row)
    return _named_error_labels(s)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_merged_pairs(
    fed_dir: Path,
) -> dict[str, pd.DataFrame]:
    """Inner-merge baseline vs adapter per dataset; MBPP eval = adapter task_ids only."""
    pairs = [
        (
            "ds1000",
            fed_dir / "ds1000_pipeline_output.csv",
            fed_dir / "ds1000_adapter_pipeline_output.csv",
        ),
        (
            "humaneval",
            fed_dir / "humaneval_pipeline_output.csv",
            fed_dir / "humaneval_adapter_pipeline_output.csv",
        ),
        (
            "mbpp",
            fed_dir / "mbpp_pipeline_output.csv",
            fed_dir / "mbpp_adapter_pipeline_output.csv",
        ),
    ]
    out: dict[str, pd.DataFrame] = {}
    for name, pre_path, post_path in pairs:
        pre = pd.read_csv(pre_path)
        post = pd.read_csv(post_path)
        merged = pre.merge(post, on="task_id", how="inner", suffixes=("_pre", "_post"))
        out[name] = merged
    return out


def _series_for_suffix(row: pd.Series, suffix: str) -> pd.Series:
    """Build a row slice with base column names for extract_* helpers."""
    keys = ("error_types", "dynamic_info", "ast_info")
    return pd.Series({k: row.get(f"{k}{suffix}") for k in keys})


def category_counts_pre_post(merged: pd.DataFrame) -> tuple[Counter[str], Counter[str]]:
    """Task–error-type pairs: each task contributes 1 per distinct named error type on that row."""
    before = Counter()
    after = Counter()
    for _, row in merged.iterrows():
        for c in _row_cats(_series_for_suffix(row, "_pre")):
            before[c] += 1
        for c in _row_cats(_series_for_suffix(row, "_post")):
            after[c] += 1
    return before, after


def total_pairs(counter: Counter[str]) -> int:
    return int(sum(counter.values()))


def main() -> None:
    root = _project_root()
    fed = root / "FED_AVG_CHECK"
    out_dir = Path(__file__).resolve().parent

    merged_all = load_merged_pairs(fed)

    # --- Chart 1: global category before vs after ---
    g_before = Counter()
    g_after = Counter()
    for name in ("ds1000", "humaneval", "mbpp"):
        b, a = category_counts_pre_post(merged_all[name])
        g_before.update(b)
        g_after.update(a)

    all_types = sorted(set(g_before.keys()) | set(g_after.keys()))
    n = len(all_types)
    x = range(n)
    w = 0.35
    fig_w = max(12.0, 0.45 * n + 4)
    fig1, ax1 = plt.subplots(figsize=(fig_w, 5.5))
    ax1.bar(
        [i - w / 2 for i in x],
        [g_before.get(c, 0) for c in all_types],
        width=w,
        label="Before FedAvg",
        color="#4472c4",
    )
    ax1.bar(
        [i + w / 2 for i in x],
        [g_after.get(c, 0) for c in all_types],
        width=w,
        label="After FedAvg",
        color="#ed7d31",
    )
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(all_types, rotation=40, ha="right", fontsize=8)
    ax1.set_ylabel("Task–error-type pairs")
    ax1.set_title("Error types (named): before vs after FedAvg (all datasets, aligned tasks)")
    ax1.legend()
    fig1.tight_layout()
    fig1.savefig(out_dir / "error_types_before_after.png", dpi=150)
    plt.close(fig1)

    # --- Chart 2: net reduction per dataset (total task–category pairs) ---
    reductions = []
    labels = []
    for name in ("ds1000", "humaneval", "mbpp"):
        b, a = category_counts_pre_post(merged_all[name])
        tb, ta = total_pairs(b), total_pairs(a)
        reductions.append(tb - ta)
        n = len(merged_all[name])
        extra = f" (MBPP eval n={n})" if name == "mbpp" else f" (n={n})"
        labels.append(name + extra)

    fig2, ax2 = plt.subplots(figsize=(8, 5))
    colors = ["#2e7d32" if r >= 0 else "#c62828" for r in reductions]
    ax2.bar(labels, reductions, color=colors)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_ylabel("Reduction (before − after)")
    ax2.set_title("Net change in task–error-type counts per dataset")
    ax2.tick_params(axis="x", rotation=15)
    fig2.tight_layout()
    fig2.savefig(out_dir / "error_reduction_by_dataset.png", dpi=150)
    plt.close(fig2)

    # --- Chart 3: overall totals before vs after ---
    tot_b = total_pairs(g_before)
    tot_a = total_pairs(g_after)
    fig3, ax3 = plt.subplots(figsize=(6, 5))
    ax3.bar(["Before FedAvg", "After FedAvg"], [tot_b, tot_a], color=["#4472c4", "#ed7d31"])
    ax3.set_ylabel("Total task–error-type pairs")
    ax3.set_title(f"Overall error counts (aligned tasks; net reduced = {tot_b - tot_a})")
    fig3.tight_layout()
    fig3.savefig(out_dir / "total_errors_before_after.png", dpi=150)
    plt.close(fig3)

    print("Wrote PNGs to", out_dir)
    print("  error_types_before_after.png")
    print("  error_reduction_by_dataset.png")
    print("  total_errors_before_after.png")
    print(f"Totals: before={tot_b}, after={tot_a}, reduced={tot_b - tot_a}")


if __name__ == "__main__":
    main()
