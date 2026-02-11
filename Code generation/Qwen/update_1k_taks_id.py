import pandas as pd

df = pd.read_csv("ds1k_gen.csv")
df["task_id"] = [f"DS{str(i).zfill(4)}" for i in range(len(df))]
df.to_csv("ds1k_gen.csv", index=False)