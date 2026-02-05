
import pandas as pd
import re
import matplotlib.pyplot as plt

def get_columns():
    for file in ["ds1k_gen.csv", "humaneval_gen.csv", "mbpp_gen.csv"]:
        df = pd.read_csv(file)
        print(f"\n{file} columns:")
        print(list(df.columns))

def get_count_status_msg():
    files = {
        "DS1000": ("ds1k_gen.csv", "Status"),
        "HumanEval": ("humaneval_gen.csv", "STATUS"),
        "MBPP": ("mbpp_gen.csv", "STATUS")
    }

    for name, (file, col) in files.items():
        df = pd.read_csv(file)
        print(f"\n{name} distinct {col} values:")
        print(len(df[col].dropna().unique()))
        print(df[col].dropna().unique())

#defining a parser
def parse_status(status):
    if pd.isna(status):
        return "Unknown", None

    status = str(status)

    if status.startswith("Passed"):
        return "Passed", None

    if not status.startswith("Failed"):
        return "Unknown", None

    if "Syntax Hallucination" in status:
        return "Failed", "Syntax Hallucination"

    if "Logic Hallucination" in status:
        return "Failed", "Logic Hallucination"
    
    #only for DS-1K
    if "Logic Error" in status:
        return "Failed", "Logic Hallucination"

    match = re.search(r"Failed:\s*([A-Za-z_]+Error)", status)
    if match:
        return "Failed", match.group(1)

    #last else
    return "Failed", "Other"


get_columns()
get_count_status_msg()

def visualize():
    ds1k = pd.read_csv("ds1k_gen.csv")

    ds1k[["Outcome", "Failure_Type"]] = ds1k["Status"].apply(
        lambda x: pd.Series(parse_status(x))
    )

    he = pd.read_csv("humaneval_gen.csv")

    he[["Outcome", "Failure_Type"]] = he["STATUS"].apply(
        lambda x: pd.Series(parse_status(x))
    )

    mbpp = pd.read_csv("mbpp_gen.csv")

    mbpp[["Outcome", "Failure_Type"]] = mbpp["STATUS"].apply(
        lambda x: pd.Series(parse_status(x))
    )

    #------------------------------------------------------------------------

    def plot_error_distribution(df, title):
        error_counts = (
            df[df["Outcome"] == "Failed"]
            .groupby("Failure_Type")
            .size()
            .sort_values(ascending=False)
        )

        plt.figure(figsize=(10, 5))
        ax = error_counts.plot(kind="bar")

        plt.title(title)
        plt.ylabel("Count")
        plt.xlabel("Failure Type")
        plt.xticks(rotation=45, ha="right")

        # 🔹 Add count labels on bars
        for p in ax.patches:
            ax.annotate(
                str(int(p.get_height())),
                (p.get_x() + p.get_width() / 2, p.get_height()),
                ha="center",
                va="bottom",
                fontsize=9,
                xytext=(0, 3),
                textcoords="offset points"
            )

        plt.tight_layout()
        plt.show()

    plot_error_distribution(ds1k, "DS-1000 Failure Type Distribution")
    plot_error_distribution(he, "HumanEval Failure Type Distribution")
    plot_error_distribution(mbpp, "MBPP Failure Type Distribution")

visualize()










