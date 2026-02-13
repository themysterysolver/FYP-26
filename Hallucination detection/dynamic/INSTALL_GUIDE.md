# Package Installation Guide

## Current Situation

- **Python 3.14.3** on Apple Silicon (ARM64)
- **TensorFlow**: Not compatible with Python 3.14 yet ❌
- **Other packages**: Compatible and ready to install ✅

## Installation Instructions

### Step 1: Install Compatible Packages

In your terminal (where `.venv` is activated), run:

```bash
# Install core packages (these will work)
pip install scipy scikit-learn seaborn sympy pyyaml xgboost torch
```

**Note**: Skip TensorFlow - it doesn't support Python 3.14 yet. This means:
- ✅ Can resolve: ~363 errors (scipy, sklearn, torch, seaborn, etc.)
- ❌ Cannot resolve: 47 TensorFlow errors (will remain until TF updates)

### Step 2: Verify Installation

```bash
cd "Hallucination detection/dynamic"
python3 check_and_rerun.py
```

This script will:
- ✓ Check which packages are installed
- ✓ Show expected improvements
- ✓ Offer to re-run dynamic execution

### Step 3: Re-run Dynamic Execution

Option A - **Automatic** (if you used check_and_rerun.py):
- Just answer 'y' when prompted

Option B - **Manual**:
```bash
cd "Hallucination detection/dynamic"
python3 dynamic_execution.py
```

This will take **several minutes** to complete.

### Step 4: Re-integrate Results

After dynamic execution completes:

```bash
cd "Hallucination detection"
python3 integrate_fault_data.py
```

## Expected Results

### Before Package Installation
- Total entries: 1,491
- Module errors: 410 (27.5%)
- Pass rate: 34.6%

### After Package Installation (without TensorFlow)
- Module errors: ~47 (TensorFlow only)
- Resolved: ~363 errors
- Expected pass rate: **~45-55%** (depends on if resolved tests pass or reveal other issues)

### By Dataset

| Dataset | Current Errors | Resolvable | Remaining |
|---------|----------------|------------|-----------|
| DS1000 | 406 | ~359 | ~47 (TF only) |
| HumanEval | 3 | 3 | 0 |
| MBPP | 1 | 1 | 0 |

## Troubleshooting

### TensorFlow Installation Error
```
ERROR: No matching distribution found for tensorflow
```
**Solution**: Skip TensorFlow for now. Python 3.14 support will come in a future TF release.

### PyTorch Installation Slow
PyTorch is a large package (~2GB). Installation may take 5-10 minutes on slower connections.

### Permission Errors
Make sure you're in your virtual environment (`.venv` should show in terminal prompt).

## Alternative: Use Python 3.11 or 3.12

If you need TensorFlow support, you could:

1. Create a new virtual environment with Python 3.11:
```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install scipy scikit-learn seaborn sympy pyyaml xgboost torch tensorflow
```

2. Run the dynamic execution with that environment

**Note**: This is optional - you'll get 88% of the benefit with just the compatible packages.

## Quick Reference Commands

```bash
# Install packages (in .venv)
pip install scipy scikit-learn seaborn sympy pyyaml xgboost torch

# Check installation
cd "Hallucination detection/dynamic"
python3 check_and_rerun.py

# Manual re-run
python3 dynamic_execution.py
cd ..
python3 integrate_fault_data.py
```

## Files Created

- `install_packages.sh` - Automated installation script
- `check_and_rerun.py` - Verify packages and re-run execution
- `INSTALL_GUIDE.md` - This file
- `MODULE_ERRORS_ANALYSIS.md` - Detailed error analysis
- `MODULE_FIX_OPTIONS.md` - Resolution options

---

**Ready to proceed?** Run the install command in your terminal, then use `check_and_rerun.py` to verify and re-run!
