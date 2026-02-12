# Dynamic Code Hallucination Detection

This module runs **dynamic** detection on generated code: it executes code in a sandboxed subprocess, runs dataset-specific test oracles, and classifies failures (wrong output, exceptions, timeouts) with repairability assessment.
It now includes a standalone BVA/ECP test-generation framework that augments dataset tests with derived boundary-value and equivalence-class checks.

For full design (architecture diagram, handling per hallucination type, implementation steps), see **[PLAN.md](PLAN.md)**.

## Pipeline steps

1. **Code extraction** — Strip markdown fences and extract executable Python.
2. **Spec extraction + test generation** — Build normalized specs from each row, infer domains, and generate BVA/ECP tests where applicable.
3. **Test harness injection** — Build a harness that runs original + generated tests and prints JSON results.
4. **Sandbox execution** — Run code + harness in a subprocess with a configurable timeout (default 5s). Outcomes: success, timeout, resource_error (OOM), crash, parse_error.
5. **Oracle and handling** — Compare actual vs expected; classify failures (wrong_output, exception subtypes); apply handling (e.g. `can_repair: false`, `suggestion: "human review"` for timeout).

## Dataset support

| Dataset    | Support   | Test source                    |
|-----------|-----------|---------------------------------|
| **MBPP**  | Full      | `test_list`, `test_imports`, generated BVA/ECP |
| **HumanEval** | Full  | `test`, `entry_point`, generated BVA/ECP |
| **DS1000**| Oracle-enabled | `code_context` (`generate_test_case`, `exec_test`) |

## How to run

From the **project root** with venv activated:

```bash
python "Hallucination detection/dynamic/dynamic_detection.py"
```

Or from this directory:

```bash
cd "Hallucination detection/dynamic"
python dynamic_detection.py
```

Optional: enable flakiness check (run each sample 3× and use majority vote):

```python
from dynamic_detection import run_dynamic_pipeline
run_dynamic_pipeline(timeout=5, run_flakiness_check=True, enable_generated_tests=True)
```

## Outputs

- **dynamic_mbpp.jsonl**, **dynamic_humaneval.jsonl**, **dynamic_ds1000.jsonl** — One JSON object per sample (dataset, task_id, valid, error_type, hallucination_subtype, failures, can_repair, flaky, oracle_confidence, etc.).
- **dynamic_summary.csv** — Summary rows (dataset, task_id, valid, error_type, hallucination_subtype, can_repair, flaky, failure_count, bva/ecp aggregates, oracle_confidence).

Input CSVs are read from `Code generation/Qwen/` (same as static modules).
