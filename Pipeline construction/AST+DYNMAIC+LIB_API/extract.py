import pandas as pd

ds1000 = pd.read_csv("ds1000_pipeline_output.csv")
humaneval = pd.read_csv("humaneval_pipeline_output.csv")
mbpp = pd.read_csv("mbpp_pipeline_output.csv")

task_id_ds1000 = ds1000[ds1000["status"] == "hallucinated"]["task_id"].tolist()
task_id_humaneval = humaneval[humaneval["status"] == "hallucinated"]["task_id"].tolist()
task_id_mbpp = mbpp[mbpp["status"] == "hallucinated"]["task_id"].tolist()

with open("output.py", "w") as f:
    f.write("task_id_ds1000 = " + str(task_id_ds1000) + "\n\n")
    f.write("task_id_humaneval = " + str(task_id_humaneval) + "\n\n")
    f.write("task_id_mbpp = " + str(task_id_mbpp) + "\n")

print("✅ output.py generated successfully!")