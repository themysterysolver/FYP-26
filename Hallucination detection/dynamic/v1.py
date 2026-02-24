# =========================
# 1️⃣ Count Passed vs Hallucinated (Failed)
# =========================

import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_csv("dynamic_execution_results.csv")

# Count status
status_counts = df["status"].value_counts()

# Plot
plt.figure()
plt.bar(status_counts.index.astype(str), status_counts.values)

plt.title("Passed vs Hallucinated (Failed)")
plt.xlabel("Status")
plt.ylabel("Count")

# Add labels
for i, value in enumerate(status_counts.values):
    plt.text(i, value, str(value), ha="center", va="bottom")

plt.tight_layout()
plt.show()
