# Quick Start Guide

## ✅ Installation Complete!

All required packages (including plotly) are now installed in a virtual environment.

## Running the Notebook

### Method 1: One-Command Start (Easiest)

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation
./run_notebook.sh
```

This script will:
- Activate the virtual environment
- Start Jupyter Notebook
- Open the presentation in your browser

### Method 2: Manual Start

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation

# Activate virtual environment
source venv/bin/activate

# Start Jupyter
jupyter notebook apr_pipeline_demo.ipynb

# When done, stop with Ctrl+C, then:
deactivate
```

## What Just Happened?

✅ Created a Python virtual environment in `venv/`  
✅ Installed all required packages:
- **plotly** (6.5.2) - Interactive visualizations ← This was missing!
- **matplotlib** (3.10.8) - Additional plots
- **seaborn** (0.13.2) - Statistical visualizations
- **pandas** (3.0.0) - Data manipulation
- **numpy** (2.4.2) - Numerical computing
- **jupyter** (1.1.1) - Notebook environment
- **pygments** (2.19.2) - Code highlighting

## Verifying Installation

Test that plotly is working:

```bash
source venv/bin/activate
python3 -c "import plotly; print('✓ Plotly version:', plotly.__version__)"
```

Expected output: `✓ Plotly version: 6.5.2`

## VS Code Users

If you're using VS Code to run the notebook:

1. Open the notebook: `apr_pipeline_demo.ipynb`
2. Click "Select Kernel" (top right)
3. Choose: "Python 3.14.0 64-bit ('venv': venv)"
4. Run cells!

The path should be: `.../presentation/venv/bin/python`

## Jupyter Lab (Alternative)

If you prefer Jupyter Lab instead of Notebook:

```bash
source venv/bin/activate
jupyter lab apr_pipeline_demo.ipynb
```

## Troubleshooting

### "source: command not found"
- You're in a different shell. Try: `. venv/bin/activate`

### "jupyter: command not found" after activation
- Install it: `pip install jupyter`
- Or re-run setup: `./setup_environment.sh`

### "ModuleNotFoundError" still appearing
- Make sure virtual environment is active
- Check prompt shows `(venv)` at the beginning
- Verify: `which python` → should show `.../venv/bin/python`

### Browser doesn't open automatically
- Look for the URL in the terminal output
- Copy and paste into your browser
- Format: `http://localhost:8888/?token=...`

## Next Steps

1. **Run the notebook** - Execute cells to see visualizations
2. **Review Section 8** - Efficiency comparison (key differentiator)
3. **Export if needed** - See README.md for HTML/PDF export
4. **Customize** - Modify examples for your presentation

## Files Created

```
presentation/
├── apr_pipeline_demo.ipynb     ← The notebook
├── venv/                        ← Virtual environment (packages here)
├── setup_environment.sh         ← Setup script
├── run_notebook.sh              ← Quick start script (use this!)
├── requirements.txt             ← Package list
├── INSTALL.md                   ← Detailed install guide
├── QUICKSTART.md                ← This file
└── README.md                    ← Full documentation
```

---

**Ready to present!** 🎓

The notebook is now fully functional with all required packages installed.
