import pandas as pd
import json

# Read the patched_code CSV
df = pd.read_csv("/Users/abhinavh.parthiban/Documents/FYP-26/Hallucination detection/patched_code.csv")

# Find DS0110
idx = df[df['task_id'] == 'DS0110'].index[0]

print(f"Found DS0110 at index {idx}")
print(f"\nOriginal patched code:")
print(df.loc[idx, 'patched_code'])

# Get the current patched code
patched_code = df.loc[idx, 'patched_code']
generated_code = df.loc[idx, 'generated_code']

# Parse dynamic_info to get the error line number
dynamic_info = json.loads(df.loc[idx, 'dynamic_info'])
error_line = int(float(dynamic_info['line_no']))

print(f"\nError should be on line: {error_line}")

# Split the generated code into lines
generated_lines = generated_code.strip().split('\n')

# Create the correct patched code with error markers at the right line
patched_lines = []
for i, line in enumerate(generated_lines, start=1):
    if i == error_line:
        patched_lines.append('<<<< [ERROR START]')
        patched_lines.append(line)
        patched_lines.append('[ERROR FINISH] >>>>')
    else:
        patched_lines.append(line)

new_patched_code = '\n'.join(patched_lines)

print(f"\nNew patched code:")
print(new_patched_code)

# Update the dataframe
df.loc[idx, 'patched_code'] = new_patched_code

# Save the updated CSV
df.to_csv("/Users/abhinavh.parthiban/Documents/FYP-26/Hallucination detection/patched_code.csv", index=False)

print("\n✓ Successfully updated patched_code.csv with correct line number for DS0110")
