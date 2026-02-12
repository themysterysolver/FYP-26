# DS-KG Integration Demo

This directory contains a complete end-to-end demonstration of the DS-KG (Data Science Knowledge Graph) integration with the patch generation system.

## What This Demo Shows

The demo demonstrates how broken Python code with API errors can be automatically fixed using:

1. **Error Detection** - Static and dynamic analysis identifies the error
2. **Patch Generation** - Creates error markers in the code
3. **KG Query** - Queries the Knowledge Graph for relevant API documentation
4. **Prompt Building** - Constructs an LLM repair prompt with API context
5. **Code Repair** - Generates fixed code (mocked in this demo)
6. **Validation** - Validates the fix with test cases

## Files

- **`demo_kg_repair.py`** - Main demo script showing the complete integration flow
- **`run_demo.sh`** - Shell script runner with formatted output
- **`README.md`** - This file

## Running the Demo

### Option 1: Direct Python Execution

```bash
cd /path/to/FYP-26
python3 APR/examples/demo_kg_repair.py
```

### Option 2: Shell Script Runner

```bash
cd /path/to/FYP-26
bash APR/examples/run_demo.sh
```

## Example Output

```
============================================================
DS-KG + Patch Generation Demo
============================================================

1. BROKEN CODE:
------------------------------------------------------------
def calculate_mean(numbers):
    arr = np.array(numbers)
    return arr.mean()

2. ERROR DETECTION:
------------------------------------------------------------
   Status: UNDEFINED_NAME detected
   Variable: 'np' at line 2
   Suggestion: numpy

3. GENERATED PATCH:
------------------------------------------------------------
def calculate_mean(numbers):
<<<<<<< [ERROR START: UNDEFINED_NAME]
    arr = np.array(numbers)
=======
# Undefined: 'np', did you mean 'numpy'?
import numpy
>>>>>>> [ERROR END: UNDEFINED_NAME]
    return arr.mean()

4. KG CONTEXT EXTRACTION:
------------------------------------------------------------
   Loaded KG: numpy (288 entries)
   Queried for 'array' API
   Found 2 relevant API docs
     - numpy.array: array(object, dtype=None, *, copy=True, ...)
     - numpy.asanyarray: asanyarray(a, dtype=None, order=None, ...)

5. REPAIR PROMPT BUILT:
------------------------------------------------------------
   Prompt length: 635 characters
   Contains KG context: True

6. LLM REPAIR:
------------------------------------------------------------
import numpy as np

def calculate_mean(numbers):
    arr = np.array(numbers)
    return arr.mean()

7. VALIDATION:
------------------------------------------------------------
   ✓ All tests passed: 2/2

============================================================
✓ Demo completed successfully!
✓ Broken code was fixed and validated
============================================================
```

## Demo Scenario

**Broken Code**: Missing numpy import causing `NameError`

```python
def calculate_mean(numbers):
    arr = np.array(numbers)  # Error: np is not defined
    return arr.mean()
```

**Error Type**: `UNDEFINED_NAME`

**KG Context Provided**: 
- `numpy.array` API documentation
- Required/optional parameters
- Return type information

**Fixed Code**: Correct import added

```python
import numpy as np

def calculate_mean(numbers):
    arr = np.array(numbers)
    return arr.mean()
```

## Technical Flow

1. **APRInput Creation**: Mock input with static/dynamic analysis results
2. **PatchGenerator**: Creates hunks with error markers
3. **DSKGEngine**: Loads numpy KG (288 entries) and queries for 'array'
4. **build_repair_prompt()**: Assembles prompt with KG context
5. **Mock LLM**: Returns corrected code with proper import
6. **Validation**: Executes test cases (mock if numpy not installed)

## Integration Points

The demo showcases the integration between:

- `APR/DS-KG/engine.py` - KG query engine
- `APR/patch_generation/generator.py` - Patch generation
- `APR/patch_generation/kg_integration.py` - Error signature extraction & KG queries
- `APR/patch_generation/prompts.py` - Prompt building with KG context

## Notes

- **Mock LLM**: The demo uses a mock LLM response for reproducibility. In production, this would call a real LLM API (e.g., OpenAI, Anthropic, local model).

- **Mock Validation**: If numpy is not installed, the demo uses mock validation to show successful completion. With numpy installed, it actually executes the fixed code.

- **Extensibility**: The demo structure can be extended to test other error scenarios:
  - API_ERROR (deprecated APIs)
  - RUNTIME_ERROR (AttributeError, TypeError)
  - LOGIC_ERROR (wrong output)

## Requirements

- Python 3.8+
- APR module structure in place
- DS-KG JSON files (numpy, pandas, etc.)

Optional:
- numpy (for real validation instead of mock)

## Exit Codes

- `0` - Demo completed successfully
- `1` - Demo failed (check output for errors)
