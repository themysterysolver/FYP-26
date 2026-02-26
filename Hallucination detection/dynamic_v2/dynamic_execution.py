import os
import sys
import ast
import re
import traceback
import pandas as pd
import numpy as np
import signal
import threading
import json
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

TIMEOUT_SECONDS = 10


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException("Execution exceeded timeout")


def extract_syntax_error_line(error_message: str) -> str:

    match = re.search(r'\(<string>,\s*line\s+(\d+)\)', error_message)
    if match:
        return match.group(1)
    return ""

#objects are stores as hasesh which can't be used thus we serialize this!
def serialize_value(value: Any, max_length: int = 500) -> str:
    try:
        if isinstance(value, pd.DataFrame):
            try:
                serialized = value.to_dict('list')
                result = f"DataFrame({serialized})"
            except:
                result = f"DataFrame:\n{value.to_string()}"
        elif isinstance(value, pd.Series):
            try:
                serialized = value.to_dict()
                result = f"Series({serialized})"
            except:
                result = f"Series:\n{value.to_string()}"
        elif isinstance(value, np.ndarray):
            try:
                result = f"array({value.tolist()})"
            except:
                result = f"array({repr(value)})"
        elif isinstance(value, (dict, list, tuple)):
            result = str(value)
        elif value is None:
            return "None"
        else:
            try:
                if pd.isna(value):
                    return "NaN"
            except (TypeError, ValueError):
                pass
            result = str(value)

        if len(result) > max_length:
            result = result[:max_length] + "...[truncated]"

        return result
    except Exception as e:
        return f"<Serialization Error: {str(e)}>"


def extract_ds1000_test_cases(generated_code: str, code_context: str) -> List[List[str]]:

    test_cases_data = []

    try:
        # testing environment
        test_env = {}
        exec(code_context, test_env)

        if 'generate_test_case' not in test_env:
            return []

        for test_id in range(1, 10):
            try:
                test_input, expected_result = test_env['generate_test_case'](test_id)

                exec_env = {}
                exec_env['test_input'] = test_input

                try:
                    exec(generated_code, exec_env)
                    actual_result = exec_env.get('result', '<No result variable>')
                except Exception as exec_error:
                    actual_result = f"<Execution Error: {str(exec_error)}>"

                # Serialize the values from objects
                input_str = serialize_value(test_input)
                expected_str = serialize_value(expected_result)
                actual_str = serialize_value(actual_result)

                test_cases_data.append([input_str, expected_str, actual_str])

            except Exception:
                break
    except Exception as e:
        pass
    return test_cases_data


def extract_humaneval_test_cases(generated_code: str, test_code: str, entry_point: str) -> List[List[str]]:
    test_cases_data = []
    try:
        tree = ast.parse(test_code)

        test_env = {}
        exec(generated_code, test_env)

        if entry_point not in test_env:
            return []

        func = test_env[entry_point]

        #using as to find all the assert statements!
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert): #ast.Assert
                try:
                    test_node = node.test

                    # Handle assert func(input) == expected
                    if isinstance(test_node, ast.Compare): #ast.Compare
                        left = test_node.left
                        comparators = test_node.comparators
                        if isinstance(left, ast.Call):
                            args = []
                            for arg in left.args:
                                try:
                                    arg_value = ast.literal_eval(arg)
                                    args.append(arg_value)
                                except:
                                    args.append("<complex_arg>")

                            if comparators:
                                try:
                                    expected_value = ast.literal_eval(comparators[0])
                                except:
                                    expected_value = "<complex_expected>"
                            else:
                                expected_value = "<unknown>"

                            # Execute function with args to get actual
                            try:
                                actual_value = func(*args)
                            except Exception as exec_error:
                                actual_value = f"<Error: {str(exec_error)}>"

                            # Serialize
                            input_str = serialize_value(tuple(args) if len(args) > 1 else (args[0] if args else "()"))
                            expected_str = serialize_value(expected_value)
                            actual_str = serialize_value(actual_value)

                            test_cases_data.append([input_str, expected_str, actual_str])
                except Exception:
                    continue

    except Exception as e:
        pass

    return test_cases_data


def extract_mbpp_test_cases(generated_code: str, test_list: List[str], test_imports: List[str]) -> List[List[str]]:

    test_cases_data = []

    try:
        test_env = {}
        for imp in test_imports:
            if imp.strip():
                exec(imp, test_env)
        exec(generated_code, test_env)

        for test_assertion in test_list:
            if not test_assertion.strip():
                continue

            try:
                tree = ast.parse(test_assertion)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        test_node = node.test

                        if isinstance(test_node, ast.Compare):
                            left = test_node.left
                            comparators = test_node.comparators

                            if isinstance(left, ast.Call):

                                func_name = None
                                if isinstance(left.func, ast.Name):
                                    func_name = left.func.id

                                if func_name and func_name in test_env:
                                    func = test_env[func_name]

                                    args = []
                                    for arg in left.args:
                                        try:
                                            arg_value = eval(compile(ast.Expression(arg), '<string>', 'eval'), test_env)
                                            args.append(arg_value)
                                        except:
                                            args.append("<complex_arg>")

                                    if comparators:
                                        try:
                                            expected_value = eval(compile(ast.Expression(comparators[0]), '<string>', 'eval'), test_env)
                                        except:
                                            expected_value = "<complex_expected>"
                                    else:
                                        expected_value = "<unknown>"

                                    try:
                                        actual_value = func(*args)
                                    except Exception as exec_error:
                                        actual_value = f"<Error: {str(exec_error)}>"

                                    # Serialize
                                    input_str = serialize_value(tuple(args) if len(args) > 1 else (args[0] if args else "()"))
                                    expected_str = serialize_value(expected_value)
                                    actual_str = serialize_value(actual_value)

                                    test_cases_data.append([input_str, expected_str, actual_str])
            except Exception:
                continue

    except Exception as e:
        pass

    return test_cases_data


def execute_with_timeout(func, args, timeout=TIMEOUT_SECONDS):

    result_container = {"result": None, "exception": None, "traceback": None}

    def wrapper():
        try:
            result_container["result"] = func(*args)
        except Exception as e:
            result_container["exception"] = e
            result_container["traceback"] = traceback.format_exc()

    thread = threading.Thread(target=wrapper)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        # Thread still running - timeout occurred
        # Extract generated_code from args if available
        gen_code = args[0] if args else ""
        return {
            "status": "failed",
            "error_type": "TimeoutError",
            "error_message": "Execution exceeded timeout (likely infinite loop or recursion)",
            "line_number": "",
            "test_case": "",
            "testcase_output": "",
            "generated_code": gen_code
        }

    if result_container["exception"] is not None:
        e = result_container["exception"]
        is_assertion_error = isinstance(e, AssertionError)
        is_syntax_error = isinstance(e, SyntaxError)
        tb = traceback.extract_tb(e.__traceback__)
        full_traceback = result_container["traceback"] or ""


        if is_assertion_error:
            line_num = ""
        elif is_syntax_error:
            line_num = extract_syntax_error_line(str(e))
        else:
            string_frames = [frame for frame in tb if '<string>' in frame.filename]
            line_num = min((frame.lineno for frame in string_frames), default="") if string_frames else ""

        gen_code = args[0] if args else ""

        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else "",
            "test_case": "",
            "testcase_output": full_traceback if is_assertion_error else "",
            "generated_code": gen_code
        }

    if result_container["result"] is not None:
        return result_container["result"]

    gen_code = args[0] if args else ""
    return {
        "status": "failed",
        "error_type": "UnknownError",
        "error_message": "Execution completed but no result returned",
        "line_number": "",
        "test_case": "",
        "testcase_output": "",
        "generated_code": gen_code
    }


def execute_ds1000_test_inner(generated_code: str, code_context: str) -> Dict[str, Any]:
    """
    Inner function to execute DS1000 test (runs inside timeout wrapper).

    Args:
        generated_code: Generated code snippet
        code_context: Test context with test_execution function

    Returns:
        Dictionary with test results including test_case and testcase_output
    """
    test_env = {}
    line_offset = 0

    try:

        exec(code_context, test_env)

        # Compute line offset from exec_context template
        # DS1000's test_execution() wraps generated_code inside exec_context,
        # prepending setup lines before [insert]. Traceback line numbers refer
        # to the combined code, so we must subtract the offset to map back to
        # the original generated_code.
        exec_ctx = test_env.get('exec_context', '')
        if exec_ctx and '[insert]' in exec_ctx:
            line_offset = exec_ctx.split('[insert]')[0].count('\n')

        # Execute the test
        test_env['test_execution'](generated_code)

        return {
            "status": "passed",
            "error_type": "",
            "error_message": "",
            "line_number": "",
            "test_case": "",
            "testcase_output": "",
            "generated_code": generated_code
        }

    except Exception as e:
        is_assertion_error = isinstance(e, AssertionError)
        is_syntax_error = isinstance(e, SyntaxError)
        tb = traceback.extract_tb(e.__traceback__)
        full_traceback = traceback.format_exc()

        # Get line number based on error type
        if is_assertion_error:
            # AssertionErrors don't populate line_number
            line_num = ""
        elif is_syntax_error:
            # Extract line number from SyntaxError message
            line_num = extract_syntax_error_line(str(e))
            # Adjust for exec_context offset
            if line_num and line_offset:
                line_num = str(max(1, int(line_num) - line_offset))
        else:
            # For runtime errors, use the last <string> frame (innermost exec
            # context = actual error location), then adjust for the offset
            string_frames = [frame for frame in tb if '<string>' in frame.filename]
            if string_frames:
                raw_line = string_frames[-1].lineno
                line_num = str(max(1, raw_line - line_offset)) if raw_line else ""
            else:
                line_num = ""

        # Extract test case data for all failed tests
        test_case_data = extract_ds1000_test_cases(generated_code, code_context)
        test_case_json = json.dumps(test_case_data) if test_case_data else ""

        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else "",
            "test_case": test_case_json,
            "testcase_output": full_traceback if is_assertion_error else "",
            "generated_code": generated_code
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
        Dictionary with test results including test_case and testcase_output
    """
    test_env = {}

    try:

        exec(generated_code, test_env)

        exec(test_code, test_env)

        if entry_point in test_env and 'check' in test_env:
            test_env['check'](test_env[entry_point])
        else:
            raise NameError(f"Entry point '{entry_point}' or 'check' function not found")

        return {
            "status": "passed",
            "error_type": "",
            "error_message": "",
            "line_number": "",
            "test_case": "",
            "testcase_output": "",
            "generated_code": generated_code
        }

    except Exception as e:
        is_assertion_error = isinstance(e, AssertionError)
        is_syntax_error = isinstance(e, SyntaxError)
        tb = traceback.extract_tb(e.__traceback__)
        full_traceback = traceback.format_exc()

        if is_assertion_error:
            line_num = ""
        elif is_syntax_error:
            line_num = extract_syntax_error_line(str(e))
        else:

            string_frames = [frame for frame in tb if '<string>' in frame.filename]
            line_num = min((frame.lineno for frame in string_frames), default="") if string_frames else ""

        # Extract test case data for all failed tests
        test_case_data = extract_humaneval_test_cases(generated_code, test_code, entry_point)
        test_case_json = json.dumps(test_case_data) if test_case_data else ""

        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else "",
            "test_case": test_case_json,
            "testcase_output": full_traceback if is_assertion_error else "",
            "generated_code": generated_code
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
        Dictionary with test results including test_case and testcase_output
    """
    test_env = {}

    test_case_parts = []
    if test_imports:
        test_case_parts.extend([imp for imp in test_imports if imp.strip()])
    if test_list:
        test_case_parts.extend([test for test in test_list if test.strip()])
    formatted_test_case = "\n".join(test_case_parts)

    try:
        for imp in test_imports:
            if imp.strip():
                exec(imp, test_env)


        exec(generated_code, test_env)

        # Run each test assertion
        for test_assertion in test_list:
            if test_assertion.strip():  # Skip empty assertions
                exec(test_assertion, test_env)

        return {
            "status": "passed",
            "error_type": "",
            "error_message": "",
            "line_number": "",
            "test_case": "",
            "testcase_output": "",
            "generated_code": generated_code
        }

    except Exception as e:
        is_assertion_error = isinstance(e, AssertionError)
        is_syntax_error = isinstance(e, SyntaxError)
        tb = traceback.extract_tb(e.__traceback__)
        full_traceback = traceback.format_exc()

        # Get line number based on error type
        if is_assertion_error:
            # AssertionErrors don't populate line_number
            line_num = ""
        elif is_syntax_error:
            # Extract line number from SyntaxError message
            line_num = extract_syntax_error_line(str(e))
        else:
            # For runtime errors, get minimum line from <string> frames (user's code)
            string_frames = [frame for frame in tb if '<string>' in frame.filename]
            line_num = min((frame.lineno for frame in string_frames), default="") if string_frames else ""

        # Extract test case data for all failed tests
        test_case_data = extract_mbpp_test_cases(generated_code, test_list, test_imports)
        test_case_json = json.dumps(test_case_data) if test_case_data else ""

        return {
            "status": "failed",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "line_number": str(line_num) if line_num else "",
            "test_case": test_case_json,
            "testcase_output": full_traceback if is_assertion_error else "",
            "generated_code": generated_code
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


def process_ds1000(gen_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Process DS1000 dataset and execute tests.

    Args:
        gen_df: DataFrame with generated code and test cases

    Returns:
        List of result dictionaries
    """
    results = []

    print(f"Processing DS1000: {len(gen_df)} samples")

    for idx, row in gen_df.iterrows():
        task_id = row.get('task_id')
        generated_code = str(row.get('full_code', ''))

        # Get code_context from the same row
        if 'code_context' not in row or pd.isna(row['code_context']):
            print(f"  Warning: No test found for task_id {task_id}")
            results.append({
                "dataset": "ds1000",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestNotFound",
                "error_message": "Test case not found in dataset",
                "line_number": "",
                "test_case": "",
                "testcase_output": "",
                "generated_code": generated_code
            })
            continue

        code_context = str(row['code_context'])

        # Execute test
        result = execute_ds1000_test(generated_code, code_context)
        result["dataset"] = "ds1000"
        result["task_id"] = task_id

        results.append(result)

        if (idx + 1) % 100 == 0:
            print(f"  Processed {idx + 1}/{len(gen_df)} samples")

    return results


def process_humaneval(gen_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Process HumanEval dataset and execute tests.

    Args:
        gen_df: DataFrame with generated code and test cases

    Returns:
        List of result dictionaries
    """
    results = []

    print(f"Processing HumanEval: {len(gen_df)} samples")

    for idx, row in gen_df.iterrows():
        task_id = row.get('task_id')
        generated_code = str(row.get('GENERATED_CODE', ''))

        # Get test data from the same row
        if 'test' not in row or pd.isna(row['test']) or 'entry_point' not in row or pd.isna(row['entry_point']):
            print(f"  Warning: No test found for task_id {task_id}")
            results.append({
                "dataset": "humaneval",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestNotFound",
                "error_message": "Test case not found in dataset",
                "line_number": "",
                "test_case": "",
                "testcase_output": "",
                "generated_code": generated_code
            })
            continue

        test_code = str(row['test'])
        entry_point = str(row['entry_point'])

        # Execute test
        result = execute_humaneval_test(generated_code, test_code, entry_point)
        result["dataset"] = "humaneval"
        result["task_id"] = task_id

        results.append(result)

        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(gen_df)} samples")

    return results


def process_mbpp(gen_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Process MBPP dataset and execute tests.

    Args:
        gen_df: DataFrame with generated code and test cases

    Returns:
        List of result dictionaries
    """
    results = []

    print(f"Processing MBPP: {len(gen_df)} samples")

    for idx, row in gen_df.iterrows():
        task_id = row.get('task_id')
        generated_code = str(row.get('GENERATED_CODE', ''))

        # Get test data from the same row
        if 'test_list' not in row or pd.isna(row['test_list']) or 'test_imports' not in row or pd.isna(row['test_imports']):
            print(f"  Warning: No test found for task_id {task_id}")
            results.append({
                "dataset": "mbpp",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestNotFound",
                "error_message": "Test case not found in dataset",
                "line_number": "",
                "test_case": "",
                "testcase_output": "",
                "generated_code": generated_code
            })
            continue

        # Parse test_list and test_imports from string representation
        test_list_str = str(row['test_list'])
        test_imports_str = str(row['test_imports'])

        try:
            # Fix for MBPP CSV format: Replace actual newlines between strings with commas
            # The CSV stores lists like: ['test1'\n 'test2'\n 'test3'] (actual newlines)
            # Python's literal_eval treats adjacent strings as concatenation, so we need commas
            test_list_str_fixed = test_list_str.replace("'\n '", "', '").replace('"\n "', '", "')
            test_list = ast.literal_eval(test_list_str_fixed)
            test_imports = ast.literal_eval(test_imports_str)
        except Exception as e:
            print(f"  Error parsing test data for task_id {task_id}: {e}")
            results.append({
                "dataset": "mbpp",
                "task_id": task_id,
                "status": "failed",
                "error_type": "TestParseError",
                "error_message": f"Failed to parse test data: {str(e)}",
                "line_number": "",
                "test_case": "",
                "testcase_output": "",
                "generated_code": generated_code
            })
            continue

        # Execute test
        result = execute_mbpp_test(generated_code, test_list, test_imports)
        result["dataset"] = "mbpp"
        result["task_id"] = task_id

        results.append(result)

        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx + 1}/{len(gen_df)} samples")

    return results


def update_syntax_error_line_numbers(csv_path: Path) -> int:
    """
    Post-process existing CSV to extract line numbers from SyntaxError messages.
    This ensures any SyntaxErrors that slipped through without line numbers get updated.

    Args:
        csv_path: Path to the results CSV file

    Returns:
        Number of rows updated
    """
    print("\nPost-processing: Updating SyntaxError line numbers...")

    try:
        df = pd.read_csv(csv_path)
        updates = 0

        # Find SyntaxErrors with empty line_number
        for idx, row in df.iterrows():
            if row['error_type'] == 'SyntaxError' and pd.notna(row['error_message']):
                # Check if line_number is empty or NaN
                if pd.isna(row['line_number']) or str(row['line_number']).strip() == '':
                    # Extract line number from error message
                    line_num = extract_syntax_error_line(str(row['error_message']))
                    if line_num:
                        df.at[idx, 'line_number'] = line_num
                        updates += 1

        if updates > 0:
            df.to_csv(csv_path, index=False)
            print(f"✓ Updated {updates} SyntaxError entries with line numbers")
        else:
            print("✓ All SyntaxError entries already have line numbers")

        return updates

    except Exception as e:
        print(f"✗ Failed to update SyntaxError line numbers: {e}")
        traceback.print_exc()
        return 0

def run_dynamic_driver_dynamic_analysis(
    row: pd.DataFrame,
    dataset_type: str,
    task_id: str,
    generated_code: str = "generated_code"
) -> pd.DataFrame:
    """
    Dynamic execution driver.

    Args:
        df: DataFrame containing generated code + test columns
        dataset_type: "DS1000", "HumanEval", or "MBPP"
        code_column: column containing code to evaluate

    Returns:
        DataFrame with structured dynamic execution results
    """

    results = []


    if dataset_type == "ds1000":
        code_context = str(row.get("code_context", ""))
        result = execute_ds1000_test(generated_code, code_context)

    elif dataset_type == "humaneval":
        test_code = str(row.get("test", ""))
        entry_point = str(row.get("entry_point", ""))
        result = execute_humaneval_test(generated_code, test_code, entry_point)

    elif dataset_type == "mbpp":
        try:
            test_list = row.get("test_list", [])
            test_imports = row.get("test_imports", [])
            result = execute_mbpp_test(generated_code, test_list, test_imports)
        except Exception as e:
            result = {
                "status": "failed",
                "error_type": "TestParseError",
                "error_message": str(e),
                "line_number": "",
                "test_case": "",
                "testcase_output": "",
                "generated_code": generated_code
            }

    else:
        result = {
            "status": "failed",
            "error_type": "UnknownDataset",
            "error_message": f"Unsupported dataset: {dataset_type}",
            "line_number": "",
            "test_case": "",
            "testcase_output": "",
            "generated_code": generated_code
        }

        result["dataset"] = dataset_type
        result["task_id"] = task_id



    return result

