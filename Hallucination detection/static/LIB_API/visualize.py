import pandas as pd
import matplotlib.pyplot as plt
import ast

# Load summary
df = pd.read_csv("libapi_summary.csv")

# Dictionary to count error types
error_counter = {}

for details in df["libapi_details"]:
    if pd.isna(details):
        continue

    try:
        errors = ast.literal_eval(details)  # Convert string → list
    except Exception:
        continue

    for err in errors:
        err_type = err.get("type")
        error_counter[err_type] = error_counter.get(err_type, 0) + 1


# Prepare plotting
labels = list(error_counter.keys())
counts = list(error_counter.values())

plt.figure()
bars = plt.bar(labels, counts)

plt.title("Library / API Hallucination Distribution")
plt.ylabel("Total Error Count")
plt.xlabel("Error Type")

for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        str(int(height)),
        ha="center",
        va="bottom"
    )

plt.xticks(rotation=25)
plt.tight_layout()
plt.savefig("library_api.png", dpi=300)
plt.show()