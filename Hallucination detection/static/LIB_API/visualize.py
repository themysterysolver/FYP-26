import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Load summary
df = pd.read_csv(SCRIPT_DIR / "libapi_summary.csv")

error_types = [
    "name_error",
    "attribute_error",
    "type_error",
    "module_not_found",
    # "potential_key_error"
]

counts = [df[col].sum() for col in error_types]

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
plt.savefig(SCRIPT_DIR / "library_api.png", dpi=300)
plt.show()
