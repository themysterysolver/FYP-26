import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

df = pd.read_csv(SCRIPT_DIR / "master.csv")


out = df[["task_id", "status"]]


out.to_csv(SCRIPT_DIR / "task_status.csv", index=False)

print("task_status.csv created successfully")
