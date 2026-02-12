# Installation Guide

## Problem: Missing Dependencies

If you're seeing `ModuleNotFoundError: No module named 'plotly'`, you need to install the required Python packages.

## Solution: Virtual Environment (Recommended)

Your system uses an externally-managed Python environment (macOS with Homebrew), so we'll use a virtual environment.

### Option 1: Automatic Setup (Easiest)

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation
./setup_environment.sh
```

This script will:
1. Create a virtual environment
2. Install all required packages
3. Show you how to activate it

### Option 2: Manual Setup

```bash
# Navigate to presentation folder
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

## Running the Notebook

After setup:

```bash
# 1. Activate virtual environment (if not already active)
source venv/bin/activate

# 2. Start Jupyter
jupyter notebook apr_pipeline_demo.ipynb

# 3. When done, deactivate
deactivate
```

## Required Packages

The notebook needs:
- **jupyter** - Notebook environment
- **pandas, numpy** - Data manipulation
- **plotly** - Interactive visualizations (the one that's missing!)
- **matplotlib, seaborn** - Additional plots
- **pygments** - Code highlighting

All are listed in `requirements.txt`.

## Alternative: System-Wide Install (Not Recommended)

If you really want to install system-wide:

```bash
# Use --break-system-packages flag (not recommended)
pip3 install --break-system-packages plotly matplotlib seaborn
```

⚠️ **Warning**: This can interfere with your system Python. Virtual environment is safer!

## Quick Test

After installation, test in Python:

```bash
source venv/bin/activate
python3 -c "import plotly; print('✓ Plotly installed:', plotly.__version__)"
```

You should see: `✓ Plotly installed: 5.x.x`

## Troubleshooting

### "venv/bin/activate: No such file"
- Make sure you ran `python3 -m venv venv` first
- Check you're in the `/presentation` directory

### "jupyter: command not found"
- Make sure virtual environment is activated: `source venv/bin/activate`
- If still missing: `pip install jupyter`

### Still getting ModuleNotFoundError
- Confirm you're using the venv Python: `which python`
- Should show: `.../presentation/venv/bin/python`
- If not, deactivate and reactivate: `deactivate && source venv/bin/activate`

## VS Code Users

If using VS Code to run the notebook:

1. Open Command Palette (Cmd+Shift+P)
2. Search: "Python: Select Interpreter"
3. Choose: `./venv/bin/python`
4. Reload notebook

VS Code will then use the virtual environment with all packages.
