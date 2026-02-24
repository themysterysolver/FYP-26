import pandas as pd

# Load AST summary
df = pd.read_csv("ast_summary.csv")

# Filter failed parses
failed = df[df["ast_parsed"] == False][["task_id"]]

# Save
failed.to_csv("failed_ast_task_ids.csv", index=False)

print("Saved failed_ast_task_ids.csv")