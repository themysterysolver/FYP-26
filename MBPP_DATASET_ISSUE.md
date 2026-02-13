# MBPP Dataset Mismatch Issue

## Problem Summary

The warnings occur because **63.3% of task IDs in the generation file don't exist in the test file**.

```
Warning: No test found for task_id 79
Warning: No test found for task_id 80
...
```

## Root Cause

**Dataset Misalignment:**
- **Generation file** (`Code generation/Qwen/mbpp_gen.csv`):
  - 327 samples
  - Task IDs: **11 to 809**
  
- **Test file** (`Dataset used/mbpp.csv`):
  - 120 samples  
  - Task IDs: **602 to 809** only

**Result:** 207 out of 327 task IDs (63.3%) have no matching test cases.

## Impact

- Only **120 out of 327 MBPP samples** can be tested
- 207 samples are marked as "TestNotFound" errors
- This inflates your failure rate artificially

## Comparison with Other Datasets

| Dataset | Generation Samples | Test Samples | Match Rate |
|---------|-------------------|--------------|------------|
| DS1000 | 1,000 | ✅ Complete | 100% |
| HumanEval | 164 | ✅ 164 | 100% |
| MBPP | 327 | ❌ 120 | 36.7% |

## Solutions

### Option 1: Get Complete MBPP Test Dataset (Recommended)

The original MBPP dataset has **974 problems**. You're missing tests for task IDs 11-601.

**Action:** Obtain the full MBPP test dataset that includes all task IDs from 11-809.

```bash
# The full MBPP dataset is available at:
# https://github.com/google-research/google-research/tree/master/mbpp
```

### Option 2: Filter Generation File to Match Test File

Only test the 120 samples that have corresponding test cases (task IDs 602-809).

**Script to filter:**

```python
import pandas as pd

# Load datasets
gen_df = pd.read_csv('Code generation/Qwen/mbpp_gen.csv')
test_df = pd.read_csv('Dataset used/mbpp.csv')

# Get valid task IDs
valid_ids = set(test_df['task_id'].unique())

# Filter generation to only valid IDs
filtered_gen = gen_df[gen_df['task_id'].isin(valid_ids)]

# Save filtered version
filtered_gen.to_csv('Code generation/Qwen/mbpp_gen_filtered.csv', index=False)

print(f'Original: {len(gen_df)} samples')
print(f'Filtered: {len(filtered_gen)} samples')
print(f'Removed: {len(gen_df) - len(filtered_gen)} samples')
```

Then update `dynamic_execution.py` to use the filtered file:

```python
"MBPP": {
    "gen_path": GENERATION_DIR / "mbpp_gen_filtered.csv",  # Changed
    "test_path": DATASET_DIR / "mbpp.csv",
    "code_column": "GENERATED_CODE",
    "task_id_column": "task_id"
}
```

### Option 3: Suppress Warnings (Not Recommended)

Keep the current setup but suppress warning messages. This doesn't fix the underlying issue.

## Recommendation

**Use Option 1 or Option 2** depending on your research needs:

- **If you need complete MBPP coverage:** Get the full test dataset (Option 1)
- **If you only care about the 120 samples:** Filter the generation file (Option 2)

## Missing Task ID Ranges

The following task ID ranges are missing from the test file:

```
11-12, 14, 16-20, 56-59, 61-72, 74-75, 77, 79-80, 82-102, 103-106, 108-109,
111, 113, 115-120, 123-133, 135, 137-143, 145, 160-168, 170-172, 222-224,
226-230, 232-235, 237-240, 242, 244-253, 255-262, 264-274, 276-284, 418-448,
450-465, 468, 470-479
```

## Current Behavior

The script continues execution and marks these as:
- **Status:** `failed`
- **Error Type:** `TestNotFound`
- **Error Message:** `"Test case not found in dataset"`

This is correct behavior given the missing data, but it's not ideal for analysis.
