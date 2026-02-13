import pandas as pd

# ===============================
# 1️⃣ LOAD GENERATION FILES
# ===============================

# ---- DS1000 ----
ds = pd.read_csv("ds1k_gen.csv")
ds_gen = ds[["task_id", "full_code", "Status", "reference_code"]].copy()
ds_gen.rename(columns={
    "full_code": "generated_code",
    "Status": "status",
    "reference_code": "solution"
}, inplace=True)
ds_gen["dataset"] = "DS1000"


# ---- HumanEval ----
he = pd.read_csv("humaneval_gen.csv")
he_gen = he[["task_id", "GENERATED_CODE", "STATUS", "canonical_solution"]].copy()
he_gen.rename(columns={
    "GENERATED_CODE": "generated_code",
    "STATUS": "status",
    "canonical_solution": "solution"
}, inplace=True)
he_gen["dataset"] = "HumanEval"


# ---- MBPP ----
mbpp = pd.read_csv("mbpp_gen.csv")
mbpp_gen = mbpp[["task_id", "GENERATED_CODE", "STATUS", "code"]].copy()
mbpp_gen.rename(columns={
    "GENERATED_CODE": "generated_code",
    "STATUS": "status",
    "code": "solution"
}, inplace=True)
mbpp_gen["dataset"] = "MBPP"


# Combine all generation data
gen_master = pd.concat([ds_gen, he_gen, mbpp_gen], ignore_index=True)


# ===============================
# 2️⃣ LOAD STATIC + LIBAPI FILES
# ===============================

ast_df = pd.read_csv("ast_summary.csv")
cfg_df = pd.read_csv("cfg_summary.csv")
lib_df = pd.read_csv("libapi_summary.csv")

gen_master["dataset"] = gen_master["dataset"].str.strip()
ast_df["dataset"] = ast_df["dataset"].str.strip()
cfg_df["dataset"] = cfg_df["dataset"].str.strip()
lib_df["dataset"] = lib_df["dataset"].str.strip()

gen_master["task_id"] = gen_master["task_id"].astype(str)
ast_df["task_id"] = ast_df["task_id"].astype(str)
cfg_df["task_id"] = cfg_df["task_id"].astype(str)
lib_df["task_id"] = lib_df["task_id"].astype(str)



# ===============================
# 3️⃣ MERGE EVERYTHING
# ===============================

master = gen_master.merge(ast_df, on=["dataset", "task_id"], how="left")
master = master.merge(cfg_df, on=["dataset", "task_id"], how="left")
master = master.merge(lib_df, on=["dataset", "task_id"], how="left")


# ===============================
# 4️⃣ REORDER COLUMNS
# ===============================

# Put generated_code and solution next to each other
core_columns = [
    "dataset",
    "task_id",
    "generated_code",
    "solution",
    "status"
]

# Keep the rest automatically
other_columns = [col for col in master.columns if col not in core_columns]

master = master[core_columns + other_columns]

#priortatoze
priority_columns = [
    "dataset",
    "task_id",
    "generated_code",
    "solution",
    "status",
    "libapi_details",
    "message",
    "cfg_details",
    
]

# Keep everything else automatically
remaining_columns = [col for col in master.columns if col not in priority_columns]

master = master[priority_columns + remaining_columns]

print("Reordered Columns:")
print(master.columns.tolist())


# ===============================
# 5️⃣ SAVE FINAL CSV
# ===============================

master.to_csv("hallucination_master_table.csv", index=False)

print("✅ Master CSV created successfully!")
print("Final Shape:", master.shape)
print("Columns:", master.columns.tolist())