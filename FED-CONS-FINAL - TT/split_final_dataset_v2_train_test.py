import os
from collections import Counter

import numpy as np
import pandas as pd


SEED = 42
TEST_FRAC = 0.25
FAILED_LABEL_MIN_TASKS = 2  # map rare failed_<error> strata into failed_other

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_IN = os.path.join(BASE_DIR, "final_dataset_v2.csv")
CSV_TRAIN = os.path.join(BASE_DIR, "final_dataset_v2_train.csv")
CSV_TEST = os.path.join(BASE_DIR, "final_dataset_v2_test.csv")


def status_norm(x: object) -> str:
    return str(x).strip().lower()


def primary_error(err: object) -> str:
    if pd.isna(err):
        return "unknown"
    s = str(err).strip()
    if not s or s.lower() == "nan":
        return "unknown"
    # Some rows look like: "AttributeError,lib:attribute_error,lib:attribute_error"
    # Keep only the first token as the primary error type.
    return s.split(",")[0].strip() or "unknown"


def main() -> None:
    df = pd.read_csv(CSV_IN)

    required = {"dataset", "task_id", "prompt", "status", "error_types", "canonical_solution"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in input CSV: {missing}")

    # Helper columns for stratification only (will not be written out)
    df["_status_norm"] = df["status"].apply(status_norm)
    df["_primary_error"] = df["error_types"].apply(primary_error)

    # Task-level table (robust even if task_id repeats in future)
    task_df = (
        df.groupby(["dataset", "task_id"], as_index=False)
        .agg(
            task_passed=("_status_norm", lambda s: all(str(v).strip().lower() == "passed" for v in s)),
            primary_error=("_primary_error", lambda s: Counter(list(s)).most_common(1)[0][0] if len(s) else "unknown"),
        )
        .copy()
    )
    task_df["strat_label"] = np.where(
        task_df["task_passed"], "passed", "failed_" + task_df["primary_error"].astype(str)
    )

    # Collapse rare failed strata to avoid unstable splits
    label_counts = task_df["strat_label"].value_counts()
    rare_failed = (task_df["strat_label"] != "passed") & (task_df["strat_label"].map(label_counts) < FAILED_LABEL_MIN_TASKS)
    task_df.loc[rare_failed, "strat_label"] = "failed_other"

    rng = np.random.RandomState(SEED)
    train_task_ids = []
    test_task_ids = []

    # Split separately per dataset so each fine-tuning subset keeps ~75/25.
    for ds, ds_tasks in task_df.groupby("dataset"):
        ds_train = []
        ds_test = []
        for label, label_tasks in ds_tasks.groupby("strat_label"):
            ids = label_tasks["task_id"].tolist()
            rng.shuffle(ids)

            n = len(ids)
            n_test = int(round(n * TEST_FRAC))

            # Prevent empty splits for multi-item strata
            if n > 1:
                n_test = min(max(n_test, 0), n - 1)
            else:
                n_test = 0

            ds_test.extend(ids[:n_test])
            ds_train.extend(ids[n_test:])

        # Small correction to hit closer to 75/25 overall within the dataset
        total = len(ds_tasks)
        target_test = int(round(total * TEST_FRAC))
        # If we overshot/undershot, move tasks across (keeping the moved tasks as-is).
        if len(ds_test) != target_test and total > 1:
            ds_train_set = set(ds_train)
            ds_test_set = set(ds_test)

            if len(ds_test) > target_test:
                # move from test -> train
                candidates = sorted(ds_test_set)
                # deterministic subset to move
                move_n = len(ds_test_set) - target_test
                to_move = candidates[:move_n]
                for tid in to_move:
                    ds_test_set.remove(tid)
                    ds_train_set.add(tid)
            else:
                # move from train -> test
                candidates = sorted(ds_train_set)
                move_n = target_test - len(ds_test_set)
                to_move = candidates[:move_n]
                for tid in to_move:
                    ds_train_set.remove(tid)
                    ds_test_set.add(tid)

            ds_train = list(ds_train_set)
            ds_test = list(ds_test_set)

        train_task_ids.extend(ds_train)
        test_task_ids.extend(ds_test)

    train_task_ids = set(train_task_ids)
    test_task_ids = set(test_task_ids)

    overlap = train_task_ids & test_task_ids
    if overlap:
        raise RuntimeError(f"Split error: task_id overlap found (size={len(overlap)})")

    # Ensure we didn't lose tasks
    all_task_ids = set(task_df["task_id"].tolist())
    if train_task_ids | test_task_ids != all_task_ids:
        raise RuntimeError("Split error: some tasks are missing from both splits")

    # Row-level materialization (task_id is unique today, but keep this generic)
    train_df = df[df["task_id"].isin(train_task_ids)].copy()
    test_df = df[df["task_id"].isin(test_task_ids)].copy()

    # Output with the original schema (preserve column order)
    orig_cols = list(df.columns)
    train_df = train_df[[c for c in orig_cols if not c.startswith("_")]].copy()
    test_df = test_df[[c for c in orig_cols if not c.startswith("_")]].copy()

    # Sanity checks
    if list(train_df.columns) != list(test_df.columns):
        raise RuntimeError("Output schema mismatch between train and test CSVs")

    # Write outputs
    train_df.to_csv(CSV_TRAIN, index=False)
    test_df.to_csv(CSV_TEST, index=False)

    # Verification summary
    def summarize(split_df: pd.DataFrame, split_name: str) -> None:
        print(f"\n== {split_name} ==")
        print(f"rows: {len(split_df)} | tasks: {split_df['task_id'].nunique()}")
        print("dataset counts:", split_df["dataset"].value_counts().to_dict())
        status_counts = split_df["status"].fillna("").astype(str).map(status_norm).value_counts()
        print("status counts:", {k: int(v) for k, v in status_counts.to_dict().items()})
        failed = split_df[split_df["status"].fillna("").astype(str).map(status_norm) != "passed"]
        if len(failed) > 0:
            failed_primary = failed["error_types"].apply(primary_error).value_counts().head(10)
            print("top failed primary_error:", failed_primary.to_dict())

    summarize(train_df, "TRAIN")
    summarize(test_df, "TEST")

    total_rows = len(df)
    print("\n== Overall ==")
    print(f"train_ratio_rows={len(train_df)/total_rows:.4f} (target {1-TEST_FRAC:.2f})")
    print(f"test_ratio_rows ={len(test_df)/total_rows:.4f} (target {TEST_FRAC:.2f})")
    print(f"wrote: {CSV_TRAIN}")
    print(f"wrote: {CSV_TEST}")


if __name__ == "__main__":
    main()

