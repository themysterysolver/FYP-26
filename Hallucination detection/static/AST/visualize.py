import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("ast_summary.csv")

syntax = df["syntax_error"].sum()
indent = df["indentation_error"].sum()
structural = df["structural_error"].sum()
clean = (df["ast_parsed"] & 
         (df["syntax_error"] == 0) & 
         (df["indentation_error"] == 0) & 
         (df["structural_error"] == 0)).sum()

labels = ["Syntax Errors", "Indentation Errors", "Structural Hazards", "Clean AST"]
sizes = [syntax, indent, structural, clean]

plt.figure()
bars = plt.bar(labels, sizes)

plt.title("AST Hallucination Distribution")
plt.ylabel("Number of Programs")
plt.xlabel("AST Outcome")


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