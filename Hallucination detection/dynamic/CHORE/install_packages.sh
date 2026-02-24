#!/bin/bash
# Install DS1000 dependencies for dynamic execution
# Run this from your activated virtual environment

echo "======================================================================"
echo "Installing DS1000 Dependencies"
echo "======================================================================"

echo ""
echo "📦 Installing core scientific computing packages..."
pip install scipy scikit-learn

echo ""
echo "📊 Installing visualization package..."
pip install seaborn

echo ""
echo "🔢 Installing symbolic math and utilities..."
pip install sympy pyyaml xgboost

echo ""
echo "🔥 Installing PyTorch (may take a while)..."
pip install torch

echo ""
echo "⚠️  Skipping TensorFlow (not compatible with Python 3.14 yet)"
echo "   TensorFlow will be available when they release Python 3.14 support"

echo ""
echo "======================================================================"
echo "✅ Installation Complete!"
echo "======================================================================"

echo ""
echo "Checking installed packages..."
python3 << 'EOF'
import sys
print(f"Python version: {sys.version}")
print("\nInstalled DS1000 packages:")

packages = ['scipy', 'sklearn', 'seaborn', 'sympy', 'yaml', 'xgboost', 'torch', 'tensorflow']
for pkg in packages:
    try:
        if pkg == 'yaml':
            __import__(pkg)
        elif pkg == 'sklearn':
            import sklearn
        else:
            __import__(pkg)
        print(f"  ✓ {pkg}")
    except ImportError:
        print(f"  ✗ {pkg} (not installed)")
EOF

echo ""
echo "📝 Next steps:"
echo "   1. Run: cd 'Hallucination detection/dynamic'"
echo "   2. Run: python3 dynamic_execution.py"
echo "   3. Run: cd .. && python3 integrate_fault_data.py"
echo ""
