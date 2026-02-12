import pandas as pd
import os

FILES = [
    "ds1k_gen.csv",
    "humaneval_gen.csv",
    "mbpp_gen.csv",
    "ast_summary.csv",
    "cfg_summary.csv",
    "libapi_summary.csv"
]

def inspect_csv(file):
    print("\n" + "="*80)
    print(f"FILE: {file}")
    print("="*80)

    try:
        df = pd.read_csv(file)

        print("\nColumns:")
        print(df.columns.tolist())

        print("\nShape:")
        print(df.shape)

        print("\nSample Rows:")
        print(df.head(2))

    except Exception as e:
        print(f"Error loading {file}: {e}")

for file in FILES:
    if os.path.exists(file):
        inspect_csv(file)
    else:
        print(f"\n❌ File not found: {file}")
