import ast
import pandas as pd
import json
import os

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Code generation", "Qwen")
)

DATASETS = {
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "ast_mbpp.jsonl"
    }
}


#task_id 643 has an error
df = pd.read_csv(DATASETS["MBPP"]["path"])
#row = df.loc[df["task_id"] == 643].iloc[0]
row = df.loc[df["task_id"] == 641].iloc[0]
code = str(row["GENERATED_CODE"])
try:
    tree = ast.parse(code)
    print(code)
    print('-----------')
    print("AST parsed successfully")
    print(tree)
    print(ast.dump(tree, indent=4))

except Exception as e:
    print("AST Error:", e)
