# Module Data Flow Guide

## Overview: How to See Input/Output for Each Module

This guide explains what data each module (AST, CFG, LIB_API, Dynamic) receives as input and what it outputs, and where to observe this data.

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      GENERATED CODE (Input)                      │
│        Source: Code generation/Qwen/{dataset}_gen.csv            │
│         Column: "full_code" (DS1000) or "GENERATED_CODE"         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     │
        ┌───────────────────────┐        │
        │   1. AST ANALYSIS     │        │
        │   (Static)            │        │
        └───────────┬───────────┘        │
                    │                     │
                    ▼                     ▼
        ┌───────────────────────┐  ┌────────────────────┐
        │   2. CFG ANALYSIS     │  │  3. LIB_API        │
        │   (Static)            │  │     ANALYSIS       │
        │   Only if AST passes  │  │     (Static)       │
        └───────────┬───────────┘  └─────────┬──────────┘
                    │                        │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  4. DYNAMIC EXECUTION  │
                    │  (Runtime Testing)     │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   APR INPUT BUILDER    │
                    │   (Unified Format)     │
                    └────────────────────────┘
```

---

## 📁 Module 1: AST (Abstract Syntax Tree) Analysis

### **Purpose**
Parse code and check for syntax/structural errors

### **Input**
- **Type**: String (Python code)
- **Source File**: 
  - DS1000: `Code generation/Qwen/ds1k_gen.csv` → column `full_code`
  - HumanEval: `Code generation/Qwen/humaneval_gen.csv` → column `GENERATED_CODE`
  - MBPP: `Code generation/Qwen/mbpp_gen.csv` → column `GENERATED_CODE`

### **Function Signature**
```python
def analyze_ast(code: str) -> dict
```
Located in: `Hallucination detection/static/AST/ast_analysis.py`

### **Output Structure**
```python
{
    "ast_parsed": bool,              # Can the code be parsed?
    "syntax_error": 0 or 1,          # Syntax error count
    "indentation_error": 0 or 1,     # Indentation error count
    "structural_error": int,         # Structural violation count
    "error_type": str | None,        # "SyntaxError", "IndentationError", etc.
    "line": int | None,              # Line number where error occurred
    "message": str | None,           # Error message details
    "structural_details": [          # List of structural issues
        {
            "type": str,             # e.g., "return_outside_function"
            "start_line": int,
            "end_line": int
        }
    ]
}
```

### **Where to Observe Output**
1. **Per-dataset JSONL files** (one line per task):
   - `Hallucination detection/static/AST/ast_ds1000.jsonl`
   - `Hallucination detection/static/AST/ast_humaneval.jsonl`
   - `Hallucination detection/static/AST/ast_mbpp.jsonl`

2. **Unified CSV summary**:
   - `Hallucination detection/static/AST/ast_summary.csv`
   - Columns: `dataset`, `task_id`, `ast_parsed`, `syntax_error`, etc.

### **Example: View AST Results**
```bash
# View first 10 AST results for DS1000
head -10 "Hallucination detection/static/AST/ast_ds1000.jsonl"

# View summary statistics
csvlook "Hallucination detection/static/AST/ast_summary.csv" | head -20
```

---

## 📁 Module 2: CFG (Control Flow Graph) Analysis

### **Purpose**
Analyze control flow for unreachable code and missing returns

### **Input**
- **Type**: String (Python code) - **ONLY if AST parsing succeeds**
- **Prerequisite**: `ast_parsed == True` from AST module
- **Source**: Same as AST module

### **Function Signature**
```python
def analyze_cfg(code: str) -> dict
```
Located in: `Hallucination detection/static/CFG/cfg_analysis.py`

### **Output Structure**
```python
{
    "cfg_analyzed": bool,            # Was CFG built successfully?
    "unreachable_code": int,         # Count of unreachable blocks
    "missing_return": int,           # Count of functions missing returns
    "cfg_details": [                 # Detailed issues list
        {
            "type": str,             # "unreachable_code" or "missing_return"
            "function": str,         # Function name (for missing_return)
            "start_line": int,
            "end_line": int
        }
    ]
}
```

### **Where to Observe Output**
1. **Per-dataset JSONL files**:
   - `Hallucination detection/static/CFG/cfg_ds1000.jsonl`
   - `Hallucination detection/static/CFG/cfg_humaneval.jsonl`
   - `Hallucination detection/static/CFG/cfg_mbpp.jsonl`

2. **Unified CSV summary**:
   - `Hallucination detection/static/CFG/cfg_summary.csv`

### **Example: View CFG Results**
```bash
# View CFG results for tasks with issues
grep '"unreachable_code": [^0]' "Hallucination detection/static/CFG/cfg_ds1000.jsonl"
```

---

## 📁 Module 3: LIB_API (Library API Validation)

### **Purpose**
Check for invalid library usage: missing modules, wrong attributes, bad parameters

### **Input**
- **Type**: String (Python code)
- **Source**: Same as AST module
- **Note**: Runs independently of AST/CFG results

### **Function Signature**
```python
def analyze_library_api(code: str) -> dict
```
Located in: `Hallucination detection/static/LIB_API/library_api.py`

### **Output Structure**
```python
{
    "libapi_analyzed": bool,         # Was analysis successful?
    "name_error": int,               # Undefined names count
    "attribute_error": int,          # Invalid attribute access count
    "type_error": int,               # Invalid parameter count
    "module_not_found": int,         # Missing module count
    "total_libapi_errors": int,      # Sum of all error types
    "libapi_details": [              # Detailed error list
        {
            "type": str,             # Error type
            "module": str,           # Module name (if module_not_found)
            "object": str,           # Object name (if attribute_error)
            "attribute": str,        # Attribute name (if attribute_error)
            "function": str,         # Function name (if type_error)
            "invalid_arg": str,      # Invalid argument (if type_error)
            "line": int              # Line number
        }
    ]
}
```

### **Where to Observe Output**
1. **Per-dataset JSONL files**:
   - `Hallucination detection/static/LIB_API/libapi_ds1000.jsonl`
   - `Hallucination detection/static/LIB_API/libapi_humaneval.jsonl`
   - `Hallucination detection/static/LIB_API/libapi_mbpp.jsonl`

2. **Unified CSV summary**:
   - `Hallucination detection/static/LIB_API/libapi_summary.csv`

### **Example: View LIB_API Results**
```bash
# Find all module_not_found errors
grep '"module_not_found": [^0]' "Hallucination detection/static/LIB_API/libapi_ds1000.jsonl"
```

---

## 📁 Module 4: Dynamic Execution

### **Purpose**
Execute code with test cases and capture runtime behavior

### **Input**
- **Type**: Generated code + Test cases
- **Source Code**: Same generation CSV files
- **Test Cases**: From benchmark metadata

### **Output Structure**
```python
{
    "task_id": str,
    "status": str,                   # "passed", "failed", "error", etc.
    "error_type": str,               # Runtime error type
    "hallucination_subtype": str,    # Specific hallucination category
    "execution_time_ms": float,
    "test_results": [...],           # Individual test outcomes
    "traceback": str                 # Stack trace if error
}
```

### **Where to Observe Output**
1. **Per-dataset JSONL files**:
   - `Hallucination detection/dynamic/dynamic_ds1000.jsonl`
   - `Hallucination detection/dynamic/dynamic_humaneval.jsonl`
   - `Hallucination detection/dynamic/dynamic_mbpp.jsonl`

2. **Unified CSV summary**:
   - `Hallucination detection/dynamic/dynamic_summary.csv`

---

## 🔗 Module Integration: APR Input Builder

### **Purpose**
Combine all module outputs into unified APRInput format

### **Location**
`APR/input/builder.py`

### **Process**
```python
# 1. Load static analysis results (indexed by dataset + task_id)
static_index = _load_static_index(
    ast_path="Hallucination detection/static/AST/ast_summary.csv",
    cfg_path="Hallucination detection/static/CFG/cfg_summary.csv",
    lib_path="Hallucination detection/static/LIB_API/libapi_summary.csv"
)

# 2. Load dynamic results
dynamic_index = _load_dynamic_index({
    "DS1000": "Hallucination detection/dynamic/dynamic_ds1000.jsonl",
    "HumanEval": "Hallucination detection/dynamic/dynamic_humaneval.jsonl",
    "MBPP": "Hallucination detection/dynamic/dynamic_mbpp.jsonl"
})

# 3. For each task, merge all results
for source_dataset, task_id, row in generation_rows:
    key = (dataset, task_id)
    
    # Get results for this specific task
    ast_result = static_index[key]["ast"]
    cfg_result = static_index[key]["cfg"]
    lib_result = static_index[key]["lib"]
    dynamic_result = dynamic_index[key]
    
    # Convert to unified APRInput format
    apr_input = {
        "task_id": f"{dataset}_{task_id}",
        "generated_code": code,
        "static_ast": adapt_ast(ast_result),
        "static_cfg": adapt_cfg(cfg_result),
        "static_library_api": adapt_libapi(lib_result),
        "dynamic_analysis": adapt_dynamic(dynamic_result),
        # ... other fields
    }
```

### **Output**
- **File**: `APR/input/apr_input.jsonl`
- **Format**: One JSON object per line, each with complete module results

### **Run Builder**
```bash
python3 APR/build_apr_input_pipeline.py --output APR/input/apr_input.jsonl
```

---

## 🔍 Quick Reference: Finding Module Data

### For a specific task (e.g., DS0001 from DS1000):

1. **Original Generated Code**:
   ```bash
   # Look in: Code generation/Qwen/ds1k_gen.csv
   # Find row where task_id == "DS0001"
   # Column: "full_code"
   ```

2. **AST Result**:
   ```bash
   # Look in: Hallucination detection/static/AST/ast_ds1000.jsonl
   # Find line where "task_id": "DS0001"
   # OR: Check ast_summary.csv, filter by task_id
   ```

3. **CFG Result**:
   ```bash
   # Look in: Hallucination detection/static/CFG/cfg_ds1000.jsonl
   # Find line where "task_id": "DS0001"
   ```

4. **LIB_API Result**:
   ```bash
   # Look in: Hallucination detection/static/LIB_API/libapi_ds1000.jsonl
   # Find line where "task_id": "DS0001"
   ```

5. **Dynamic Result**:
   ```bash
   # Look in: Hallucination detection/dynamic/dynamic_ds1000.jsonl
   # Find line where "task_id": "DS0001"
   ```

6. **Unified APR Input**:
   ```bash
   # Look in: APR/input/apr_input.jsonl
   # Find line where "task_id": "DS-1000_DS0001"
   ```

---

## 📊 Data Files Quick Reference

| Module | Input File | Output Files |
|--------|-----------|--------------|
| **AST** | `Code generation/Qwen/{dataset}_gen.csv` | `Hallucination detection/static/AST/ast_summary.csv`<br>`Hallucination detection/static/AST/ast_{dataset}.jsonl` |
| **CFG** | Same as AST | `Hallucination detection/static/CFG/cfg_summary.csv`<br>`Hallucination detection/static/CFG/cfg_{dataset}.jsonl` |
| **LIB_API** | Same as AST | `Hallucination detection/static/LIB_API/libapi_summary.csv`<br>`Hallucination detection/static/LIB_API/libapi_{dataset}.jsonl` |
| **Dynamic** | Same as AST + test cases | `Hallucination detection/dynamic/dynamic_summary.csv`<br>`Hallucination detection/dynamic/dynamic_{dataset}.jsonl` |
| **APR Builder** | All above outputs | `APR/input/apr_input.jsonl` |

---

## 🛠️ Useful Commands

### View sample outputs:
```bash
# View first AST result
head -1 "Hallucination detection/static/AST/ast_ds1000.jsonl" | python3 -m json.tool

# Count errors by type
grep -o '"error_type": "[^"]*"' "Hallucination detection/static/AST/ast_summary.csv" | sort | uniq -c

# Find tasks with API errors
awk -F',' '$7 > 0' "Hallucination detection/static/LIB_API/libapi_summary.csv" | head

# View APR input sample
head -1 APR/input/apr_input.jsonl | python3 -m json.tool
```

---

## 💡 Key Takeaways

1. **All modules receive the same input**: Generated Python code string
2. **AST must succeed** for CFG to run
3. **Results are indexed** by `(dataset, task_id)` tuple
4. **Three output formats**: 
   - Per-dataset JSONL (detailed)
   - Summary CSV (all datasets)
   - Unified APR input (integrated)
5. **Data flow is unidirectional**: Generation → Static Analysis → Dynamic → APR Input

---

## 📞 Need More Info?

- **Module implementations**: Check `Hallucination detection/static/{AST,CFG,LIB_API}/`
- **Integration logic**: Check `APR/input/builder.py` and `adapters.py`
- **Schema definitions**: Check `APR/input/schema.py`
