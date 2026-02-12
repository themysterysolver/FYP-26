#!/bin/bash
# Verify the notebook works by executing it programmatically

echo "=========================================="
echo "Verifying Notebook Execution"
echo "=========================================="
echo ""

cd "$(dirname "$0")"
source venv/bin/activate

echo "Executing notebook..."
jupyter nbconvert --to notebook --execute \
    --ExecutePreprocessor.timeout=300 \
    --output /tmp/test_notebook.ipynb \
    apr_pipeline_demo.ipynb 2>&1 | grep -E "(Error|✓|✗|Traceback)" || echo "No errors detected"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "=========================================="
    echo "✓ NOTEBOOK EXECUTES SUCCESSFULLY"
    echo "=========================================="
    echo ""
    echo "The notebook works! You can now:"
    echo "1. Close your current Jupyter session (Ctrl+C)"
    echo "2. Start fresh: ./run_notebook.sh"
    echo "3. Open the notebook and run all cells"
    exit 0
else
    echo "=========================================="
    echo "✗ NOTEBOOK HAS EXECUTION ERRORS"
    echo "=========================================="
    echo ""
    echo "Check the error messages above."
    echo "Common issues:"
    echo "- Missing data files"
    echo "- Syntax errors in cells"
    echo "- Wrong Python environment"
    exit 1
fi
