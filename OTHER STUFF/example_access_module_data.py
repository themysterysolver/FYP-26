#!/usr/bin/env python3
"""
Simple example showing how to programmatically access module data.
Demonstrates the input/output for each module.
"""

import ast
import sys
from pathlib import Path

# Add module paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Hallucination detection" / "static" / "AST"))
sys.path.insert(0, str(PROJECT_ROOT / "Hallucination detection" / "static" / "CFG"))
sys.path.insert(0, str(PROJECT_ROOT / "Hallucination detection" / "static" / "LIB_API"))

# Import analysis functions
from ast_analysis import analyze_ast
from cfg_analysis import analyze_cfg
from library_api import analyze_library_api


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def example_1_correct_code():
    """Example 1: Correct code - all modules should pass."""
    print_section("Example 1: Correct Code")
    
    code = """
import pandas as pd
import numpy as np

def process_data(df):
    result = df.mean()
    return result

df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
output = process_data(df)
"""
    
    print("Input Code:")
    print(code)
    print()
    
    # Run each module
    ast_result = analyze_ast(code)
    cfg_result = analyze_cfg(code)
    libapi_result = analyze_library_api(code)
    
    print("AST Result:")
    print(f"  ✓ Parsed: {ast_result['ast_parsed']}")
    print(f"  • Syntax errors: {ast_result['syntax_error']}")
    print(f"  • Structural errors: {ast_result['structural_error']}")
    print()
    
    print("CFG Result:")
    print(f"  ✓ Analyzed: {cfg_result['cfg_analyzed']}")
    print(f"  • Unreachable code: {cfg_result['unreachable_code']}")
    print(f"  • Missing returns: {cfg_result['missing_return']}")
    print()
    
    print("LIB_API Result:")
    print(f"  ✓ Analyzed: {libapi_result['libapi_analyzed']}")
    print(f"  • Total API errors: {libapi_result['total_libapi_errors']}")
    print()


def example_2_syntax_error():
    """Example 2: Syntax error - AST should fail, others skip."""
    print_section("Example 2: Code with Syntax Error")
    
    code = """
import pandas as pd

def broken_function(
    print("Missing closing parenthesis")
"""
    
    print("Input Code:")
    print(code)
    print()
    
    ast_result = analyze_ast(code)
    
    print("AST Result:")
    print(f"  ✗ Parsed: {ast_result['ast_parsed']}")
    print(f"  • Error type: {ast_result['error_type']}")
    print(f"  • Error line: {ast_result['line']}")
    print(f"  • Message: {ast_result['message']}")
    print()
    
    print("Note: CFG analysis would be skipped because AST parsing failed.")
    print()


def example_3_api_error():
    """Example 3: API error - LIB_API should detect issues."""
    print_section("Example 3: Code with API Error")
    
    code = """
import pandas as pd
import numpy as np

# Using non-existent function
df = pd.DataFrame({'A': [1, 2, 3]})
result = df.non_existent_method()

# Using wrong attribute
arr = np.array([1, 2, 3])
val = arr.wrong_attribute
"""
    
    print("Input Code:")
    print(code)
    print()
    
    ast_result = analyze_ast(code)
    libapi_result = analyze_library_api(code)
    
    print("AST Result:")
    print(f"  ✓ Parsed: {ast_result['ast_parsed']} (syntax is valid)")
    print()
    
    print("LIB_API Result:")
    print(f"  ✓ Analyzed: {libapi_result['libapi_analyzed']}")
    print(f"  • Total API errors: {libapi_result['total_libapi_errors']}")
    print(f"  • Attribute errors: {libapi_result['attribute_error']}")
    print(f"  • Details: {libapi_result['libapi_details']}")
    print()


def example_4_control_flow_issues():
    """Example 4: Control flow issues - CFG should detect problems."""
    print_section("Example 4: Code with Control Flow Issues")
    
    code = """
def function_with_issues():
    x = 10
    return x
    print("This code is unreachable!")
    y = 20

def function_missing_return(a, b):
    if a > b:
        return a
    # Missing return for else case
"""
    
    print("Input Code:")
    print(code)
    print()
    
    ast_result = analyze_ast(code)
    cfg_result = analyze_cfg(code)
    
    print("AST Result:")
    print(f"  ✓ Parsed: {ast_result['ast_parsed']}")
    print()
    
    print("CFG Result:")
    print(f"  ✓ Analyzed: {cfg_result['cfg_analyzed']}")
    print(f"  • Unreachable code: {cfg_result['unreachable_code']}")
    print(f"  • Missing returns: {cfg_result['missing_return']}")
    print(f"  • Details: {cfg_result['cfg_details']}")
    print()


def example_5_multiple_errors():
    """Example 5: Multiple types of errors."""
    print_section("Example 5: Code with Multiple Error Types")
    
    code = """
import pandas as pd

def buggy_function():
    df = pd.DataFrame({'A': [1, 2, 3]})
    
    # API error: non-existent method
    result = df.non_existent_method()
    
    return result
    
    # Control flow issue: unreachable code
    print("This will never execute")
"""
    
    print("Input Code:")
    print(code)
    print()
    
    ast_result = analyze_ast(code)
    cfg_result = analyze_cfg(code)
    libapi_result = analyze_library_api(code)
    
    print("AST Result:")
    print(f"  ✓ Parsed: {ast_result['ast_parsed']}")
    print()
    
    print("CFG Result:")
    print(f"  ✓ Analyzed: {cfg_result['cfg_analyzed']}")
    print(f"  • Unreachable code blocks: {cfg_result['unreachable_code']}")
    print()
    
    print("LIB_API Result:")
    print(f"  ✓ Analyzed: {libapi_result['libapi_analyzed']}")
    print(f"  • API errors: {libapi_result['total_libapi_errors']}")
    print()
    
    print("Summary: Code has both control flow and API issues!")
    print()


def main():
    """Run all examples."""
    print("=" * 80)
    print("  Module Input/Output Examples")
    print("  Demonstrating AST, CFG, and LIB_API Analysis")
    print("=" * 80)
    
    try:
        example_1_correct_code()
        example_2_syntax_error()
        example_3_api_error()
        example_4_control_flow_issues()
        example_5_multiple_errors()
        
        print_section("Summary")
        print("Key Takeaways:")
        print()
        print("1. INPUT: All modules receive the same input - Python code as a string")
        print()
        print("2. OUTPUTS:")
        print("   • AST: Detects syntax/structural errors")
        print("   • CFG: Detects unreachable code and missing returns")
        print("   • LIB_API: Detects invalid library usage")
        print()
        print("3. WORKFLOW:")
        print("   • Each module analyzes the code independently")
        print("   • CFG requires AST to succeed first")
        print("   • Results are stored separately and later merged")
        print()
        print("4. FILE LOCATIONS:")
        print("   • Outputs saved to: Hallucination detection/static/{AST,CFG,LIB_API}/")
        print("   • Format: JSONL (one JSON per line) and CSV (summary)")
        print()
        print("=" * 80)
        
    except ImportError as e:
        print(f"\n❌ Error: Could not import analysis modules.")
        print(f"   {e}")
        print(f"\n   Make sure you're running this from the project root:")
        print(f"   python example_access_module_data.py")


if __name__ == "__main__":
    main()
