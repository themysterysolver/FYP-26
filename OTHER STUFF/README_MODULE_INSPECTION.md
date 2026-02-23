# How to See Module Inputs and Outputs

## Quick Answer

Each module (AST, CFG, LIB_API, Dynamic) receives **the same input**: the generated Python code string. The outputs are stored in different files that you can easily inspect.

## 📖 Documentation Files

I've created two comprehensive guides for you:

1. **`MODULE_DATA_FLOW.md`** - Complete reference with:
   - Detailed explanation of each module
   - Input/output formats
   - File locations
   - Data flow diagrams

2. **`view_task_data.sh`** - Shell script to view all module data for a specific task

## 🚀 Quick Start

### Option 1: Use the Shell Script (Easiest)

```bash
# View all module data for a specific task
./view_task_data.sh DS0001 DS1000

# View data for HumanEval task
./view_task_data.sh "HumanEval/0" HumanEval

# View data for MBPP task
./view_task_data.sh 1 MBPP
```

This will show you:
1. The generated code (input to all modules)
2. AST analysis result
3. CFG analysis result
4. LIB_API analysis result
5. Dynamic execution result
6. Unified APR input

### Option 2: Manual Inspection

For task `DS0001` from dataset `DS1000`:

```bash
# 1. View original generated code
grep "^DS0001," "Code generation/Qwen/ds1k_gen.csv"

# 2. View AST result
grep '"task_id": "DS0001"' "Hallucination detection/static/AST/ast_ds1000.jsonl" | python3 -m json.tool

# 3. View CFG result
grep '"task_id": "DS0001"' "Hallucination detection/static/CFG/cfg_ds1000.jsonl" | python3 -m json.tool

# 4. View LIB_API result
grep '"task_id": "DS0001"' "Hallucination detection/static/LIB_API/libapi_ds1000.jsonl" | python3 -m json.tool

# 5. View Dynamic result
grep '"task_id": "DS0001"' "Hallucination detection/dynamic/dynamic_ds1000.jsonl" | python3 -m json.tool

# 6. View unified APR input (note: task_id format is "DS-1000_DS0001")
grep '"task_id": "DS-1000_DS0001"' "APR/input/apr_input.jsonl" | python3 -m json.tool
```

## 📊 Understanding the Data Flow

```
GENERATED CODE (String)
    ↓
┌───┴─────┬────────┬─────────┐
│         │        │         │
▼         ▼        ▼         ▼
AST → CFG    LIB_API    Dynamic
│         │        │         │
└───┬─────┴────────┴─────────┘
    ↓
APR Input Builder
    ↓
apr_input.jsonl (Unified format)
```

### Key Points:

1. **Same Input for All**: All modules receive the generated Python code as a string
2. **Different Analyses**: Each module analyzes different aspects
   - AST: Syntax and structure
   - CFG: Control flow (unreachable code, missing returns)
   - LIB_API: Library usage (wrong APIs, missing modules)
   - Dynamic: Runtime behavior (test execution)
3. **Independent Execution**: Most modules run independently
   - Exception: CFG only runs if AST parsing succeeds
4. **Results Indexed by (dataset, task_id)**: Easy to look up

## 📁 File Locations Quick Reference

| What | Where |
|------|-------|
| **Input (Generated Code)** | `Code generation/Qwen/{dataset}_gen.csv` |
| **AST Output** | `Hallucination detection/static/AST/ast_{dataset}.jsonl`<br>`Hallucination detection/static/AST/ast_summary.csv` |
| **CFG Output** | `Hallucination detection/static/CFG/cfg_{dataset}.jsonl`<br>`Hallucination detection/static/CFG/cfg_summary.csv` |
| **LIB_API Output** | `Hallucination detection/static/LIB_API/libapi_{dataset}.jsonl`<br>`Hallucination detection/static/LIB_API/libapi_summary.csv` |
| **Dynamic Output** | `Hallucination detection/dynamic/dynamic_{dataset}.jsonl`<br>`Hallucination detection/dynamic/dynamic_summary.csv` |
| **APR Input (Unified)** | `APR/input/apr_input.jsonl` |

Replace `{dataset}` with:
- `ds1000` for DS-1000
- `humaneval` for HumanEval
- `mbpp` for MBPP

## 🔍 Example: Viewing Data for Task DS0001

### 1. Input (Generated Code)

**File**: `Code generation/Qwen/ds1k_gen.csv`

```csv
task_id,full_code,prompt,...
DS0001,"import pandas as pd\nimport numpy as np\n...",Problem: How to...,....
```

The `full_code` column contains the Python code string that gets passed to all modules.

### 2. AST Module Output

**File**: `Hallucination detection/static/AST/ast_ds1000.jsonl`

```json
{
  "dataset": "DS1000",
  "task_id": "DS0001",
  "ast_parsed": true,
  "syntax_error": 0,
  "indentation_error": 0,
  "structural_error": 0,
  "error_type": null,
  "line": null,
  "message": null,
  "structural_details": []
}
```

**Key Fields**:
- `ast_parsed`: `true` means code can be parsed, `false` means syntax error
- `error_type`: `"SyntaxError"`, `"IndentationError"`, or `null`
- `line`: Line number where error occurred

### 3. CFG Module Output

**File**: `Hallucination detection/static/CFG/cfg_ds1000.jsonl`

```json
{
  "dataset": "DS1000",
  "task_id": "DS0001",
  "cfg_analyzed": true,
  "unreachable_code": 0,
  "missing_return": 0,
  "cfg_details": []
}
```

**Key Fields**:
- `cfg_analyzed`: Whether CFG was built successfully
- `unreachable_code`: Count of unreachable code blocks
- `missing_return`: Count of functions without proper returns

### 4. LIB_API Module Output

**File**: `Hallucination detection/static/LIB_API/libapi_ds1000.jsonl`

```json
{
  "dataset": "DS1000",
  "task_id": "DS0001",
  "libapi_analyzed": true,
  "name_error": 0,
  "attribute_error": 1,
  "type_error": 0,
  "module_not_found": 0,
  "total_libapi_errors": 1,
  "libapi_details": [
    {
      "type": "attribute_error",
      "object": "pd",
      "attribute": "DataFrame_",
      "line": 5
    }
  ]
}
```

**Key Fields**:
- `module_not_found`: Missing `import` modules
- `attribute_error`: Invalid attributes (e.g., `pd.DataFrmae` instead of `pd.DataFrame`)
- `type_error`: Wrong function parameters
- `libapi_details`: List of specific errors with line numbers

### 5. Dynamic Module Output

**File**: `Hallucination detection/dynamic/dynamic_ds1000.jsonl`

```json
{
  "task_id": "DS0001",
  "status": "runtime_error",
  "error_type": "AttributeError",
  "hallucination_subtype": "api_misuse",
  "execution_time_ms": 123.45,
  "traceback": "Traceback (most recent call last):\n  File...",
  "test_results": [...]
}
```

**Key Fields**:
- `status`: `"passed"`, `"runtime_error"`, `"assertion_failure"`, `"timeout"`
- `hallucination_subtype`: Specific category of error
- `traceback`: Full stack trace if error occurred

### 6. Unified APR Input

**File**: `APR/input/apr_input.jsonl`

```json
{
  "task_id": "DS-1000_DS0001",
  "generated_code": "import pandas as pd\n...",
  "static_ast": {
    "status": "success",
    "error_type": null,
    ...
  },
  "static_cfg": {
    "status": "success",
    "unreachable_code": [],
    ...
  },
  "static_library_api": {
    "status": "api_errors_found",
    "nonexistent_apis": [...],
    ...
  },
  "dynamic_analysis": {
    "status": "runtime_error",
    "failure_details": {...},
    ...
  },
  "problem_description": "...",
  "function_signature": "...",
  "test_cases": [...]
}
```

This unified format contains:
- All static analysis results (AST, CFG, LIB_API)
- Dynamic analysis results
- Problem context (description, signature, test cases)
- Alignment check (consistency between static and dynamic)

## 💡 Common Tasks

### Find all tasks with syntax errors:
```bash
grep '"syntax_error": 1' "Hallucination detection/static/AST/ast_ds1000.jsonl"
```

### Find all tasks with API errors:
```bash
awk -F',' '$7 > 0' "Hallucination detection/static/LIB_API/libapi_summary.csv"
```

### Count errors by type:
```bash
# AST errors
cut -d',' -f4 "Hallucination detection/static/AST/ast_summary.csv" | sort | uniq -c

# LIB_API errors
cut -d',' -f5,6,7,8 "Hallucination detection/static/LIB_API/libapi_summary.csv"
```

### View a specific task across all modules:
```bash
./view_task_data.sh DS0001 DS1000
```

## 🎓 Understanding Module Inputs

**Question**: "What is the input to each module?"

**Answer**: All modules receive the **same input**: the generated Python code as a string.

- **Source**: CSV files in `Code generation/Qwen/`
- **Column name**: 
  - DS1000: `full_code`
  - HumanEval/MBPP: `GENERATED_CODE`
- **Format**: Plain Python code string (may contain `\n` for newlines)

**Example**:
```python
# This is what gets passed to analyze_ast(), analyze_cfg(), analyze_library_api()
code = """
import pandas as pd
import numpy as np

df = pd.DataFrame({'A': [1, 2, 3]})
result = df.sum()
"""

# Each module analyzes this string independently
ast_result = analyze_ast(code)
cfg_result = analyze_cfg(code)
libapi_result = analyze_library_api(code)
```

## 📖 Further Reading

- **Complete module documentation**: See `MODULE_DATA_FLOW.md`
- **Schema definitions**: See `APR/input/schema.py`
- **Integration logic**: See `APR/input/builder.py`
- **Module implementations**:
  - AST: `Hallucination detection/static/AST/ast_analysis.py`
  - CFG: `Hallucination detection/static/CFG/cfg_analysis.py`
  - LIB_API: `Hallucination detection/static/LIB_API/library_api.py`
  - Dynamic: `Hallucination detection/dynamic/dynamic_detection.py`

## 🤔 Still Have Questions?

Common questions answered:

**Q: How do I know what code was analyzed for task X?**  
A: Look in `Code generation/Qwen/{dataset}_gen.csv`, find the row with matching `task_id`, check the `full_code` or `GENERATED_CODE` column.

**Q: Where do I see what errors AST found?**  
A: Check `Hallucination detection/static/AST/ast_{dataset}.jsonl` or `ast_summary.csv`, find the row with matching `task_id`.

**Q: How are results combined into APR input?**  
A: The `APR/input/builder.py` script reads all CSV/JSONL outputs, indexes them by `(dataset, task_id)`, and merges them into a unified format.

**Q: Can I run just one module on custom code?**  
A: Yes! Each module has a standalone function:
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "Hallucination detection" / "static" / "AST"))

from ast_analysis import analyze_ast

code = "print('hello world')"
result = analyze_ast(code)
print(result)
```
