#!/usr/bin/env python3
"""
Test script to verify all notebook fixes are working.
"""
import sys
import pandas as pd
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    try:
        import plotly.graph_objects as go
        import matplotlib.pyplot as plt
        import seaborn as sns
        import numpy as np
        print("  ✓ All visualization packages imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_data_loading():
    """Test that data files can be loaded."""
    print("\nTesting data loading...")
    PROJECT_ROOT = Path('/Users/abhinavh.parthiban/Documents/FYP-26')
    
    files_to_check = [
        PROJECT_ROOT / 'APR' / 'input' / 'apr_input.jsonl',
        PROJECT_ROOT / 'Hallucination detection' / 'static' / 'AST' / 'ast_summary.csv',
        PROJECT_ROOT / 'Hallucination detection' / 'static' / 'CFG' / 'cfg_summary.csv',
        PROJECT_ROOT / 'Hallucination detection' / 'static' / 'LIB_API' / 'libapi_summary.csv',
        PROJECT_ROOT / 'Hallucination detection' / 'dynamic' / 'dynamic_summary.csv',
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if file_path.exists():
            print(f"  ✓ {file_path.name}")
        else:
            print(f"  ✗ {file_path.name} not found")
            all_exist = False
    
    return all_exist

def test_column_names():
    """Test that CSV files have expected column names."""
    print("\nTesting column names...")
    PROJECT_ROOT = Path('/Users/abhinavh.parthiban/Documents/FYP-26')
    
    # Test dynamic CSV
    dynamic_path = PROJECT_ROOT / 'Hallucination detection' / 'dynamic' / 'dynamic_summary.csv'
    if dynamic_path.exists():
        df = pd.read_csv(dynamic_path, nrows=1)
        if 'hallucination_subtype' in df.columns:
            print("  ✓ dynamic_summary.csv has 'hallucination_subtype' column")
        else:
            print(f"  ✗ dynamic_summary.csv missing 'hallucination_subtype' (has: {df.columns.tolist()})")
            return False
        
        if 'valid' in df.columns:
            print("  ✓ dynamic_summary.csv has 'valid' column")
        else:
            print("  ⚠ dynamic_summary.csv missing 'valid' column (optional)")
    
    # Test AST CSV
    ast_path = PROJECT_ROOT / 'Hallucination detection' / 'static' / 'AST' / 'ast_summary.csv'
    if ast_path.exists():
        df = pd.read_csv(ast_path, nrows=1)
        if 'syntax_error' in df.columns:
            print("  ✓ ast_summary.csv has 'syntax_error' column")
        else:
            print(f"  ✗ ast_summary.csv missing 'syntax_error' (has: {df.columns.tolist()})")
            return False
    
    return True

def test_valid_column_handling():
    """Test that valid column is handled correctly."""
    print("\nTesting valid column handling...")
    PROJECT_ROOT = Path('/Users/abhinavh.parthiban/Documents/FYP-26')
    dynamic_path = PROJECT_ROOT / 'Hallucination detection' / 'dynamic' / 'dynamic_summary.csv'
    
    if dynamic_path.exists():
        df = pd.read_csv(dynamic_path, nrows=100)
        if 'valid' in df.columns:
            try:
                # Test the fixed approach
                invalid_count = int((df['valid'] == False).sum())
                print(f"  ✓ Valid column handled correctly (found {invalid_count} invalid entries)")
                return True
            except Exception as e:
                print(f"  ✗ Error handling valid column: {e}")
                return False
    else:
        print("  ⚠ dynamic_summary.csv not found (skipping test)")
        return True

def main():
    """Run all tests."""
    print("="*60)
    print("APR Notebook Fixes - Verification Tests")
    print("="*60)
    
    results = []
    
    results.append(("Package Imports", test_imports()))
    results.append(("Data Loading", test_data_loading()))
    results.append(("Column Names", test_column_names()))
    results.append(("Valid Column", test_valid_column_handling()))
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:<20} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✅ All tests passed! Notebook is ready to use.")
        return 0
    else:
        print("\n⚠ Some tests failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
