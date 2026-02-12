#!/bin/bash
# Run the complete DS-KG integration demo and show results

set -e  # Exit on error

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║    DS-KG Integration Demo - Test Runner               ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "✗ Error: python3 not found"
    exit 1
fi

echo "Running demo script..."
echo ""

# Run the demo
python3 examples/demo_kg_repair.py

# Check exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  ✓ DEMO COMPLETED SUCCESSFULLY!                       ║"
    echo "║  ✓ Broken code was fixed using KG integration         ║"
    echo "║  ✓ All validation tests passed                        ║"
    echo "╚════════════════════════════════════════════════════════╝"
    exit 0
else
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  ✗ DEMO FAILED                                         ║"
    echo "║  Check output above for errors                         ║"
    echo "╚════════════════════════════════════════════════════════╝"
    exit 1
fi
