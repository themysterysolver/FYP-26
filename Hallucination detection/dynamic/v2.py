# =========================
# 2️⃣ Count Different Error Types
# =========================

import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv("dynamic_execution_results.csv")

# Remove passed rows (only keep hallucinated errors)
error_df = df[df["status"] != "passed"]

# Count error types
error_counts = error_df["error_type"].value_counts()

# Plot
plt.figure()
plt.bar(error_counts.index.astype(str), error_counts.values)

plt.title("Different Types of Errors")
plt.xlabel("Error Type")
plt.ylabel("Count")

# Rotate labels for readability
plt.xticks(rotation=30)

# Add labels
for i, value in enumerate(error_counts.values):
    plt.text(i, value, str(value), ha="center", va="bottom")

plt.tight_layout()
plt.show()
