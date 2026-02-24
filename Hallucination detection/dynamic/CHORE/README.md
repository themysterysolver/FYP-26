# Dynamic Test Execution Module

This module executes generated code against test cases and captures detailed error information.

## Setup (Local Installation)

### Install Dependencies

All dependencies are installed locally (no virtual environment needed):

```bash
pip3 install --user --break-system-packages pandas numpy matplotlib
```

Or if you need additional scientific libraries:

```bash
pip3 install --user --break-system-packages pandas numpy matplotlib scipy
```

### Verify Installation

```bash
python3 -c "import pandas; import numpy; import matplotlib; print('✓ Dependencies ready')"
```

## Usage

### Run Full Pipeline

Execute all datasets (DS1000, HumanEval, MBPP):

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26
python3 "Hallucination detection/dynamic/dynamic_execution.py"
```

### Import as Module

```python
import sys
sys.path.insert(0, 'Hallucination detection/dynamic')
import dynamic_execution

# Run the pipeline programmatically
dynamic_execution.run_dynamic_pipeline()
```

## Output

Results are saved to:
```
Hallucination detection/dynamic/dynamic_execution_results.csv
```

### Output Columns

- `dataset`: Dataset name (DS1000, HumanEval, MBPP)
- `task_id`: Unique task identifier
- `status`: "passed" or "failed"
- `error_type`: Type of error (e.g., SyntaxError, ValueError, AssertionError)
- `error_message`: Detailed error message
- `line_number`: Line where error occurred
- `test_case`: Test case code (for AssertionErrors)
- `testcase_output`: Full traceback (for AssertionErrors)
- `generated_code`: The code that was executed

## Configuration

Edit paths in `dynamic_execution.py`:

```python
PROJECT_ROOT = Path(__file__).parent.parent.parent
GENERATION_DIR = PROJECT_ROOT / "Code generation" / "Qwen"
DATASET_DIR = PROJECT_ROOT / "Dataset used"
OUTPUT_DIR = Path(__file__).parent
```

## Features

- ✅ Timeout protection (10 seconds per test)
- ✅ Captures syntax, runtime, and assertion errors
- ✅ Extracts line numbers from error messages
- ✅ Handles infinite loops and recursion
- ✅ Processes three datasets: DS1000, HumanEval, MBPP
- ✅ Thread-safe execution with daemon threads
- ✅ Post-processes SyntaxError line numbers

## Environment

- **Python:** 3.14.3
- **OS:** macOS (darwin 24.6.0)
- **pandas:** 3.0.0
- **numpy:** 2.4.2
- **matplotlib:** 3.10.8

## Notes

- No virtual environment required - all packages installed locally with `--user` flag
- Runs directly with system Python 3
- Compatible with externally-managed Python environments (Homebrew)
