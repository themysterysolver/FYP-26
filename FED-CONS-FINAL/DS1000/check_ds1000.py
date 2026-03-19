import math
import torch
from safetensors.torch import load_file

p = r"D:\Desktop\MIT\CODES\FYP-26\FED-CONS-FINAL\DS1000\lora_adapters_ds1000\adapter_model.safetensors"
sd = load_file(p)

nan = inf = 0
l2sq = 0.0
max_abs = 0.0

for t in sd.values():
    tt = t.float()
    nan += torch.isnan(tt).sum().item()
    inf += torch.isinf(tt).sum().item()
    l2sq += float((tt * tt).sum().item())
    max_abs = max(max_abs, float(tt.abs().max().item()))

print("keys:", len(sd))
print("nan:", nan, "inf:", inf)
print("max_abs:", max_abs)
print("l2:", math.sqrt(l2sq))