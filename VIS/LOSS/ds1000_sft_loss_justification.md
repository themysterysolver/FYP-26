# DS1000 SFT training loss (Qwen2.5-Coder-3B + LoRA)

This note supports the loss figure produced from the supervised fine-tuning run documented in [`FED-CONS-FINAL - TT/DS1000/SFT_LoRA_Adapters_Windows_try_fix.ipynb`](../../FED-CONS-FINAL%20-%20TT/DS1000/SFT_LoRA_Adapters_Windows_try_fix.ipynb).

## What the curve measures

Training uses TRL’s `SFTTrainer` with causal language-modeling **cross-entropy** on the target sequence. The notebook configures completion-oriented supervision via `DataCollatorForCompletionOnlyLM` (response starts after `<|im_start|>assistant\n`), so loss is intended to reflect **predicting the assistant’s code/solution tokens**, not the user prompt. Hugging Face logs a **running training loss** every `logging_steps=5` global optimizer steps.

Some batches in the saved run emit tokenizer/collator warnings (e.g. template fragments not found in a few long or unusual examples). Those samples may be skipped or partially masked; they add noise but do not change the overall interpretation: the model is still being trained to minimize next-token error on valid supervision tokens.

## How to read the plot

- **X-axis**: global step (one entry every five steps). With `per_device_train_batch_size=1`, `gradient_accumulation_steps=8`, and 1000 training examples, one epoch is **125** optimizer steps; the saved run completes **3** epochs (**375** steps).
- **Y-axis**: reported training loss (lower is better, unbounded below but typically positive).
- **Dashed vertical lines**: epoch boundaries (after steps 125 and 250).
- **Shape**: a clear downward trend from the first epoch into the second, with **residual jitter** typical of small effective batch size and heterogeneous coding tasks. The third epoch continues refinement at lower loss values.

Aggregated run summary (from notebook output): mean `training_loss` ≈ **0.251** over 375 steps (`ds1000_sft_run_summary.json`).

## Why two epochs can still be a defensible FYP choice

The figure you export here documents the **full three-epoch** run saved in the notebook. For thesis scope, it is still reasonable to **standardize on two epochs** (or fewer) for other experiments because:

1. **Compute and iteration speed**: Each extra epoch multiplies GPU time and slows federated or ablation cycles; a cap keeps the project tractable.
2. **Diminishing returns**: In many SFT settings, the **largest relative drop** in loss appears early; later epochs polish the adapter rather than changing behavior as dramatically. Your curve is consistent with a large improvement when moving from epoch 1 into epoch 2, with smaller marginal changes afterward.
3. **Federated context**: If the research question is aggregation or client heterogeneity rather than squeezing the last bit of single-node SFT performance, a fixed modest budget (e.g. two epochs) is a clear, reproducible design choice.

State explicitly in the thesis that **epoch budget is an experimental constraint**, and cite this figure when you need evidence that training was stable and loss decreased under the DS1000 + LoRA setup.

## Files in this folder

| File | Role |
|------|------|
| [`ds1000_sft_training_loss.csv`](ds1000_sft_training_loss.csv) | One row per log point: `step`, `epoch`, `training_loss`. |
| [`ds1000_sft_run_summary.json`](ds1000_sft_run_summary.json) | Epoch layout, steps per epoch, mean training loss / global step from `TrainOutput`. |
| [`ds1000_sft_training_loss.png`](ds1000_sft_training_loss.png) | Loss vs step with epoch boundary markers. |
| [`extract_ds1000_sft_loss.py`](extract_ds1000_sft_loss.py) | Regenerates CSV/JSON from the notebook. |
| [`plot_ds1000_sft_loss.py`](plot_ds1000_sft_loss.py) | Regenerates the PNG from the CSV. |

## Regenerating after a new training run

Re-execute the DS1000 notebook, save it, then from the repo root:

```text
python VIS/LOSS/extract_ds1000_sft_loss.py
python VIS/LOSS/plot_ds1000_sft_loss.py
```
