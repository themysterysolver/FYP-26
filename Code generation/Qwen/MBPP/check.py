#doubted my check on code_gen intendation
import pandas as pd
import numpy as np
df = pd.read_csv(r"D:\Desktop\MIT\CODES\FOR GIT HUB\FYP-26\Code generation\MBPP\mbpp_results_100_to_121.csv")

print(df.columns)
print(df['GENERATED_CODE'][0])