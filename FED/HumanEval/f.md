SFT on HumanEval in Colab (T4) – Implementation Plan

Context and inputs





Data source: [Pipeline construction/AST+DYNMAIC+LIB_API/final_dataset_v2.csv](Pipeline construction/AST+DYNMAIC+LIB_API/final_dataset_v2.csv)
Columns used: dataset, task_id, prompt, canonical_solution.
The prompt column is the full generation prompt as a single string: "System: ...\n\nUser: ..." (built in [prompt_extractor.ipynb](Pipeline construction/AST+DYNMAIC+LIB_API/prompt_extractor.ipynb) via messages_to_prompt_string).



HumanEval subset: Filter rows with dataset == "humaneval" (164 rows).



Model: Qwen/Qwen2.5-Coder-3B-Instruct.



Hardware: Colab with T4 GPU (16 GB VRAM).



Output location: Notebook stored in FED folder at repo root (create FED/ if it does not exist). Suggested notebook name: SFT_HumanEval_Colab.ipynb.

Data flow

flowchart LR
  subgraph input [Input]
    CSV[final_dataset_v2.csv]
  end
  subgraph prep [Preparation]
    Filter[Filter dataset eq humaneval]
    Parse[Parse prompt to system and user]
    Messages[Build messages with assistant]
  end
  subgraph train [Training]
    HFDS[HuggingFace Dataset]
    Template[Apply Qwen chat template]
    LoRA[QLoRA SFT]
  end
  CSV --> Filter --> Parse --> Messages --> HFDS --> Template --> LoRA

1. Notebook structure and placement





Create directory FED at repo root: FYP-26/FED/.



Create FED/SFT_HumanEval_Colab.ipynb with the following sections (each as one or more cells).

2. Colab setup and GPU





Cell 1 (Markdown): Title and short description (SFT on HumanEval with Qwen2.5-Coder-3B, LoRA, T4).



Cell 2 (Code):  





Check GPU: !nvidia-smi (optional).  



Ensure GPU is selected: Runtime → Change runtime type → T4 GPU.  



No code to “enable” GPU; Colab uses it when available.

3. Install dependencies





Cell 3 (Code) (single !pip install or multiple):
transformers, peft, bitsandbytes, datasets, trl, accelerate, pandas.
Pin versions that are known to work together (e.g. transformers>=4.36, peft>=0.7, bitsandbytes>=0.41, trl>=0.7).
Restart runtime after install if the notebook instructs it.

4. Data loading





Cell 4 (Code) – Load CSV in a Colab-friendly way:





Option A (default): Upload final_dataset_v2.csv to the Colab session (e.g. from google.colab import files; uploaded = files.upload()), then set CSV_PATH = list(uploaded.keys())[0] or the path where the file is saved.



Option B: Optional Google Drive mount; set CSV_PATH to the path of the CSV on Drive (e.g. "/content/drive/MyDrive/.../final_dataset_v2.csv").



Use pandas: df = pd.read_csv(CSV_PATH) so that quoted multiline fields (e.g. prompt, canonical_solution) are read correctly.



Cell 5 (Code) – Filter and validate:





df_he = df[df["dataset"] == "humaneval"].copy().



Assert or check len(df_he) == 164.



Drop rows where prompt or canonical_solution is null/empty (if any); optionally strip whitespace on canonical_solution.

5. Parse prompt and build chat messages





Cell 6 (Code) – Parse the prompt string into system and user:





The column format is: "System: <system_text>\n\nUser: <user_text>".



Split only on the first occurrence of "\n\nUser: " so that any \n\n inside the user text is preserved.



Example logic:





idx = row["prompt"].find("\n\nUser: ")



system_content = row["prompt"][:idx].replace("System: ", "", 1).strip()



user_content = row["prompt"][idx + len("\n\nUser: "):].strip()



Build per-row: messages = [{"role": "system", "content": system_content}, {"role": "user", "content": user_content}, {"role": "assistant", "content": row["canonical_solution"]}].



Cell 7 (Code) – Build HuggingFace Dataset:





From the list of messages, create a datasets.Dataset with a single column "messages" (each element is the list of 3 dicts above).  



This matches the format expected by SFTTrainer with dataset_text_field not set and the dataset having a messages column.

6. Model and tokenizer





Cell 8 (Code):





Load tokenizer: AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-3B-Instruct", trust_remote_code=True).



Set padding side to "left" for generation (optional but common for decoder-only), and ensure the tokenizer has a chat_template (Qwen uses ChatML); if not set by default, set it explicitly.



Cell 9 (Code) – Load base model in 4-bit for T4:





BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4") (or fp16 if bfloat16 is not supported on T4).



AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-3B-Instruct", quantization_config=..., device_map="auto", trust_remote_code=True).

7. LoRA (PEFT) configuration





Cell 10 (Code):





LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj","k_proj","o_proj","gate_proj","up_proj","down_proj"], lora_dropout=0.05, bias="none", task_type="CAUSAL_LM").



get_peft_model(model, peft_config) and optionally model.print_trainable_parameters().

8. Training arguments and SFTTrainer





Cell 11 (Code) – TrainingArguments:





output_dir="./sft_humaneval_output" (or a path under /content/ so it persists during the session).



num_train_epochs=3, per_device_train_batch_size=2, gradient_accumulation_steps=4 (effective batch size 8).



learning_rate=2e-4, weight_decay=0.01, warmup_ratio=0.03 or warmup_steps=10, lr_scheduler_type="cosine".



logging_steps=5, save_strategy="epoch", bf16=True if T4 supports it, else fp16=True.



max_grad_norm=0.3, max_steps=-1 (use epochs).



Cell 12 (Code) – SFTTrainer:





model=model, args=training_args, train_dataset=dataset, dataset_text_field=None, dataset_kwargs={"columns": ["messages"]} or equivalent so the trainer uses the messages column.



Use the tokenizer’s chat template: tokenizer.apply_chat_template(..., tokenize=False) in a custom formatting function, or pass processing_class=tokenizer and let the trainer use the default chat handling (see trl docs for exact parameter name, e.g. dataset_num_proc and ensuring the dataset yields messages).



Max sequence length: max_seq_length=2048 (or 1024 if OOM). This caps prompt+response length and avoids T4 OOM.



Label masking: Only assistant tokens should have non‑negative labels; system and user should be masked (-100). The SFTTrainer with messages and a chat model should do this when using the tokenizer’s chat template; confirm in trl that the trainer sets labels accordingly (assistant part only).



No data_collator override unless needed; default is fine when using messages.

9. Run training and save





Cell 13 (Code) – trainer.train().



Cell 14 (Code) – Save full adapter (PEFT format, for inference and FedAvg):





ADAPTER_DIR = "./sft_humaneval_output/lora_adapters" (or similar).



trainer.save_model(ADAPTER_DIR) and tokenizer.save_pretrained(ADAPTER_DIR).



This writes adapter_config.json and adapter_model.safetensors (standard PEFT format); FedAvg can load these per client and average the underlying tensors.



Optional: copy ADAPTER_DIR to Google Drive so the adapter is not lost after session end.

9b. Get and print LoRA adapters (FedAvg-ready, visible as output)





Cell 15 (Code) – Get LoRA adapter state and make it visible:





Get only the trainable (LoRA) parameters:
lora_state = {k: v.detach().cpu().clone() for k, v in model.named_parameters() if v.requires_grad}.



Print adapter structure (so it appears as notebook output):  





Loop over lora_state.items() and print each name and tensor.shape (e.g. "base_model.model.model.layers.0.self_attn.q_proj.lora_A.default: torch.Size([16, 2048])").  



Optionally print a one-line summary per param (e.g. min, max, norm) so the adapters are visibly inspected.



Print a short summary: total number of LoRA parameters, total element count, and list of parameter names (so FedAvg code knows which keys to average).



Cell 16 (Code) – Save FedAvg-ready adapter snapshot (optional but recommended):





Save the LoRA-only state dict so FedAvg can load and average without the full model:
torch.save(lora_state, f"{ADAPTER_DIR}/lora_state_dict.pt").  



Alternatively or additionally save in safetensors: use peft.get_peft_model(...).save_pretrained(ADAPTER_DIR) which already writes adapter_model.safetensors; for FedAvg you can load with peft.PeftModel.from_pretrained(base_model, ADAPTER_DIR) and then read model.state_dict() filtered to LoRA keys, or use a small script that loads multiple adapter_model.safetensors, averages them, and saves the result.



Add a markdown cell above this cell explaining that lora_state_dict.pt (or adapter_model.safetensors) is the file to use for FedAvg aggregation.

10. Sanity check before full run (recommended)





Optional cell after building the dataset and before training: run trainer.train(max_steps=2) (or 1 step) to verify no OOM and that loss decreases. Then run full training in the main training cell.

11. Important implementation details





CSV path in Colab: The notebook must not hardcode a local Windows path. Use a variable CSV_PATH set by upload or Drive path so it runs as-is in Colab.



Parsing robustness: If "\n\nUser: " is missing for a row, skip that row or use a fallback (e.g. treat whole prompt as user content and use a default system message) and log a warning.



Tokenizer chat template: Qwen2.5-Coder uses ChatML; apply_chat_template(..., tokenize=True, add_generation_prompt=False) with the 3-turn messages produces the full sequence. The trainer must set labels so that only the assistant turn tokens are trained (rest -100). TRL’s SFTTrainer with messages and the correct tokenizer typically does this; double-check in code or docs.



T4 memory: With 4-bit model, LoRA, and batch size 2, 16 GB is usually sufficient. If OOM: reduce per_device_train_batch_size to 1, or max_seq_length to 1024, or gradient checkpointing.

12. FedAvg note





For FedAvg, all clients must use the same LoRA config (same r, lora_alpha, target_modules) so that state dict keys and shapes match when averaging. The notebook will use a fixed config; document it (e.g. in a markdown cell) so your FedAvg script uses the same config when loading and averaging lora_state_dict.pt or adapter_model.safetensors from multiple runs.

13. Deliverable





Single file: FED/SFT_HumanEval_Colab.ipynb (to be created).



No changes to [final_dataset_v2.csv](Pipeline construction/AST+DYNMAIC+LIB_API/final_dataset_v2.csv) or to PHASE_1_RUN / prompt_extractor; the notebook only reads the CSV and uses the existing prompt format.



Adapter visibility: Running the notebook will print the LoRA adapter structure (parameter names and shapes) and optionally per-parameter stats, and will save adapters in PEFT format plus a FedAvg-ready lora_state_dict.pt (or equivalent).



User flow: open the notebook in Colab, upload CSV (or set Drive path), run all cells; training runs on T4; adapters are printed and saved under the chosen output dir and optionally to Drive.