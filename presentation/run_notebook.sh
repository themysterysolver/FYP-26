#!/bin/bash
# Quick start script to run the APR presentation notebook

echo "Starting APR Presentation Notebook..."
echo "======================================"

# Navigate to presentation directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠ Virtual environment not found!"
    echo "Running setup first..."
    ./setup_environment.sh
    echo ""
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Check if jupyter is installed
if ! command -v jupyter &> /dev/null; then
    echo "✗ Jupyter not found in venv. Installing requirements..."
    pip install -r requirements.txt
fi

# Start Jupyter notebook
echo "✓ Starting Jupyter Notebook..."
echo ""
echo "The notebook will open in your browser."
echo "Press Ctrl+C in this terminal to stop the server."
echo ""

jupyter notebook apr_pipeline_demo.ipynb
