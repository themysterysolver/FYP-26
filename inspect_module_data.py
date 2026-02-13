#!/usr/bin/env python3
"""
Script to inspect data flow through AST, CFG, LIB_API, and Dynamic modules.
Shows inputs and outputs for a specific task_id.

Usage:
    python inspect_module_data.py --task-id DS0001 --dataset DS1000
    python inspect_module_data.py --task-id HumanEval/0 --dataset HumanEval
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent
GENERATION_DIR = PROJECT_ROOT / "Code generation" / "Qwen"
STATIC_DIR = PROJECT_ROOT / "Hallucination detection" / "static"
DYNAMIC_DIR = PROJECT_ROOT / "Hallucination detection" / "dynamic"


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def get_generated_code(dataset: str, task_id: str) -> Optional[str]:
    """Get the generated code for a specific task."""
    dataset_files = {
        "DS1000": GENERATION_DIR / "ds1k_gen.csv",
        "HumanEval": GENERATION_DIR / "humaneval_gen.csv",
        "MBPP": GENERATION_DIR / "mbpp_gen.csv",
    }
    
    file_path = dataset_files.get(dataset)
    if not file_path or not file_path.exists():
        return None
    
    df = pd.read_csv(file_path)
    row = df[df['task_id'] == task_id]
    
    if row.empty:
        return None
    
    code_column = "full_code" if dataset == "DS1000" else "GENERATED_CODE"
    return row.iloc[0][code_column]


def get_ast_result(dataset: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Get AST analysis result for a specific task."""
    ast_summary = STATIC_DIR / "AST" / "ast_summary.csv"
    if not ast_summary.exists():
        return None
    
    df = pd.read_csv(ast_summary)
    row = df[(df['dataset'] == dataset) & (df['task_id'] == task_id)]
    
    if row.empty:
        return None
    
    return row.iloc[0].to_dict()


def get_cfg_result(dataset: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Get CFG analysis result for a specific task."""
    cfg_summary = STATIC_DIR / "CFG" / "cfg_summary.csv"
    if not cfg_summary.exists():
        return None
    
    df = pd.read_csv(cfg_summary)
    row = df[(df['dataset'] == dataset) & (df['task_id'] == task_id)]
    
    if row.empty:
        return None
    
    return row.iloc[0].to_dict()


def get_libapi_result(dataset: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Get LIB_API analysis result for a specific task."""
    libapi_summary = STATIC_DIR / "LIB_API" / "libapi_summary.csv"
    if not libapi_summary.exists():
        return None
    
    df = pd.read_csv(libapi_summary)
    row = df[(df['dataset'] == dataset) & (df['task_id'] == task_id)]
    
    if row.empty:
        return None
    
    return row.iloc[0].to_dict()


def get_dynamic_result(dataset: str, task_id: str) -> Optional[Dict[str, Any]]:
    """Get dynamic analysis result for a specific task."""
    dataset_files = {
        "DS1000": DYNAMIC_DIR / "dynamic_ds1000.jsonl",
        "HumanEval": DYNAMIC_DIR / "dynamic_humaneval.jsonl",
        "MBPP": DYNAMIC_DIR / "dynamic_mbpp.jsonl",
    }
    
    file_path = dataset_files.get(dataset)
    if not file_path or not file_path.exists():
        return None
    
    with open(file_path, 'r') as f:
        for line in f:
            record = json.loads(line)
            if record.get('task_id') == task_id:
                return record
    
    return None


def display_result(module_name: str, result: Optional[Dict[str, Any]]):
    """Display a module's result in a formatted way."""
    print_section(f"{module_name} Analysis Result")
    
    if result is None:
        print(f"❌ No result found for {module_name}")
        return
    
    print(f"✓ {module_name} analysis completed")
    print("\nKey Metrics:")
    
    if module_name == "AST":
        print(f"  • AST Parsed:         {result.get('ast_parsed', 'N/A')}")
        print(f"  • Syntax Errors:      {result.get('syntax_error', 0)}")
        print(f"  • Indentation Errors: {result.get('indentation_error', 0)}")
        print(f"  • Structural Errors:  {result.get('structural_error', 0)}")
        if result.get('error_type'):
            print(f"  • Error Type:         {result.get('error_type')}")
            print(f"  • Error Line:         {result.get('line')}")
            print(f"  • Error Message:      {result.get('message')}")
    
    elif module_name == "CFG":
        print(f"  • CFG Analyzed:       {result.get('cfg_analyzed', 'N/A')}")
        print(f"  • Unreachable Code:   {result.get('unreachable_code', 0)} instances")
        print(f"  • Missing Returns:    {result.get('missing_return', 0)} functions")
    
    elif module_name == "LIB_API":
        print(f"  • Analysis Status:    {result.get('libapi_analyzed', 'N/A')}")
        print(f"  • Module Not Found:   {result.get('module_not_found', 0)} errors")
        print(f"  • Attribute Errors:   {result.get('attribute_error', 0)} errors")
        print(f"  • Name Errors:        {result.get('name_error', 0)} errors")
        print(f"  • Type Errors:        {result.get('type_error', 0)} errors")
        print(f"  • Total API Errors:   {result.get('total_libapi_errors', 0)}")
    
    elif module_name == "Dynamic":
        print(f"  • Execution Status:   {result.get('status', 'N/A')}")
        print(f"  • Error Type:         {result.get('error_type', 'N/A')}")
        print(f"  • Hallucination Type: {result.get('hallucination_subtype', 'N/A')}")
    
    print("\nFull Result:")
    print(json.dumps(result, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(
        description="Inspect data flow through module pipeline"
    )
    parser.add_argument(
        "--task-id",
        required=True,
        help="Task ID to inspect (e.g., DS0001, HumanEval/0)"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["DS1000", "HumanEval", "MBPP"],
        help="Dataset name"
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Show the generated code"
    )
    
    args = parser.parse_args()
    
    print_section(f"Module Data Flow Inspection: {args.dataset} / {args.task_id}")
    
    # Get generated code (input to all modules)
    code = get_generated_code(args.dataset, args.task_id)
    
    if code is None:
        print(f"❌ Could not find task {args.task_id} in {args.dataset}")
        return
    
    print(f"✓ Found task {args.task_id} in {args.dataset}")
    print(f"  Code length: {len(code)} characters")
    print(f"  Code lines:  {len(code.splitlines())} lines")
    
    if args.show_code:
        print_section("Generated Code (Input to all modules)")
        print(code)
    
    # Get results from each module
    ast_result = get_ast_result(args.dataset, args.task_id)
    cfg_result = get_cfg_result(args.dataset, args.task_id)
    libapi_result = get_libapi_result(args.dataset, args.task_id)
    dynamic_result = get_dynamic_result(args.dataset, args.task_id)
    
    # Display results
    display_result("AST", ast_result)
    display_result("CFG", cfg_result)
    display_result("LIB_API", libapi_result)
    display_result("Dynamic", dynamic_result)
    
    # Summary
    print_section("Module Pipeline Summary")
    print("Data Flow:")
    print("  1. Generated Code (input)")
    print("     ↓")
    print(f"  2. AST Analysis → {'✓ Success' if ast_result and ast_result.get('ast_parsed') else '✗ Failed'}")
    print("     ↓")
    print(f"  3. CFG Analysis → {'✓ Analyzed' if cfg_result and cfg_result.get('cfg_analyzed') else '✗ Skipped/Failed'}")
    print("     ↓")
    print(f"  4. LIB_API Analysis → {'✓ Analyzed' if libapi_result and libapi_result.get('libapi_analyzed') else '✗ Failed'}")
    print("     ↓")
    print(f"  5. Dynamic Execution → {dynamic_result.get('status', 'N/A') if dynamic_result else '✗ Not found'}")
    
    print("\n" + "=" * 80)
    print("\nFile Locations:")
    print(f"  • Input data:  {GENERATION_DIR}")
    print(f"  • AST output:  {STATIC_DIR / 'AST' / 'ast_summary.csv'}")
    print(f"  • CFG output:  {STATIC_DIR / 'CFG' / 'cfg_summary.csv'}")
    print(f"  • API output:  {STATIC_DIR / 'LIB_API' / 'libapi_summary.csv'}")
    print(f"  • Dynamic:     {DYNAMIC_DIR / f'dynamic_{args.dataset.lower()}.jsonl'}")
    print("=" * 80)


if __name__ == "__main__":
    main()
