import pandas as pd

df_before = pd.read_csv("humaneval_pipeline_output.csv")
df_after  = pd.read_csv("humaneval_pipeline_output_f.csv")

merged = df_before[['task_id','status']].merge(
    df_after[['task_id','status']],
    on='task_id',
    suffixes=('_before','_after')
)

fixed = merged[(merged.status_before!='passed') & (merged.status_after=='passed')]

print("Fixed problems:")
print(fixed)