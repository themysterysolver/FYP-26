import os
from typing import List, Tuple

import pandas as pd


def normalize_status(x: object) -> str:
    return str(x).strip().lower()


def deterministic_split(task_ids: List[str], test_frac: float) -> Tuple[List[str], List[str]]:
    """
    Split task ids deterministically by lexicographic order:
    - test_task_ids: first round(n * test_frac)
    - train_task_ids: remaining
    """
    if not task_ids:
        return [], []
    task_ids_sorted = sorted(task_ids)
    n = len(task_ids_sorted)
    n_test = int(round(n * test_frac))

    # Avoid degenerate splits when there is more than 1 task available.
    if n > 1:
        n_test = max(1, min(n - 1, n_test))
    else:
        n_test = 0

    test_task_ids = task_ids_sorted[:n_test]
    train_task_ids = task_ids_sorted[n_test:]
    return train_task_ids, test_task_ids


def split_human_eval_sft_ready(
    input_csv_path: str,
    train_out_path: str,
    test_out_path: str,
    test_frac: float = 0.25,
) -> None:
    df = pd.read_csv(input_csv_path)

    required = {"task_id", "status"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input CSV missing required columns: {missing}")

    # Task-level split: ensure whole task_id goes to exactly one split.
    # (In current data it should already be one row per task_id, but keep it robust.)
    # Build a task-level table so we split by whole task_id.
    task_status = (
        df.groupby("task_id", as_index=False)
        .agg(status_first=("status", "first"))
    )

    task_status["task_id"] = task_status["task_id"].astype(str)
    task_status["status_norm"] = task_status["status_first"].apply(normalize_status)

    passed_task_ids = task_status[task_status["status_norm"].eq("passed")]["task_id"].tolist()
    other_task_ids = task_status[~task_status["status_norm"].eq("passed")]["task_id"].tolist()

    train_passed, test_passed = deterministic_split(passed_task_ids, test_frac=test_frac)
    train_other, test_other = deterministic_split(other_task_ids, test_frac=test_frac)

    train_task_ids = set(train_passed) | set(train_other)
    test_task_ids = set(test_passed) | set(test_other)

    overlap = train_task_ids & test_task_ids
    if overlap:
        raise RuntimeError(f"Split error: task_id overlap found: {sorted(list(overlap))[:10]}")

    all_task_ids = set(task_status["task_id"].tolist())
    if train_task_ids | test_task_ids != all_task_ids:
        missing = all_task_ids - (train_task_ids | test_task_ids)
        raise RuntimeError(f"Split error: some task_ids missing from split: {sorted(list(missing))[:10]}")

    # Materialize row-level CSVs while preserving original schema/column order.
    orig_cols = list(df.columns)
    train_df = df[df["task_id"].astype(str).isin(train_task_ids)].copy()
    test_df = df[df["task_id"].astype(str).isin(test_task_ids)].copy()
    train_df = train_df[orig_cols]
    test_df = test_df[orig_cols]

    train_df.to_csv(train_out_path, index=False)
    test_df.to_csv(test_out_path, index=False)

    # Summary for quick verification.
    total_tasks = len(all_task_ids)
    print("HumanEval split summary")
    print(f"- total task_ids: {total_tasks}")
    print(f"- train task_ids: {len(train_task_ids)}")
    print(f"- test  task_ids: {len(test_task_ids)}")
    print(f"- train CSV rows: {len(train_df)} | test CSV rows: {len(test_df)}")
    print(f"- wrote: {train_out_path}")
    print(f"- wrote: {test_out_path}")


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    humaneval_dir = os.path.join(base_dir, "HUMANEVAL")

    input_csv = os.path.join(humaneval_dir, "human_eval_sft_ready.csv")
    train_out = os.path.join(humaneval_dir, "human_eval_sft_train.csv")
    test_out = os.path.join(humaneval_dir, "human_eval_sft_test.csv")

    split_human_eval_sft_ready(
        input_csv_path=input_csv,
        train_out_path=train_out,
        test_out_path=test_out,
        test_frac=0.25,
    )


if __name__ == "__main__":
    main()

