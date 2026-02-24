# =========================
# 📊 1️⃣ Error Type Distribution per Dataset (Grouped Bar Chart)
# =========================

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
df = pd.read_csv("dynamic_execution_results.csv")

# Keep only failed rows
error_df = df[df["status"] != "passed"]

# Count error types per dataset
error_counts = (
    error_df.groupby(["dataset", "error_type"])
    .size()
    .unstack(fill_value=0)
)

datasets = error_counts.index.tolist()
error_types = error_counts.columns.tolist()

x = np.arange(len(error_types))
width = 0.25

plt.figure()

for i, dataset in enumerate(datasets):
    plt.bar(
        x + i * width,
        error_counts.loc[dataset],
        width,
        label=dataset
    )

plt.xticks(x + width, error_types, rotation=30)
plt.xlabel("Error Type")
plt.ylabel("Count")
plt.title("Error Type Distribution Across Datasets")
plt.legend()

plt.tight_layout()
plt.show()


# =========================
# 📊 2️⃣ Pass@1 Comparison (Logical vs Passed vs Other Error)
# =========================

# Define Logical Hallucination (AssertionError assumed logical failure)
df["category"] = "Other Error"
df.loc[df["status"] == "passed", "category"] = "Passed"
df.loc[(df["status"] != "passed") & (df["error_type"] == "AssertionError"), "category"] = "Logical"

category_counts = (
    df.groupby(["dataset", "category"])
    .size()
    .unstack(fill_value=0)
)

categories = ["Logical", "Passed", "Other Error"]
x = np.arange(len(categories))

plt.figure()

for i, dataset in enumerate(category_counts.index):
    values = [category_counts.loc[dataset].get(cat, 0) for cat in categories]
    plt.bar(
        x + i * width,
        values,
        width,
        label=dataset
    )

plt.xticks(x + width, categories)
plt.xlabel("Outcome Category")
plt.ylabel("Count")
plt.title("Pass@1 Comparison Across Datasets")
plt.legend()

plt.tight_layout()
plt.show()

