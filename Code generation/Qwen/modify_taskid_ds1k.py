import pandas as pd

# 1️⃣ Read CSV
df = pd.read_csv("ds1k_gen.csv", encoding="utf-8")

cols = ["task_id"] + [col for col in df.columns if col != "task_id"]
df = df[cols]

# 4️⃣ Save back
df.to_csv("ds1k_gen_updated.csv", index=False)

print("Done ✔")