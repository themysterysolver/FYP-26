# Where to upload on your server

Put **everything in one folder** (same directory):

| File / folder | Purpose |
|---------------|---------|
| `Verify_DS1000_Adapter_Windows.ipynb` | This notebook (JSON-only config). |
| `verification_task_ids.json` | Task list + optional `expected.*` + optional `verification_expect_key`. |
| `ds1000_pipeline_output.csv` | Baseline pipeline output (must include every `task_id` from the JSON). |
| `lora_adapters/` | Your LoRA (or a single subfolder with `adapter_config.json`). You can use `lora_adapters.zip` instead. |

Optional in JSON:

```json
"verification_expect_key": "federroravg_adapter"
```

Use `"fedavg_adapter"` when you load the **FedAvg** LoRA; use `"federroravg_adapter"` for **FedErrorAvg** (default in this notebook if omitted).

Start Jupyter from that folder or open the notebook so `os.getcwd()` is that folder (the notebook resolves paths from `NOTEBOOK_DIR` = notebook file directory when possible).

A sample `verification_task_ids.json` is included in this folder; replace with your own from `WORKING/ds1000/` in the repo if needed.
