import pandas as pd
import json

# Read both CSV files
fault_info = pd.read_csv("/Users/abhinavh.parthiban/Documents/FYP-26/Hallucination detection/Fault Information/fault_information.csv")
patched = pd.read_csv("/Users/abhinavh.parthiban/Documents/FYP-26/Hallucination detection/patched_code.csv")

# Filter for DS0110
fault_ds0110 = fault_info[fault_info['task_id'] == 'DS0110']
patched_ds0110 = patched[patched['task_id'] == 'DS0110']

print("=== FAULT INFORMATION CSV ===")
print(f"Number of rows: {len(fault_ds0110)}")
if len(fault_ds0110) > 0:
    row = fault_ds0110.iloc[0]
    print(f"task_id: {row['task_id']}")
    if pd.notna(row['dynamic_info']) and row['dynamic_info']:
        dynamic_info = json.loads(row['dynamic_info'])
        print(f"dynamic_info line_no: {dynamic_info.get('line_no', 'N/A')}")

print("\n=== PATCHED CODE CSV ===")
print(f"Number of rows: {len(patched_ds0110)}")
if len(patched_ds0110) > 0:
    row = patched_ds0110.iloc[0]
    print(f"task_id: {row['task_id']}")
    if pd.notna(row['dynamic_info']) and row['dynamic_info']:
        dynamic_info = json.loads(row['dynamic_info'])
        print(f"dynamic_info line_no: {dynamic_info.get('line_no', 'N/A')}")
    print(f"\nGenerated code:\n{row['generated_code']}")
    print(f"\nPatched code:\n{row['patched_code']}")
