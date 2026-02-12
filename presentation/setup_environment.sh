#!/bin/bash
# Setup script for APR presentation notebook

echo "Setting up Python virtual environment for APR presentation..."
echo "================================================================"

# Navigate to presentation directory
cd "$(dirname "$0")"

# Create virtual environment
echo -e "\n1. Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo -e "\n2. Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo -e "\n3. Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo -e "\n4. Installing required packages..."
pip install -r requirements.txt

echo -e "\n================================================================"
echo "✓ Setup complete!"
echo ""
echo "To use the notebook:"
echo "  1. Activate the virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Start Jupyter:"
echo "     jupyter notebook apr_pipeline_demo.ipynb"
echo ""
echo "  3. When done, deactivate:"
echo "     deactivate"
echo "================================================================"
