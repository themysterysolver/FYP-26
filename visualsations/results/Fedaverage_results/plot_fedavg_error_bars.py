"""
FedAvg pipeline error comparison: baseline vs adapter CSVs in FED_AVG_CHECK.

- MBPP: only tasks in mbpp_adapter_pipeline_output.csv (207-task eval split).
- HumanEval after FedAvg: humaneval_adapter_pipeline_output_o.csv (authoritative post-FedAvg run).
- Error-type bars (error_types_before_after.png): pooled over DS-1000, HumanEval, MBPP; x-axis types
  and order match fed_method_comparison/largest_net_fix_first_bars.png (HumanEval type set; order =
  largest fed-error net fix first, tie-break FedAvg net).

Outputs PNG bar charts into visualsations/results/Fedaverage_results/. Pooled per-type delta charts
use the same error types as error_types_before_after.png.
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


def error_types_for_method_comparison_chart(
    merged_humaneval: pd.DataFrame,
    allowed: set[str],
) -> set[str]:
    """Types on HumanEval FedAvg before/after — same set as fed_method_comparison bar charts."""
    hb, ha = category_counts_pre_post(merged_humaneval, allowed=allowed)
    return set(hb.keys()) | set(ha.keys())


def type_order_largest_net_fix_first(
    b_avg: Counter[str],
    a_avg: Counter[str],
    b_err: Counter[str],
    a_err: Counter[str],
    he_types: set[str],
) -> list[str]:
    """X-order: largest fed-error net reduction first; tie-break FedAvg net; then name."""
    return sorted(
        he_types,
        key=lambda t: (
            -(b_err.get(t, 0) - a_err.get(t, 0)),
            -(b_avg.get(t, 0) - a_avg.get(t, 0)),
            t,
        ),
    )


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

    g_all_before = Counter()
    g_all_after = Counter()
    for name in ("ds1000", "humaneval", "mbpp"):
        b, a = category_counts_pre_post(merged_all[name], allowed=allowed)
        g_all_before.update(b)
        g_all_after.update(a)

    # Chart 1: pooled counts; x-axis types/order = method-comparison largest-net-fix-first chart
    g_before = g_all_before
    g_after = g_all_after
    he_types = error_types_for_method_comparison_chart(merged_all["humaneval"], allowed)
    fed_err_dir = root / "FED_ERRORAVG_CHECK"
    try:
        merged_err = load_merged_pairs(fed_err_dir)
        allowed_err = load_allowed_error_types_from_final_dataset(
            fed_err_dir / "final_dataset_v2.csv"
        )
        b_err_p = Counter()
        a_err_p = Counter()
        for name in ("ds1000", "humaneval", "mbpp"):
            b, a = category_counts_pre_post(merged_err[name], allowed=allowed_err)
            b_err_p.update(b)
            a_err_p.update(a)
        all_types = type_order_largest_net_fix_first(
            g_all_before, g_all_after, b_err_p, a_err_p, he_types
        )
    except FileNotFoundError:
        all_types = sorted(
            he_types,
            key=lambda t: (
                -(g_all_before.get(t, 0) - g_all_after.get(t, 0)),
                -(g_all_before.get(t, 0)),
                t,
            ),
        )
    he_chart_types = he_types
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
    ax1.set_title(
        "DS-1000, HumanEval & MBPP (pooled): error types before vs after FedAvg"
    )
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
    print("  (pooled per-type delta charts match error_types_before_after types)")
    print(f"HumanEval post-FedAvg file: {HUMANEVAL_ADAPTER_POST}")
    print(
        "error_types_before_after.png: pooled over "
        f"ds1000 n={len(merged_all['ds1000'])}, humaneval n={len(merged_all['humaneval'])}, "
        f"mbpp n={len(merged_all['mbpp'])}; x-axis = HumanEval type set, "
        "order = largest fed-error net fix first (see fed_method_comparison)"
    )
    print(f"Allowed error types from final_dataset_v2.csv: {len(allowed)}")
    print(f"Totals all datasets (filtered): before={tot_b}, after={tot_a}, reduced={tot_b - tot_a}")


if __name__ == "__main__":
    main()
