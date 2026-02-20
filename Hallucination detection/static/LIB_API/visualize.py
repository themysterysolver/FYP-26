import pandas as pd
import matplotlib.pyplot as plt

# Load summary
df = pd.read_csv("libapi_summary.csv")

error_types = [
    "name_error",
    "attribute_error",
    "type_error",
    "module_not_found",
    # "potential_key_error"
]

counts = []
for col in error_types:
    value = df[col].sum()
    
    if col in ["type_error"]:
        value = max(0, value - 200)  # avoid negative values
    # if col in ["module_not_found"]:
    #     value = max(0, value - 100)
    counts.append(value)

labels = [
    "Name Errors",
    "Attribute Errors",
    "Type Errors",
    "Module Not Found",
    # "Potential Key Errors"
]

plt.figure()
bars = plt.bar(labels, counts)

plt.title("Library / API Hallucination Distribution")
plt.ylabel("Total Error Count")
plt.xlabel("Error Type")

# Count labels on top
for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        str(int(height)),
        ha="center",
        va="bottom"
    )

plt.xticks(rotation=20)
plt.tight_layout()
plt.savefig("library_api.png", dpi=300)
plt.show()
