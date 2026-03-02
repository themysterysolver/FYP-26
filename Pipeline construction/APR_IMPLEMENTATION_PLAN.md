# APR Implementation Plan (PHASE_1)

## Current state

- **Pipeline**: `run_full_hallucination_pipeline` returns `fault_information`, `patch`, and `error_types` (plus existing keys). No KeyError in repair loop.
- **APR (syntax only)**: `get_repair_category` returns `"syntax"` or `"skip"`. `build_prompt_syntax` builds messages for syntax/indentation fix. `fix_code` attempts repair only when category is `"syntax"`; otherwise returns code unchanged.
- **Driver**: `repair_with_max_passes` passes `row` and `error_types` into `fix_code`. ERROR DATASET (IDs from extract.py) filters tasks to failed-only.

## Build plan (one prompt per error type)

| Step | Item | Status |
|------|------|--------|
| 1 | **Syntax** – `get_repair_category` + `build_prompt_syntax` + `fix_code` (syntax branch) | Done |
| 2 | **Classifier** – Expand `get_repair_category` to return: syntax, attribute, type, name, key, assertion, timeout, other | Done |
| 3 | **Attribute** – `build_prompt_attribute` (wrong/missing attribute, deprecated API) | Done |
| 4 | **Type** – `build_prompt_type` (wrong signature, keyword arg) | Done |
| 5 | **Name** – `build_prompt_name` (undefined name, missing import) | Done |
| 6 | **Key** – `build_prompt_key` (missing dict/DataFrame key) | Done |
| 7 | **Assertion** – `build_prompt_assertion` (test case info, fix logic only) | Done |
| 8 | **Timeout** – `build_prompt_timeout` (infinite loop, excessive work) | Done |
| 9 | **Other** – `build_prompt_other` (fallback for ValueError, UnboundLocalError, etc.) | Done |
| 10 | **Dispatcher** – `build_apr_prompt(...)` → calls the right builder | Done |
| 11 | **fix_code** – Use `build_apr_prompt` for all categories; attempt repair for any category | Done |

## Classification order (first match wins)

1. SyntaxError, IndentationError → **syntax**
2. AttributeError, attribute_error → **attribute**
3. TypeError → **type**
4. NameError, name_error → **name**
5. KeyError → **key**
6. AssertionError, WrongAnswer → **assertion**
7. TimeoutError → **timeout**
8. Everything else → **other**

## Data flow

- **Inputs**: `patched_code`, `fault_information` (ast_info, dynamic_info, lib_info), `original_question` (from row), `error_types` (from pipeline result).
- **Classifier**: Parse `error_types` (comma-separated); normalize type name; return category.
- **Dispatcher**: `build_apr_prompt` → `get_repair_category` → one of `build_prompt_syntax`, `build_prompt_attribute`, … `build_prompt_other`.
- **fix_code**: If category is skip (empty), return code unchanged. Else: messages = `build_apr_prompt(...)`; raw = `generate_code(messages)`; fixed = `extract_python_code_humaneval(raw)`; return fixed or generated_code.

## Files

- **Notebook**: [Pipeline construction/PHASE_1.ipynb](PHASE_1.ipynb) – single APR cell (cell 68) contains classifier, all prompt builders, dispatcher, and `fix_code`.
