import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

df = pd.read_csv(SCRIPT_DIR / "ds1k_gen.csv")
df["task_id"] = [f"DS{str(i).zfill(4)}" for i in range(len(df))]
df.to_csv(SCRIPT_DIR / "ds1k_gen.csv", index=False)