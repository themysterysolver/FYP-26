import pandas as pd


df = pd.read_csv("master.csv")


out = df[["task_id", "status"]]


out.to_csv("task_status.csv", index=False)

print("task_status.csv created successfully")
