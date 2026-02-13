# Fault Information Integration

This directory contains the consolidated fault information generated from multiple hallucination detection sources.

## Output File

**`fault_information.csv`** - Unified fault information for all tasks

### Structure

The CSV file contains the following columns:

- **dataset**: Source dataset name (DS1000, HumanEval, or MBPP)
- **status**: "passed" or "hallucinated"
- **task_id**: Task identifier (format varies by dataset: e.g., DS0000 for DS1000, HumanEval/0 for HumanEval, 100 for MBPP)
- **ast_info**: JSON string containing AST error details `{type, value, message}` where value is the line number
- **cfg_info**: JSON string containing CFG error details
- **lib_info**: JSON string containing LIB_API error details  
- **dynamic_info**: JSON string containing dynamic execution error details `{error_type, error_message, line_no, test_case}`

### Data Population Rules

- **passed tasks**: Only `dataset`, `status`, and `task_id` are populated; error info fields are empty
- **hallucinated tasks**: All fields are populated with dataset, status, task_id, and applicable error information

## Source Files

The consolidated data is generated from:

1. `static/AST/ast_summary.csv` - Abstract Syntax Tree analysis results
2. `static/CFG/cfg_summary.csv` - Control Flow Graph analysis results
3. `static/LIB_API/libapi_summary.csv` - Library/API usage validation results
4. `dynamic/dynamic_execution_results.csv` - Dynamic execution test results

## Status Determination

A task is marked as **"hallucinated"** if ANY of these conditions are true:

- **AST errors**: `ast_parsed == False` OR any error count > 0
- **CFG errors**: `cfg_details` is not an empty list
- **LIB_API errors**: `total_libapi_errors > 0`
- **Dynamic errors**: `status == 'failed'`

Otherwise, the task is marked as **"passed"**.

## Regenerating the Output

To regenerate the fault information file, run:

```bash
cd "/path/to/Hallucination detection"
python3 integrate_fault_data.py
```

The script will:
1. Load all 4 source CSV files
2. Merge them on `task_id`
3. Determine status for each task
4. Generate the consolidated output file

## Statistics

Current output (as of last run):
- Total tasks: 1,491
  - DS1000: 1,000 tasks
  - MBPP: 327 tasks
  - HumanEval: 164 tasks
- Passed: 152
- Hallucinated: 1,339
