# Module I/O Cheat Sheet

## Quick Answer

**Q: What is the input to each module (AST, CFG, LIB_API)?**  
**A:** All modules receive the **same input**: Generated Python code as a string.

**Q: Where do I find this input?**  
**A:** `Code generation/Qwen/{dataset}_gen.csv` → Column: `full_code` (DS1000) or `GENERATED_CODE` (HumanEval/MBPP)

**Q: Where do I see the outputs?**  
**A:** See table below ⬇️

---

## Module I/O Reference Table

| Module | Input | Output Location | Key Output Fields |
|--------|-------|-----------------|-------------------|
| **AST** | Code string | `Hallucination detection/static/AST/`<br>• `ast_{dataset}.jsonl`<br>• `ast_summary.csv` | • `ast_parsed` (bool)<br>• `syntax_error` (0/1)<br>• `error_type` (str)<br>• `line` (int) |
| **CFG** | Code string<br>(only if AST passes) | `Hallucination detection/static/CFG/`<br>• `cfg_{dataset}.jsonl`<br>• `cfg_summary.csv` | • `cfg_analyzed` (bool)<br>• `unreachable_code` (int)<br>• `missing_return` (int) |
| **LIB_API** | Code string | `Hallucination detection/static/LIB_API/`<br>• `libapi_{dataset}.jsonl`<br>• `libapi_summary.csv` | • `total_libapi_errors` (int)<br>• `attribute_error` (int)<br>• `module_not_found` (int) |
| **Dynamic** | Code + Tests | `Hallucination detection/dynamic/`<br>• `dynamic_{dataset}.jsonl`<br>• `dynamic_summary.csv` | • `status` (str)<br>• `hallucination_subtype` (str)<br>• `error_type` (str) |

---

## Quick Commands

### View data for specific task (e.g., DS0001 from DS1000):

```bash
# Use the provided shell script (easiest way)
./view_task_data.sh DS0001 DS1000

# Or manually:
grep '"task_id": "DS0001"' "Hallucination detection/static/AST/ast_ds1000.jsonl" | python3 -m json.tool
grep '"task_id": "DS0001"' "Hallucination detection/static/CFG/cfg_ds1000.jsonl" | python3 -m json.tool
grep '"task_id": "DS0001"' "Hallucination detection/static/LIB_API/libapi_ds1000.jsonl" | python3 -m json.tool
```

### Find tasks with errors:

```bash
# Syntax errors
grep '"syntax_error": 1' "Hallucination detection/static/AST/ast_ds1000.jsonl"

# API errors
grep '"total_libapi_errors": [^0]' "Hallucination detection/static/LIB_API/libapi_ds1000.jsonl"

# Control flow issues
grep '"unreachable_code": [^0]' "Hallucination detection/static/CFG/cfg_ds1000.jsonl"
```

---

## Module Function Signatures

```python
# AST Module
from ast_analysis import analyze_ast
result = analyze_ast(code: str) -> dict

# CFG Module  
from cfg_analysis import analyze_cfg
result = analyze_cfg(code: str) -> dict

# LIB_API Module
from library_api import analyze_library_api
result = analyze_library_api(code: str) -> dict
```

---

## Data Flow Diagram

```
                 GENERATED CODE
                       ↓
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
      AST            CFG          LIB_API
        ↓              ↓              ↓
    ast_*.jsonl   cfg_*.jsonl   libapi_*.jsonl
        └──────────────┼──────────────┘
                       ↓
              APR Input Builder
                       ↓
              apr_input.jsonl
```

---

## File Path Templates

Replace `{dataset}` with: `ds1000`, `humaneval`, or `mbpp`

```
Input:
  Code generation/Qwen/{dataset}_gen.csv

Outputs:
  Hallucination detection/static/AST/ast_{dataset}.jsonl
  Hallucination detection/static/CFG/cfg_{dataset}.jsonl
  Hallucination detection/static/LIB_API/libapi_{dataset}.jsonl
  Hallucination detection/dynamic/dynamic_{dataset}.jsonl

Unified:
  APR/input/apr_input.jsonl
```

---

## Example Output Structures

### AST Output
```json
{
  "ast_parsed": true,
  "syntax_error": 0,
  "error_type": null,
  "line": null
}
```

### CFG Output
```json
{
  "cfg_analyzed": true,
  "unreachable_code": 0,
  "missing_return": 0
}
```

### LIB_API Output
```json
{
  "libapi_analyzed": true,
  "total_libapi_errors": 1,
  "attribute_error": 1,
  "libapi_details": [
    {"type": "attribute_error", "object": "pd", "attribute": "DataFram", "line": 5}
  ]
}
```

---

## Quick Facts

✅ **Same Input**: All modules analyze the same generated code  
✅ **Independent**: Modules run independently (except CFG needs AST to pass)  
✅ **Indexed**: Results indexed by `(dataset, task_id)` for easy lookup  
✅ **Two Formats**: JSONL (detailed) and CSV (summary)  
✅ **Integration**: All results merged in `APR/input/apr_input.jsonl`

---

## Tools & Resources

| Resource | Description |
|----------|-------------|
| `MODULE_DATA_FLOW.md` | Complete documentation with examples |
| `README_MODULE_INSPECTION.md` | How-to guide with practical examples |
| `view_task_data.sh` | Shell script to view all module data for a task |
| `example_access_module_data.py` | Python examples showing module usage |
| `MODULE_CHEATSHEET.md` | This file - quick reference |

---

## Need Help?

1. **Read the docs**: Start with `README_MODULE_INSPECTION.md`
2. **Use the script**: `./view_task_data.sh <task_id> <dataset>`
3. **Run examples**: `python3 example_access_module_data.py`
4. **Check module code**: Look in `Hallucination detection/static/{AST,CFG,LIB_API}/`
