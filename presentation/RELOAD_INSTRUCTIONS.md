# How to Reload the Fixed Notebook

## The Problem

Your Jupyter session is using a cached/old version of the notebook. The fixes have been applied to the file, but Jupyter hasn't reloaded it yet.

## Solution: Reload the Notebook

### Method 1: Close and Reopen (Recommended)

1. **Save any work** (if you added anything)
2. **Close the notebook tab** in your browser
3. **Stop Jupyter** in the terminal (Ctrl+C twice)
4. **Restart Jupyter**:
   ```bash
   cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation
   ./run_notebook.sh
   ```
5. **Open the notebook** again
6. **Run all cells**: Kernel → Restart & Run All

### Method 2: File → Revert to Checkpoint

1. In Jupyter: **File** → **Revert to Checkpoint** → Choose latest
2. Confirm the revert
3. **Kernel** → **Restart & Run All**

### Method 3: Force Reload

1. **Close the notebook tab**
2. In the Jupyter file browser, click the notebook again to open fresh
3. **Kernel** → **Restart & Run All**

## Verify the Fix

After reloading, run this in a new cell to test:

```python
# Test that function is defined
import inspect
print("Checking function definition...")
print(f"generate_statistics_dashboard defined: {'generate_statistics_dashboard' in dir()}")

# If it exists, show its signature
if 'generate_statistics_dashboard' in dir():
    print(f"Function signature: {inspect.signature(generate_statistics_dashboard)}")
    print("✓ Function is properly defined!")
else:
    print("✗ Function still not defined - try Method 1 (close and reopen)")
```

## What Was Fixed

The notebook file had improperly formatted cell sources (missing newlines), which caused a Python syntax error that prevented the `generate_statistics_dashboard()` function from being defined. This has been fixed in the file, but Jupyter needs to reload it.

## Alternative: Use Fresh Terminal

If the above doesn't work:

```bash
# Kill any running Jupyter servers
pkill -f jupyter

# Start fresh
cd /Users/abhinavh.parthiban/Documents/FYP-26/presentation
source venv/bin/activate
jupyter notebook apr_pipeline_demo.ipynb
```

## Expected Behavior After Reload

When you run **Kernel → Restart & Run All**:

1. Cell 1-5: Setup and imports (no errors)
2. Cell 6: Defines `generate_statistics_dashboard()` (no output, no error)
3. Cell 11: Calls `stats = generate_statistics_dashboard()` (works!)
4. All other cells: Execute normally

You should see:
```
✓ Statistics dashboard generated
  - Total examples: 1491
  - Datasets: ['DS-1000', 'HumanEval', 'MBPP']
```

## Still Having Issues?

If you still get `NameError` after reloading:

1. Check the kernel is using the venv:
   - Top right corner should show "Python 3 (venv)" or similar
   - If not: Kernel → Change Kernel → Select venv Python

2. Run cells in order:
   - Don't skip cells
   - Run Cell 1, then 2, then 3, etc.
   - Don't jump to Cell 11 without running Cell 6 first!

3. Check for errors in Cell 6:
   - If Cell 6 has a red error output, the function wasn't defined
   - Look for SyntaxError or IndentationError
   - If you see one, let me know and I'll fix it
