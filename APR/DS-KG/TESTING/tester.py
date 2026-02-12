import ast
import pandas as pd
import json
import os
import importlib
import inspect
import builtins

# =========================
# PATH CONFIG
# =========================
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Code generation", "Qwen")
)

DATASETS = {
    "DS1000": {
        "path": os.path.join(BASE_DIR, "ds1k_gen.csv"),
        "code_column": "full_code",
        "task_id_column": None,
        "output": "libapi_ds1000.jsonl"
    },
    "HumanEval": {
        "path": os.path.join(BASE_DIR, "humaneval_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "libapi_humaneval.jsonl"
    },
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "libapi_mbpp.jsonl"
    }
}

ds_path = DATASETS["DS1000"]["path"]
df = pd.read_csv(ds_path)

# Check if task_id column exists
if "task_id" in df.columns:
    df = pd.read_csv(DATASETS["DS1000"]["path"])

    row_72 = df.iloc[72]   # 0-indexed (73rd row)
    print(row_72)
else:
    print("DS1000 does not contain task_id column.")