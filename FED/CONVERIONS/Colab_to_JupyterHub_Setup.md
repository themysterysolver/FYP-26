# Replicate Google Colab Environment in CTSKII JupyterHub

Aligned with **CTSKII JupyterHub** conventions (see `/examples/welcome_ctskii.ipynb` and `/examples/README.ipynb`).

## Problem

Code works on Google Colab but fails in CTSKII JupyterHub due to version mismatches (e.g. `transformers`, `peft`, `bitsandbytes`, `trl`, `torch`, `torchao`). FED notebooks use inline `!pip install`; JupyterHub uses different Python/packages. The CTSKII examples recommend using a venv and `~/requirements.txt`.

---

## Overview

| Phase | Where | What |
|-------|-------|------|
| 1 | **Google Colab** | Run extraction notebook → download `colab_requirements.txt` |
| 2 | **CTSKII JupyterHub** | Put file in home (`~/colab_requirements.txt`) and either install in-session or create venv |
| 3 | **Notebook** | Select kernel and run FED notebooks |

---

## Step 1: Extract Requirements from Colab

1. Open [extract_colab_requirements.ipynb](./extract_colab_requirements.ipynb) in **Google Colab**.
2. Set runtime to **T4 GPU** if your FED work needs GPU (Runtime → Change runtime type).
3. Run all cells.
4. Download `colab_requirements.txt` (from the download cell or Files sidebar).
5. Keep this file for the next step.

---

## Step 2: Use in CTSKII JupyterHub

CTSKII uses: persistent home directory, venv at `~/venv`, requirements at `~/requirements.txt`. For FED we use a separate venv so it does not conflict with the basic examples setup.

### Option A – Install in Session (Quick Test)

Use this to try the environment without creating a venv.

1. **Upload** `colab_requirements.txt` into your home folder in JupyterHub (e.g. `~/colab_requirements.txt`).
2. In a notebook, run:
   ```python
   !pip install --no-cache-dir -r ~/colab_requirements.txt
   ```
3. **Restart kernel** (Kernel → Restart Kernel).
4. Run your FED notebook with the default kernel.

> Note: Installations may not persist across server restarts depending on your setup. For persistence, use Option B.

### Option B – Use venv (Recommended, matches `/examples`)

Follow the same pattern as `welcome_ctskii.ipynb` but for the Colab-like environment.

**Easiest:** Run [setup_colab_env_ctskii.ipynb](./setup_colab_env_ctskii.ipynb) cell-by-cell. It automates the steps below.

#### Manual steps (or run the notebook)

1. **Put requirements in home:** Upload `colab_requirements.txt` to `~/colab_requirements.txt`.
2. **Create venv:** `python3 -m venv ~/colab_venv`
3. **Install packages:** `~/colab_venv/bin/pip install --upgrade pip ipykernel` then `~/colab_venv/bin/pip install -r ~/colab_requirements.txt`
4. **Register kernel:** `~/colab_venv/bin/python -m ipykernel install --user --name=colab_venv --display-name="Python (Colab-like)"`
5. **Restart server:** File → Hub Control Panel → Stop My Server → wait ~20s → Start Server.
6. **Switch kernel:** Kernel → Change Kernel → **Python (Colab-like)** in your FED notebook.

---

## Step 3: Verify GPU (if applicable)

```python
import torch
print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0))
```

---

## Step 4: Paths and Files

- Put `final_dataset_v2.csv` in the same folder as the notebook (e.g. `FED/DS1000/`). `NOTEBOOK_DIR` falls back to `os.getcwd()`.
- If you use `~/requirements.txt` instead of `~/colab_requirements.txt`, the examples `welcome_ctskii.ipynb` check will use that file. Use a separate venv and `~/colab_requirements.txt` if you want both the basic examples env and the FED env.

---

## Optional: Use Examples Flow (welcome_ctskii.ipynb)

If you prefer the exact flow from `/examples/welcome_ctskii.ipynb`:

1. Save `colab_requirements.txt` as `~/requirements.txt` (overwrites the basic examples requirements).
2. Open `/examples/welcome_ctskii.ipynb` and run it cell-by-cell (Steps 2–5: create `~/venv`, install from `~/requirements.txt`, register kernel).
3. Use kernel **Python (User Venv)** for your FED notebook.

This uses one venv for both basic and FED packages.

---

## CTSKII Conventions (from `/examples`)

| Item | Examples | FED/Colab setup |
|------|----------|-----------------|
| Requirements file | `~/requirements.txt` | `~/colab_requirements.txt` |
| Venv path | `~/venv` | `~/colab_venv` |
| Kernel name | `user-venv` | `colab_venv` |
| Display name | Python (User Venv) | Python (Colab-like) |
| Server restart | Stop → wait 20s → Start | Same |

---

## Summary Checklist

| Step | Action |
|------|--------|
| 1 | Run `extract_colab_requirements.ipynb` in Colab, download `colab_requirements.txt` |
| 2 | Upload `colab_requirements.txt` to JupyterHub home |
| 3 | Option A: `!pip install -r ~/colab_requirements.txt` in first cell, restart kernel |
| 4 | Option B: Run `setup_colab_env_ctskii.ipynb` cell-by-cell (or follow manual steps) |
| 5 | File → Hub Control Panel → Stop → wait → Start (if using Option B) |
| 6 | Kernel → Change Kernel → Python (Colab-like) |
| 7 | Run FED notebook |
