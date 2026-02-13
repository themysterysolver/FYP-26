#!/usr/bin/env python3
"""Test DS0020 specifically with the fixed logic"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Hallucination detection/dynamic'))

from dynamic_execution import execute_ds1000_test
import pandas as pd

# Load DS0020
gen_df = pd.read_csv('Code generation/Qwen/ds1k_gen.csv')
ds0020 = gen_df[gen_df['task_id'] == 'DS0020'].iloc[0]

generated_snippet = str(ds0020['generated_code_snippet'])
full_code = str(ds0020['full_code'])
code_context = str(ds0020['code_context'])

print("=== Testing DS0020 with fixed logic ===\n")
print(f"Snippet (1 line): {generated_snippet[:60]}...")
print(f"Full code (7 lines):\n{full_code}\n")

# Execute
result = execute_ds1000_test(generated_snippet, code_context, full_code)

print("=== Results ===")
print(f"Status: {result['status']}")
print(f"Error type: {result['error_type']}")
print(f"Line number: {result['line_number']}")
print(f"Error message: {result['error_message']}")

print("\n=== Verification ===")
print(f"Expected: Line 4 (in full_code)")
print(f"Got: Line {result['line_number']}")
print(f"Match: {'✓ CORRECT' if result['line_number'] == '4' else '✗ INCORRECT'}")
