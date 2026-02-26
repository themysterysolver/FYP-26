import pandas as pd

# Load files
ds1000 = pd.read_csv("ds1000_pipeline_output.csv")
humaneval = pd.read_csv("humaneval_pipeline_output.csv")
mbpp = pd.read_csv("mbpp_pipeline_output.csv")

# Combine all
combined_df = pd.concat([ds1000, humaneval, mbpp], ignore_index=True)

# Ensure patched_code exists
if "patched_code" in combined_df.columns and "dynamic_info" in combined_df.columns:

    # Get column order
    cols = list(combined_df.columns)

    # Remove dynamic_info temporarily
    cols.remove("dynamic_info")

    # Find index of patched_code
    patch_index = cols.index("patched_code")

    # Insert dynamic_info immediately after patched_code
    cols.insert(patch_index + 1, "dynamic_info")

    # Reorder dataframe
    combined_df = combined_df[cols]

# Save final combined file
combined_df.to_csv("final_combined_pipeline_output.csv", index=False)

print("✅ Combined and reordered successfully.")