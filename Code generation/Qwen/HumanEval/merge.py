import pandas as pd
import glob
import os

def merge_ds1k_csvs(
    directory=".",
    output_file="humaneval_merged.csv"
):
    """
    Merges all ds1k_results_*.csv files in a directory into one CSV.
    """

    pattern = os.path.join(directory, "humaneval_results_*_to_*.csv")
    csv_files = sorted(glob.glob(pattern))

    if not csv_files:
        raise FileNotFoundError("No humaneval_results_*_to_*.csv files found")

    print("Found files:")
    for f in csv_files:
        print(" -", os.path.basename(f))

    dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        dfs.append(df)

    merged_df = pd.concat(dfs, ignore_index=True)

    merged_df.to_csv(output_file, index=False)

    print(f"\n✅ Merged {len(csv_files)} files")
    print(f"📁 Output saved as: {output_file}")
    print(f"📊 Total rows: {len(merged_df)}")

    return merged_df


if __name__ == "__main__":
    merge_ds1k_csvs()
