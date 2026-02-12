# Repair Context Integration - Implementation Details

## Objective

Combine Qwen generation outputs and hallucination-detection outputs into a single repair-context dataset for downstream code-repair LLM usage, with mandatory fields:

- `error_type`
- `error_line_number`
- `error_stack_trace` (plus alias `error_stack_tract`)

## Artifacts Created

Under `APR/repair_context_integration/`:

- `build_repair_context.py` - merger pipeline script
- `repair_context_qwen.jsonl` - merged JSONL output
- `repair_context_qwen.csv` - merged CSV output
- `IMPLEMENTATION_DETAILS.md` - this document

## Inputs Used

### Generation CSVs

- `Code generation/Qwen/ds1k_gen.csv`
- `Code generation/Qwen/humaneval_gen.csv`
- `Code generation/Qwen/mbpp_gen.csv`

### Static JSONLs

- AST:
  - `Hallucination detection/static/AST/ast_ds1000.jsonl`
  - `Hallucination detection/static/AST/ast_humaneval.jsonl`
  - `Hallucination detection/static/AST/ast_mbpp.jsonl`
- CFG:
  - `Hallucination detection/static/CFG/cfg_ds1000.jsonl`
  - `Hallucination detection/static/CFG/cfg_humaneval.jsonl`
  - `Hallucination detection/static/CFG/cfg_mbpp.jsonl`
- LIB_API:
  - `Hallucination detection/static/LIB_API/libapi_ds1000.jsonl`
  - `Hallucination detection/static/LIB_API/libapi_humaneval.jsonl`
  - `Hallucination detection/static/LIB_API/libapi_mbpp.jsonl`

### Dynamic JSONLs

- `Hallucination detection/dynamic/dynamic_ds1000.jsonl`
- `Hallucination detection/dynamic/dynamic_humaneval.jsonl`
- `Hallucination detection/dynamic/dynamic_mbpp.jsonl`

## Join and Normalization Strategy

The script builds canonical keys per dataset from `task_id`:

- DS1000 -> `DS####` (e.g., `4` / `DS0004` / `DS4` => `DS0004`)
- HumanEval -> `HumanEval/N` (e.g., `0`, `HumanEval/0` => `HumanEval/0`)
- MBPP -> numeric string (e.g., `602`, `"602"` => `602`)

Join key:

- `(dataset, task_id_normalized)`

Merge direction:

- generation rows are authoritative (left-join diagnostics onto generation data)
- all original generation columns are preserved with prefix `gen_`

## Required Field Derivation

### `error_type`

Priority:

1. dynamic signals (`dynamic.error_type`, and for logical failures subtype when informative)
2. AST `error_type`
3. LIB_API dominant error (details first, else max count among module/name/attribute/type errors)
4. CFG (`missing_return`, then `unreachable_code`)
5. fallback `none`

Also emitted:

- `error_source` to indicate the selected source (`dynamic`, `ast`, `libapi`, `cfg`, `none`)

### `error_line_number`

Priority:

1. AST `line`
2. first `libapi_details[].line`
3. first `cfg_details[].start_line` (or `line`)
4. fallback `null`

### `error_stack_trace`

Source is dynamic output:

1. if `failures` list exists and non-empty, serialize first failure (`test_id`, `type`, `subtype`, `message`, `input`, `expected`, `actual`, `source`)
2. else use `stderr` if present
3. else use `stdout` if present
4. fallback `null`

Alias emitted for compatibility with request typo:

- `error_stack_tract` = same value as `error_stack_trace`

## Additional Context Fields Emitted

- `generated_code`
- `dynamic_status`, `dynamic_error_type`, `dynamic_hallucination_subtype`
- `ast_error_type`, `ast_line`, `ast_message`
- `libapi_total_errors`, `cfg_missing_return`, `cfg_unreachable_code`
- raw detail payloads:
  - `raw_dynamic_failures`
  - `raw_ast_details`
  - `raw_cfg_details`
  - `raw_libapi_details`

## Execution Notes

Because system Python is externally managed, the script was executed with project virtualenv:

1. create/use `.venv`
2. install requirements from `requirements.txt`
3. run:

`/Users/abhinavh.parthiban/Documents/FYP-26/.venv/bin/python /Users/abhinavh.parthiban/Documents/FYP-26/APR/repair_context_integration/build_repair_context.py`

## Validation Results

### Output Summary

- Total rows: `1491`
- Output files:
  - `APR/repair_context_integration/repair_context_qwen.jsonl`
  - `APR/repair_context_integration/repair_context_qwen.csv`

### Row Parity Check

Generation vs merged:

- DS1000: `1000` vs `1000`
- HumanEval: `164` vs `164`
- MBPP: `327` vs `327`

### Null Rates for Required Fields

- `error_type`: `0.0000`
- `error_line_number`: `0.7036`
- `error_stack_trace`: `0.8940`

## Known Limitations

- High null rate for `error_stack_trace` is expected when dynamic output has `no_tests` or no runtime failure payload.
- `error_line_number` depends on static analyzers exposing line metadata; many logical/runtime-only failures have no static line.
- Dynamic traces are currently sourced from existing `dynamic_*.jsonl`; no dynamic rerun with enhanced traceback capture was performed in this task.
