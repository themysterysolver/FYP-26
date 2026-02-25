#doubted my check on code_gen intendation
import pandas as pd
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
df = pd.read_csv(SCRIPT_DIR / "mbpp_results_100_to_121.csv")

print(df.columns)
print(df['GENERATED_CODE'][0])