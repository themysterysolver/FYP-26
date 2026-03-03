# Error-Type Extraction Plan

## Purpose

Extract task IDs **by error type** from the three pipeline CSVs so you can run `main_driver` **for each error type alone** and measure mitigation per category.

## Inputs

- [Pipeline construction/AST+DYNMAIC+LIB_API/ds1000_pipeline_output.csv](AST+DYNMAIC+LIB_API/ds1000_pipeline_output.csv)
- [Pipeline construction/AST+DYNMAIC+LIB_API/humaneval_pipeline_output.csv](AST+DYNMAIC+LIB_API/humaneval_pipeline_output.csv)
- [Pipeline construction/AST+DYNMAIC+LIB_API/mbpp_pipeline_output.csv](AST+DYNMAIC+LIB_API/mbpp_pipeline_output.csv)

## Scripts

### 1. extract.py (existing)

- Filters rows where `status == "hallucinated"`
- Outputs `output.py` with: `task_id_ds1000`, `task_id_humaneval`, `task_id_mbpp` (all hallucinated IDs)

### 2. extract_by_error_type.py (new)

- Filters rows where `status == "hallucinated"`
- Parses `error_types` column (e.g. `"ast: SyntaxError"`, `"dynamic: AttributeError"`)
- Maps each raw type to category: syntax, attribute, type, name, key, assertion, timeout, other
- **If a task has multiple error types, it appears in multiple lists**
- Outputs [AST+DYNMAIC+LIB_API/error_type_ids.py](AST+DYNMAIC+LIB_API/error_type_ids.py) with:

```python
ERROR_TYPE_IDS = {
    "syntax":    {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "attribute": {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "type":      {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "name":      {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "key":       {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "assertion": {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "timeout":   {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
    "other":     {"ds1000": [...], "humaneval": [...], "mbpp": [...]},
}
```

**How to run:**
```bash
cd Pipeline construction/AST+DYNMAIC+LIB_API
python extract_by_error_type.py
```

## Usage in PHASE_1

### main_driver(error_type_filter=None)

- **`error_type_filter=None`** (default): Use existing `df_humaneval_f`, `df_mbpp_f`, `df_ds1k_f` (all hallucinated tasks)
- **`error_type_filter="syntax"`**: Use only task IDs that have syntax errors (from `ERROR_TYPE_IDS["syntax"]`)
- **`error_type_filter="attribute"`**, `"type"`, `"name"`, `"key"`, `"assertion"`, `"timeout"`, `"other"`**: Same idea

### Example runs

```python
# Test syntax repair alone
main_driver(max_passes=3, error_type_filter="syntax")

# Test assertion repair alone
main_driver(max_passes=3, error_type_filter="assertion")

# Test all hallucinated (default)
main_driver(max_passes=3)
```

## Workflow

1. Run `extract_by_error_type.py` to regenerate `error_type_ids.py` (after pipeline CSVs change)
2. In PHASE_1, ensure ERROR_TYPE_IDS is loaded (from error_type_ids.py)
3. Call `main_driver(error_type_filter="syntax")` (or other category) to test that error type alone
