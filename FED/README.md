# SFT on HumanEval (Qwen2.5-Coder-3B, LoRA, T4)

Supervised fine-tuning of **Qwen2.5-Coder-3B-Instruct** on the HumanEval subset of `final_dataset_v2.csv` using **QLoRA** (4-bit + LoRA). Designed for Google Colab with **T4 GPU**.

Outputs LoRA adapters in PEFT format and a FedAvg-ready `lora_state_dict.pt`.
