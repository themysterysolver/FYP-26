#doubted my check on code_gen intendation
import pandas as pd
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
df = pd.read_csv(SCRIPT_DIR / "ds1k_results_0_to_100.csv")

print(df.columns)
print(df['full_code'][0])