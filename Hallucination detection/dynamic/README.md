# Dynamic Test Execution Module

## Overview

This module executes generated code against test cases from three datasets (DS1000, HumanEval, MBPP) and captures detailed pass/fail status and error information.

## Files

- **`dynamic_execution.py`** - Main execution script
- **`dynamic_execution_results.csv`** - Output CSV with test results
- **`verify_results.py`** - Verification script to check results

## Usage

```bash
# Run with virtual environment
source ../../.venv/bin/activate
python dynamic_execution.py

# Or with absolute path
/Users/abhinavh.parthiban/Documents/FYP-26/.venv/bin/python dynamic_execution.py
```

## Output Format

The output CSV (`dynamic_execution_results.csv`) contains:

| Column | Description |
|--------|-------------|
| `dataset` | Dataset name (DS1000, HumanEval, or MBPP) |
| `task_id` | Unique task identifier |
| `status` | "passed" or "failed" |
| `error_type` | Exception class name (empty if passed) |
| `error_message` | Full, unmodified error message (empty if passed) |
| `line_number` | Line number from stack trace (empty if passed) |

## Features

### Timeout Protection
- 10-second timeout per test execution
- Catches infinite loops and infinite recursion
- Returns `TimeoutError` when timeout is exceeded

### Error Capture
Captures detailed error information including:
- **Error Type**: Exception class name (e.g., `SyntaxError`, `NameError`)
- **Error Message**: Unmodified error message from exception
- **Line Number**: Extracted from stack trace

### Supported Error Types
- SyntaxError
- IndentationError
- NameError
- ModuleNotFoundError
- AttributeError
- TypeError
- ValueError
- AssertionError
- RuntimeError
- TimeoutError (for infinite loops/recursion)

## Dataset-Specific Execution

### DS1000
- Uses `code_context` from dataset to define test environment
- Executes `test_execution()` function with generated code
- Validates against pandas/numpy operations

### HumanEval
- Executes generated function code
- Runs `check()` function from test suite
- Validates against canonical solutions

### MBPP
- Executes test imports
- Runs generated function code
- Validates against test assertions

## Results Summary

Last execution results:
- **Total**: 1,491 test cases
- **Passed**: 220 (14.8%)
- **Failed**: 1,271 (85.2%)

### By Dataset
- DS1000: 90/1,000 passed (9.0%)
- HumanEval: 130/164 passed (79.3%)
- MBPP: 0/327 passed (0.0%)

### Top Error Types
1. ModuleNotFoundError: 409
2. AssertionError: 209
3. TestNotFound: 207
4. SyntaxError: 123
5. RuntimeError: 102

## Implementation Details

### Timeout Strategy
Uses threading with timeout to handle:
- Infinite loops
- Infinite recursion
- Long-running computations

Thread-based timeout is cross-platform compatible and avoids multiprocessing pickling issues.

### Error Handling
- All exceptions are caught and logged
- Stack traces are parsed to extract line numbers
- Error messages are preserved without modification
- Passed tests have empty error fields

## Verification

Run the verification script to check results:

```bash
python verify_results.py
```

This displays:
- Total pass/fail counts
- Dataset breakdown
- Top error types
- Sample results with error details
