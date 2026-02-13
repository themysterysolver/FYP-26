#!/usr/bin/env python3
"""Quick verification script for dynamic execution results."""

import pandas as pd

# Load results
df = pd.read_csv("dynamic_execution_results.csv")

print("=" * 80)
print("Dynamic Execution Results Summary")
print("=" * 80)

print(f"\nTotal test cases: {len(df)}")
print(f"  Passed: {len(df[df['status']=='passed'])} ({100*len(df[df['status']=='passed'])/len(df):.1f}%)")
print(f"  Failed: {len(df[df['status']=='failed'])} ({100*len(df[df['status']=='failed'])/len(df):.1f}%)")

print("\nDataset breakdown:")
for dataset in ['DS1000', 'HumanEval', 'MBPP']:
    subset = df[df['dataset'] == dataset]
    passed = len(subset[subset['status'] == 'passed'])
    total = len(subset)
    print(f"  {dataset:12s}: {passed:4d}/{total:4d} passed ({100*passed/total:5.1f}%)")

print("\nTop 10 error types:")
error_counts = df[df['status']=='failed']['error_type'].value_counts().head(10)
for error_type, count in error_counts.items():
    print(f"  {error_type:25s}: {count:4d}")

print("\n" + "=" * 80)
print("Sample results:")
print("=" * 80)

# Sample passed test
print("\n1. PASSED TEST EXAMPLE:")
passed = df[df['status']=='passed'].head(1)
for _, row in passed.iterrows():
    print(f"   Dataset: {row['dataset']}")
    print(f"   Task ID: {row['task_id']}")
    print(f"   Status: {row['status']}")
    print(f"   Error fields: (all empty as expected)")

# Sample failed tests with different error types
print("\n2. FAILED TEST EXAMPLES:")

for error_type in ['SyntaxError', 'IndentationError', 'NameError', 'AssertionError']:
    sample = df[df['error_type']==error_type].head(1)
    if not sample.empty:
        row = sample.iloc[0]
        print(f"\n   {error_type}:")
        print(f"     Task ID: {row['task_id']}")
        msg = str(row['error_message']) if pd.notna(row['error_message']) else "(empty)"
        if len(msg) > 60:
            msg = msg[:60] + "..."
        print(f"     Message: {msg}")
        line = str(int(row['line_number'])) if pd.notna(row['line_number']) else "(empty)"
        print(f"     Line: {line}")

print("\n" + "=" * 80)
print("Verification complete!")
print("=" * 80)
