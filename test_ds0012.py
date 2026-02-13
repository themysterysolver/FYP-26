#!/usr/bin/env python3
"""Test DS0012 specifically to see line number mapping"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Hallucination detection/dynamic'))

from dynamic_execution import execute_ds1000_test
import pandas as pd

# Load DS0012
gen_df = pd.read_csv('Code generation/Qwen/ds1k_gen.csv')
ds0012 = gen_df[gen_df['task_id'] == 'DS0012'].iloc[0]

generated_snippet = str(ds0012['generated_code_snippet'])
full_code = str(ds0012['full_code']).strip()
code_context = str(ds0012['code_context'])

print("=== Testing DS0012 ===\n")
print(f"Snippet (1 line): {generated_snippet}")
print(f"\nFull code (6 lines):")
for i, line in enumerate(full_code.split('\n'), 1):
    print(f"  {i}: {line}")

# Execute
result = execute_ds1000_test(generated_snippet, code_context, full_code)

print("\n=== Results ===")
print(f"Status: {result['status']}")
print(f"Error type: {result['error_type']}")
print(f"Line number: {result['line_number']}")
print(f"Error message: {result['error_message']}")

print("\n=== Expected vs Got ===")
print(f"Expected: Line 4 (indentation error at 'df[\"datetime_column\"] = ...')")
print(f"Got: Line {result['line_number']}")
print(f"Match: {'✓ CORRECT' if result['line_number'] == '4' else '✗ INCORRECT'}")
