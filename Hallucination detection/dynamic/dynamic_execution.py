#!/usr/bin/env python3
"""
Dynamic Test Execution Module
Executes generated code against test cases from DS1000, HumanEval, and MBPP datasets.
Captures pass/fail status and detailed error information.
"""

import os
import sys
import ast
import traceback
import pandas as pd
import signal
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
GENERATION_DIR = PROJECT_ROOT / "Code generation" / "Qwen"
DATASET_DIR = PROJECT_ROOT / "Dataset used"
OUTPUT_DIR = Path(__file__).parent

# Dataset configurations
DATASETS = {
    "DS1000": {
        "gen_path": GENERATION_DIR / "ds1k_gen.csv",
        "test_path": DATASET_DIR / "ds1000.csv",
        "code_column": "full_code",
        "task_id_column": "task_id"
    },
    "HumanEval": {
        "gen_path": GENERATION_DIR / "humaneval_gen.csv",
        "test_path": DATASET_DIR / "humaneval.csv",
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id"
    },
    "MBPP": {
        "gen_path": GENERATION_DIR / "mbpp_gen.csv",
        "test_path": DATASET_DIR / "mbpp.csv",
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id"
    }
}

OUTPUT_CSV = OUTPUT_DIR / "dynamic_execution_results.csv"
TIMEOUT_SECONDS = 10


class TimeoutException(Exception):
    """Exception raised when execution times out."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutException("Execution exceeded timeout")


def execute_with_timeout(func, args, timeout=TIMEOUT_SECONDS):
    """
    Execute function with timeout protection for infinite loops/recursion.
    Uses threading to handle timeout gracefully across platforms.
    
    Args:
        func: Function to execute
        args: Tuple of arguments for the function
        timeout: Timeout in seconds (default 10)
    
    Returns:
        Dictionary with status, error_type, error_message, and line_number
    """
    result_container = {"result": None, "exception": None}
    
    def wrapper():
        try:
            result_container["result"] = func(*args)
        except Exception as e:
            result_container["exception"] = e
    
    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # Thread still running - timeout occurred
        return {
            "status": "failed",
            "error_type": "TimeoutError",
            "error_message": "Execution exceeded timeout (likely infinite loop or recursion)",
            "line_number": ""
        }
    
    if result_container["exception"] is not None:
        e = result_container["exception"]
        tb = traceback.extract_tb(e.__traceback__)
        line_num = tb[-1].lineno if tb else ""
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else ""
        }
    
    if result_container["result"] is not None:
        return result_container["result"]
    
    return {
        "status": "failed",
        "error_type": "UnknownError",
        "error_message": "Execution completed but no result returned",
        "line_number": ""
    }


def execute_ds1000_test_inner(generated_code: str, code_context: str) -> Dict[str, Any]:
    """
    Inner function to execute DS1000 test (runs inside timeout wrapper).
    
    Args:
        generated_code: Generated code snippet
        code_context: Test context with test_execution function
    
    Returns:
        Dictionary with test results
    """
    test_env = {}
    
    try:
        # Load the test execution context
        exec(code_context, test_env)
        
        # Execute the test
        test_env['test_execution'](generated_code)
        
        return {
            "status": "passed",
            "error_type": "",
            "error_message": "",
            "line_number": ""
        }
    
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        line_num = tb[-1].lineno if tb else ""
        
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else ""
        }


def execute_ds1000_test(generated_code: str, code_context: str) -> Dict[str, Any]:
    """
    Execute DS1000 test with timeout protection.
    
    Args:
        generated_code: Generated code snippet
        code_context: Test context with test_execution function
    
    Returns:
        Dictionary with test results
    """
    return execute_with_timeout(execute_ds1000_test_inner, (generated_code, code_context))


def execute_humaneval_test_inner(generated_code: str, test_code: str, entry_point: str) -> Dict[str, Any]:
    """
    Inner function to execute HumanEval test (runs inside timeout wrapper).
    
    Args:
        generated_code: Generated function code
        test_code: Test code with check() function
        entry_point: Function name to test
    
    Returns:
        Dictionary with test results
    """
    test_env = {}
    
    try:
        # Execute generated code to define the function
        exec(generated_code, test_env)
        
        # Execute test code to define check function
        exec(test_code, test_env)
        
        # Run the check function with the generated function
        if entry_point in test_env and 'check' in test_env:
            test_env['check'](test_env[entry_point])
        else:
            raise NameError(f"Entry point '{entry_point}' or 'check' function not found")
        
        return {
            "status": "passed",
            "error_type": "",
            "error_message": "",
            "line_number": ""
        }
    
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        line_num = tb[-1].lineno if tb else ""
        
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else ""
        }


def execute_humaneval_test(generated_code: str, test_code: str, entry_point: str) -> Dict[str, Any]:
    """
    Execute HumanEval test with timeout protection.
    
    Args:
        generated_code: Generated function code
        test_code: Test code with check() function
        entry_point: Function name to test
    
    Returns:
        Dictionary with test results
    """
    return execute_with_timeout(execute_humaneval_test_inner, (generated_code, test_code, entry_point))


def execute_mbpp_test_inner(generated_code: str, test_list: List[str], test_imports: List[str]) -> Dict[str, Any]:
    """
    Inner function to execute MBPP test (runs inside timeout wrapper).
    
    Args:
        generated_code: Generated function code
        test_list: List of test assertions
        test_imports: List of import statements
    
    Returns:
        Dictionary with test results
    """
    test_env = {}
    
    try:
        # Execute imports
        for imp in test_imports:
            if imp.strip():  # Skip empty imports
                exec(imp, test_env)
        
        # Execute generated code
        exec(generated_code, test_env)
        
        # Run each test assertion
        for test_assertion in test_list:
            if test_assertion.strip():  # Skip empty assertions
                exec(test_assertion, test_env)
        
        return {
            "status": "passed",
            "error_type": "",
            "error_message": "",
            "line_number": ""
        }
    
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        line_num = tb[-1].lineno if tb else ""
        
        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else ""
        }


def execute_mbpp_test(generated_code: str, test_list: List[str], test_imports: List[str]) -> Dict[str, Any]:
    """
    Execute MBPP test with timeout protection.
    
    Args:
        generated_code: Generated function code
        test_list: List of test assertions
        test_imports: List of import statements
    
    Returns:
        Dictionary with test results
    """
    return execute_with_timeout(execute_mbpp_test_inner, (generated_code, test_list, test_imports))


def process_ds1000(gen_df: pd.DataFrame, test_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Process DS1000 dataset and execute tests.
    
    Args:
        gen_df: DataFrame with generated code
        test_df: DataFrame with test cases
    
    Returns:
        List of result dictionaries
    """
    results = []
    
    print(f"Processing DS1000: {len(gen_df)} samples")
    
    for idx, row in gen_df.iterrows():
        task_id = row.get('task_id')
        generated_code = str(row.get('full_code', ''))
        
        # Find corresponding test case
        test_row = test_df[test_df['prompt'] == row['prompt']]
        
        if test_row.empty:
            print(f"  Warning: No test found for task_id {task_id}")
            results.append({
                "dataset": "DS1000",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestNotFound",
                "error_message": "Test case not found in dataset",
                "line_number": ""
            })
            continue
        
        code_context = str(test_row.iloc[0]['code_context'])
        
        # Execute test
        result = execute_ds1000_test(generated_code, code_context)
        result["dataset"] = "DS1000"
        result["task_id"] = task_id
        
        results.append(result)
        
        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(gen_df)} samples")
    
    return results


def process_humaneval(gen_df: pd.DataFrame, test_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Process HumanEval dataset and execute tests.
    
    Args:
        gen_df: DataFrame with generated code
        test_df: DataFrame with test cases
    
    Returns:
        List of result dictionaries
    """
    results = []
    
    print(f"Processing HumanEval: {len(gen_df)} samples")
    
    for idx, row in gen_df.iterrows():
        task_id = row.get('task_id')
        generated_code = str(row.get('GENERATED_CODE', ''))
        
        # Find corresponding test case
        test_row = test_df[test_df['task_id'] == task_id]
        
        if test_row.empty:
            print(f"  Warning: No test found for task_id {task_id}")
            results.append({
                "dataset": "HumanEval",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestNotFound",
                "error_message": "Test case not found in dataset",
                "line_number": ""
            })
            continue
        
        test_code = str(test_row.iloc[0]['test'])
        entry_point = str(test_row.iloc[0]['entry_point'])
        
        # Execute test
        result = execute_humaneval_test(generated_code, test_code, entry_point)
        result["dataset"] = "HumanEval"
        result["task_id"] = task_id
        
        results.append(result)
        
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(gen_df)} samples")
    
    return results


def process_mbpp(gen_df: pd.DataFrame, test_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Process MBPP dataset and execute tests.
    
    Args:
        gen_df: DataFrame with generated code
        test_df: DataFrame with test cases
    
    Returns:
        List of result dictionaries
    """
    results = []
    
    print(f"Processing MBPP: {len(gen_df)} samples")
    
    for idx, row in gen_df.iterrows():
        task_id = row.get('task_id')
        generated_code = str(row.get('GENERATED_CODE', ''))
        
        # Find corresponding test case
        test_row = test_df[test_df['task_id'] == task_id]
        
        if test_row.empty:
            print(f"  Warning: No test found for task_id {task_id}")
            results.append({
                "dataset": "MBPP",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestNotFound",
                "error_message": "Test case not found in dataset",
                "line_number": ""
            })
            continue
        
        # Parse test_list and test_imports from string representation
        test_list_str = str(test_row.iloc[0]['test_list'])
        test_imports_str = str(test_row.iloc[0]['test_imports'])
        
        try:
            test_list = ast.literal_eval(test_list_str)
            test_imports = ast.literal_eval(test_imports_str)
        except Exception as e:
            print(f"  Error parsing test data for task_id {task_id}: {e}")
            results.append({
                "dataset": "MBPP",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestParseError",
                "error_message": f"Failed to parse test data: {str(e)}",
                "line_number": ""
            })
            continue
        
        # Execute test
        result = execute_mbpp_test(generated_code, test_list, test_imports)
        result["dataset"] = "MBPP"
        result["task_id"] = task_id
        
        results.append(result)
        
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(gen_df)} samples")
    
    return results


def run_dynamic_pipeline():
    """
    Main pipeline to process all datasets and generate results CSV.
    """
    print("=" * 80)
    print("Dynamic Test Execution Module")
    print("=" * 80)
    
    all_results = []
    
    # Process DS1000
    print("\n[1/3] Loading DS1000 dataset...")
    try:
        ds1000_gen = pd.read_csv(DATASETS["DS1000"]["gen_path"])
        ds1000_tests = pd.read_csv(DATASETS["DS1000"]["test_path"])
        ds1000_results = process_ds1000(ds1000_gen, ds1000_tests)
        all_results.extend(ds1000_results)
        print(f"✓ DS1000 completed: {len(ds1000_results)} results")
    except Exception as e:
        print(f"✗ DS1000 failed: {e}")
        traceback.print_exc()
    
    # Process HumanEval
    print("\n[2/3] Loading HumanEval dataset...")
    try:
        humaneval_gen = pd.read_csv(DATASETS["HumanEval"]["gen_path"])
        humaneval_tests = pd.read_csv(DATASETS["HumanEval"]["test_path"])
        humaneval_results = process_humaneval(humaneval_gen, humaneval_tests)
        all_results.extend(humaneval_results)
        print(f"✓ HumanEval completed: {len(humaneval_results)} results")
    except Exception as e:
        print(f"✗ HumanEval failed: {e}")
        traceback.print_exc()
    
    # Process MBPP
    print("\n[3/3] Loading MBPP dataset...")
    try:
        mbpp_gen = pd.read_csv(DATASETS["MBPP"]["gen_path"])
        mbpp_tests = pd.read_csv(DATASETS["MBPP"]["test_path"])
        mbpp_results = process_mbpp(mbpp_gen, mbpp_tests)
        all_results.extend(mbpp_results)
        print(f"✓ MBPP completed: {len(mbpp_results)} results")
    except Exception as e:
        print(f"✗ MBPP failed: {e}")
        traceback.print_exc()
    
    # Save results
    print("\n" + "=" * 80)
    print("Saving results...")
    
    if not all_results:
        print("✗ No results to save!")
        return
    
    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Convert to DataFrame and save
    results_df = pd.DataFrame(all_results)
    
    # Ensure column order
    columns = ["dataset", "task_id", "status", "error_type", "error_message", "line_number"]
    results_df = results_df[columns]
    
    results_df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"✓ Results saved to: {OUTPUT_CSV}")
    print(f"  Total results: {len(results_df)}")
    print(f"  Passed: {len(results_df[results_df['status'] == 'passed'])}")
    print(f"  Failed: {len(results_df[results_df['status'] == 'failed'])}")
    print("=" * 80)


if __name__ == "__main__":
    run_dynamic_pipeline()
