# APR Implementation Plan (PHASE_1)

## Current state

- **Pipeline**: `run_full_hallucination_pipeline` returns `fault_information`, `patch`, and `error_types` (plus existing keys). No KeyError in repair loop.
- **APR (all types)**: `get_repair_category` returns syntax, attribute, type, name, key, assertion, timeout, other, or skip. One prompt per category. `fix_code` uses `build_apr_prompt` for all categories.
- **Driver**: `repair_with_max_passes` passes `row` and `error_types` into `fix_code`. ERROR DATASET (IDs from extract.py) filters tasks to failed-only.
- **Token economy**: We never pass full `dynamic_info` to prompts. Instead we use `extract_error_info_for_prompt` (error_type, error_message, line_number only) and `extract_failing_test_cases_for_prompt` (parsed failing tests only).

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

## Dynamic analysis schema (reference)

- **Input**: row, dataset_type, task_id, generated_code
- **Output**: status, error_type, error_message, line_number, test_case, testcase_output, generated_code, dataset, task_id
- **Main function**: `run_dynamic_driver_dynamic_analysis`

## Error and test-case extraction (token economy)

We do **not** pass the full `dynamic_info` to prompts (avoids token waste and hallucinations). Instead:

### `extract_error_info_for_prompt(fault_information)`

Returns only: `error_type`, `error_message`, `line_number`. Used by attribute, type, name, key, timeout, other prompts.

### `extract_failing_test_cases_for_prompt(fault_information, max_cases=10)`

- Parses `test_case` from dynamic_info: list of `[input_str, expected_str, actual_str]` per test.
- Filters to **failing** cases only (where `actual_str != expected_str`). Passed cases are skipped.
- Returns formatted strings: `"For this INPUT {input} we get output {actual} but we need this {expected}"`
- Used by `build_prompt_assertion`.

### Internal: `_parse_dynamic_info(fault_information)`

Parses `dynamic_info` from fault_information (handles dict or JSON string). Used only inside the extractors; never passed to prompts.

## Files

- **Notebook**: [Pipeline construction/PHASE_1.ipynb](PHASE_1.ipynb) – single APR cell (cell 68) contains classifier, extractors, all prompt builders, dispatcher, and `fix_code`.
