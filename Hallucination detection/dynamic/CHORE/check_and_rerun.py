#!/usr/bin/env python3
"""
Check which packages are installed and re-run dynamic execution if new packages are available.
"""

import sys
import subprocess

print("=" * 80)
print("PACKAGE AVAILABILITY CHECK")
print("=" * 80)

# Check packages
packages_to_check = {
    'scipy': 'Scientific computing',
    'sklearn': 'Machine learning (scikit-learn)',
    'seaborn': 'Statistical visualization',
    'sympy': 'Symbolic mathematics',
    'yaml': 'YAML parser',
    'xgboost': 'Gradient boosting',
    'torch': 'PyTorch deep learning',
    'tensorflow': 'TensorFlow deep learning'
}

installed = []
missing = []

print("\n📦 Checking packages...\n")
for pkg, description in packages_to_check.items():
    try:
        if pkg == 'sklearn':
            import sklearn
        else:
            __import__(pkg)
        installed.append(pkg)
        print(f"  ✓ {pkg:15s} - {description}")
    except ImportError:
        missing.append(pkg)
        print(f"  ✗ {pkg:15s} - {description} (NOT INSTALLED)")

print("\n" + "=" * 80)
print(f"SUMMARY: {len(installed)}/{len(packages_to_check)} packages installed")
print("=" * 80)

if len(installed) >= 2:  # At least some new packages
    print("\n✅ New packages detected!")
    print("\n📊 Expected improvements:")
    
    # Estimate based on the module errors we found
    improvements = {
        'scipy': 127,
        'sklearn': 106,
        'torch': 70,
        'seaborn': 53,
        'tensorflow': 47,
        'sympy': 4,
        'xgboost': 2,
        'yaml': 1
    }
    
    total_improvement = sum(improvements.get(pkg, 0) for pkg in installed if pkg in improvements)
    
    print(f"   • Could resolve up to {total_improvement} ModuleNotFoundError entries")
    print(f"   • Current pass rate: 34.6%")
    print(f"   • Potential new pass rate: ~{34.6 + (total_improvement/1491*100):.1f}%")
    
    print("\n🔄 Ready to re-run dynamic execution?")
    response = input("   Run dynamic_execution.py now? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\n" + "=" * 80)
        print("RUNNING DYNAMIC EXECUTION")
        print("=" * 80)
        print("\nThis will take several minutes...\n")
        
        try:
            result = subprocess.run(
                ['python3', 'dynamic_execution.py'],
                cwd='/Users/abhinavh.parthiban/Documents/FYP-26/Hallucination detection/dynamic',
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print("\n" + "=" * 80)
                print("✅ Dynamic execution complete!")
                print("=" * 80)
                print("\n📝 Next step: Re-run integration")
                print("   cd .. && python3 integrate_fault_data.py")
            else:
                print("\n❌ Dynamic execution failed. Check output above.")
        except Exception as e:
            print(f"\n❌ Error running dynamic execution: {e}")
    else:
        print("\n📝 To run manually:")
        print("   python3 dynamic_execution.py")
        print("   python3 ../integrate_fault_data.py")
else:
    print("\n⚠️  No new packages installed yet.")
    print("\n📝 To install packages, run:")
    print("   ./install_packages.sh")
    print("\n   OR manually:")
    print("   pip install scipy scikit-learn seaborn sympy pyyaml xgboost torch")

print("\n" + "=" * 80)
