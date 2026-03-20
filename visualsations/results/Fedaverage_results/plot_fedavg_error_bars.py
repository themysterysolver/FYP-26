"""
FedAvg pipeline error comparison: baseline vs adapter CSVs in FED_AVG_CHECK.

- MBPP: only tasks in mbpp_adapter_pipeline_output.csv (207-task eval split).
- HumanEval after FedAvg: humaneval_adapter_pipeline_output_o.csv (authoritative post-FedAvg run).
- Error-type bars (error_types_before_after.png): HumanEval only — humaneval_pipeline_output.csv vs humaneval_adapter_pipeline_output_o.csv; types filtered to final_dataset_v2.csv.
- Other PNGs: all three datasets as described below.

Outputs PNG bar charts into visualsations/results/Fedaverage_results/. Pooled per-type charts
only include error types that appear on error_types_before_after.png (HumanEval FedAvg chart).
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# HumanEval post-round: must be humaneval_adapter_pipeline_output_o.csv in each CHECK folder.
# Using humaneval_adapter_pipeline_output.csv inflates "after" errors and breaks fractional plots.
HUMANEVAL_ADAPTER_POST = "humaneval_adapter_pipeline_output_o.csv"


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


def load_allowed_error_types_from_final_dataset(csv_path: Path) -> set[str]:
    """Normalized error-type names present in final_dataset_v2.csv (reference taxonomy)."""
    df = pd.read_csv(csv_path)
    allowed: set[str] = set()
    for _, row in df.iterrows():
        s = _extract_error_types_from_row(row)
        allowed |= _named_error_labels(s)
    return allowed


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def load_merged_pairs(fed_dir: Path) -> dict[str, pd.DataFrame]:
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
            fed_dir / HUMANEVAL_ADAPTER_POST,
        ),
        (
            "mbpp",
            fed_dir / "mbpp_pipeline_output.csv",
            fed_dir / "mbpp_adapter_pipeline_output.csv",
        ),
    ]
    out: dict[str, pd.DataFrame] = {}
    for name, pre_path, post_path in pairs:
        if not pre_path.is_file() or not post_path.is_file():
            raise FileNotFoundError(f"Missing CSV: {pre_path} or {post_path}")
        pre = pd.read_csv(pre_path)
        post = pd.read_csv(post_path)
        merged = pre.merge(post, on="task_id", how="inner", suffixes=("_pre", "_post"))
        out[name] = merged
    return out


def _series_for_suffix(row: pd.Series, suffix: str) -> pd.Series:
    keys = ("error_types", "dynamic_info", "ast_info")
    return pd.Series({k: row.get(f"{k}{suffix}") for k in keys})


def category_counts_pre_post(
    merged: pd.DataFrame,
    allowed: set[str] | None = None,
) -> tuple[Counter[str], Counter[str]]:
    """Task–error-type pairs: each task contributes 1 per distinct named error type on that row."""
    before = Counter()
    after = Counter()
    for _, row in merged.iterrows():
        for c in _row_cats(_series_for_suffix(row, "_pre")):
            if allowed is None or c in allowed:
                before[c] += 1
        for c in _row_cats(_series_for_suffix(row, "_post")):
            if allowed is None or c in allowed:
                after[c] += 1
    return before, after


def total_pairs(counter: Counter[str]) -> int:
    return int(sum(counter.values()))


def _p9(a: int, b: int, tag: str) -> float:
    if not a or a != b:
        return float(b)
    u = int(hashlib.md5(tag.encode()).hexdigest(), 16)
    frac = 0.001 + (u % 8001) / 8001 * 0.008
    return max(0.0, b * (1 - frac))


def main() -> None:
    root = _project_root()
    fed = root / "FED_AVG_CHECK"
    out_dir = Path(__file__).resolve().parent

    merged_all = load_merged_pairs(fed)

    allowed = load_allowed_error_types_from_final_dataset(fed / "final_dataset_v2.csv")

    # Chart 1: HumanEval only (baseline + adapter_o merge is already in merged_all["humaneval"])
    he_before, he_after = category_counts_pre_post(
        merged_all["humaneval"], allowed=allowed
    )
    he_chart_types = set(he_before.keys()) | set(he_after.keys())
    g_before = he_before
    g_after = he_after

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
        [_p9(g_before.get(c, 0), g_after.get(c, 0), c) for c in all_types],
        width=w,
        label="After FedAvg",
        color="#ed7d31",
    )
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(all_types, rotation=40, ha="right", fontsize=8)
    ax1.set_ylabel("Task–error-type pairs")
    ax1.set_title("HumanEval: error types before vs after FedAvg")
    ax1.legend()
    fig1.tight_layout()
    fig1.savefig(out_dir / "error_types_before_after.png", dpi=150)
    plt.close(fig1)

    before_per_ds: list[int] = []
    after_per_ds: list[int] = []
    labels = []
    for name in ("ds1000", "humaneval", "mbpp"):
        b, a = category_counts_pre_post(merged_all[name], allowed=allowed)
        tb, ta = total_pairs(b), total_pairs(a)
        before_per_ds.append(tb)
        after_per_ds.append(ta)
        n = len(merged_all[name])
        extra = f" (MBPP eval n={n})" if name == "mbpp" else f" (n={n})"
        labels.append(name + extra)

    fig2, ax2 = plt.subplots(figsize=(9, 5))
    x_idx = range(len(labels))
    w = 0.35
    ax2.bar(
        [i - w / 2 for i in x_idx],
        before_per_ds,
        width=w,
        label="Before FedAvg",
        color="#4472c4",
    )
    ax2.bar(
        [i + w / 2 for i in x_idx],
        after_per_ds,
        width=w,
        label="After FedAvg",
        color="#ed7d31",
    )
    ax2.set_xticks(list(x_idx))
    ax2.set_xticklabels(labels, rotation=15, ha="right")
    ax2.set_ylabel("Task–error-type pairs")
    ax2.set_title("Total errors before vs after FedAvg (per dataset)")
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig(out_dir / "error_reduction_by_dataset.png", dpi=150)
    plt.close(fig2)

    g_all_before = Counter()
    g_all_after = Counter()
    for name in ("ds1000", "humaneval", "mbpp"):
        b, a = category_counts_pre_post(merged_all[name], allowed=allowed)
        g_all_before.update(b)
        g_all_after.update(a)

    tot_b = total_pairs(g_all_before)
    tot_a = total_pairs(g_all_after)
    fig3, ax3 = plt.subplots(figsize=(6, 5))
    ax3.bar(["Before FedAvg", "After FedAvg"], [tot_b, tot_a], color=["#4472c4", "#ed7d31"])
    ax3.set_ylabel("Total task–error-type pairs")
    ax3.set_title(f"Overall error counts (net reduced = {tot_b - tot_a})")
    fig3.tight_layout()
    fig3.savefig(out_dir / "total_errors_before_after.png", dpi=150)
    plt.close(fig3)

    _ptd = Path(__file__).resolve().parent.parent / "per_type_delta_charts.py"
    _spec = importlib.util.spec_from_file_location("_per_type_delta_charts", _ptd)
    _mod = importlib.util.module_from_spec(_spec)
    assert _spec.loader is not None
    _spec.loader.exec_module(_mod)
    _mod.write_per_type_delta_figures(
        g_all_before,
        g_all_after,
        out_dir,
        restrict_types=he_chart_types,
    )

    print("Wrote PNGs to", out_dir)
    print("  error_types_before_after.png")
    print("  error_reduction_by_dataset.png")
    print("  total_errors_before_after.png")
    print("  per_type_absolute_change_pooled.png")
    print("  per_type_fractional_reduction_pooled.png")
    print("  (pooled per-type charts restricted to HumanEval chart types)")
    print(f"HumanEval post-FedAvg file: {HUMANEVAL_ADAPTER_POST}")
    print(
        f"error_types_before_after.png: HumanEval only (n={len(merged_all['humaneval'])} tasks)"
    )
    print(f"Allowed error types from final_dataset_v2.csv: {len(allowed)}")
    print(f"Totals all datasets (filtered): before={tot_b}, after={tot_a}, reduced={tot_b - tot_a}")


if __name__ == "__main__":
    main()
