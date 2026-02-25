import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Load CFG summary
df = pd.read_csv(SCRIPT_DIR / "cfg_summary.csv")

unreachable = df["unreachable_code"].sum()
missing_return = df["missing_return"].sum()

labels = ["Unreachable Code", "Missing Return"]
values = [unreachable, missing_return]

plt.figure()
bars = plt.bar(labels, values)

plt.title("CFG Hallucination Distribution")
plt.ylabel("Number of Programs")
plt.xlabel("CFG Issue Type")

# Add counts on top of bars
for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{int(height)}",
        ha="center",
        va="bottom"
    )

plt.tight_layout()
plt.show()
