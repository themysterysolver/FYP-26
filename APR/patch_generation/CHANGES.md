# Hybrid Repair Prompt - Changes Summary

## Overview

Implemented a **hybrid repair prompt approach** that automatically selects the best prompt format based on error type:
- **Simple prompt** for syntax/runtime/name/API errors (error-message + error-line)
- **Rich prompt** for logic errors (TEST/EXPECTED/ACTUAL)

## What Changed

### 1. Traceback Wiring (`APR/input/adapters.py`)

**BEFORE:**
```python
failure_details = {
    "failing_test_id": failing_test_id,
    "exception_type": exc_type,
    "exception_message": exc_msg,
    "traceback": None,  # Always None
    "expected_vs_actual": expected_vs_actual,
}
```

**AFTER:**
```python
# Parse traceback from stderr when available (crash, resource_error)
traceback_lines = None
stderr = record.get("stderr")
if stderr and isinstance(stderr, str) and stderr.strip():
    traceback_lines = [line for line in stderr.strip().split("\n") if line.strip()]

failure_details = {
    "failing_test_id": failing_test_id,
    "exception_type": exc_type,
    "exception_message": exc_msg,
    "traceback": traceback_lines,  # Now populated from stderr
    "expected_vs_actual": expected_vs_actual,
}
```

**Impact:** Runtime errors now get accurate line numbers from traceback, making the simple prompt effective.

---

### 2. Prompt Templates (`APR/patch_generation/prompts.py`)

**ADDED:** New simple prompt template

```python
REPAIR_PROMPT_ERROR_LINE = """Fix the error in the code below.

## Error
Line {error_line}: {error_message}

## Problem
{problem_description}

## Code with Error Marked
```python
{patched_code}
```

## Instructions
- Fix the marked block at line {error_line}
- Remove all marker lines
- Return the corrected code
"""
```

**ADDED:** Helper functions for template selection

```python
def _use_simple_prompt(patch: GeneratedPatch) -> bool:
    """Return True if all hunks are simple (non-logic) error types."""
    hunks = patch.get("hunks") or []
    return all(hunk.get("error_type") in SIMPLE_ERROR_TYPES for hunk in hunks)

def _get_primary_error_for_simple(apr_input, patch) -> tuple[int, str]:
    """Extract error line and message from first hunk."""
    # Returns (line_number, error_message)
```

**MODIFIED:** `build_repair_prompt()` now auto-selects template

```python
def build_repair_prompt(apr_input, patch, template=None, auto_select=True):
    """Auto-select SIMPLE vs RICH template based on error types."""
    if template is None and auto_select:
        if _use_simple_prompt(patch):
            template = REPAIR_PROMPT_ERROR_LINE  # Simple for syntax/runtime/name/API
        else:
            template = REPAIR_PROMPT_TEMPLATE     # Rich for logic errors
```

---

### 3. Demo (`APR/patch_generation/demo.py`)

**BEFORE:** Single example (logic error only)

**AFTER:** Two examples showcasing both prompt types

```python
def _syntax_error_example():
    """Syntax error - uses SIMPLE prompt"""
    
def _logic_error_example():
    """Logic error - uses RICH prompt"""

def main():
    # Run both examples and show prompt type for each
    _run_example("Syntax Error (uses SIMPLE prompt)", ...)
    _run_example("Logic Error (uses RICH prompt)", ...)
```

---

### 4. Documentation (`APR/patch_generation/README.md` - NEW)

Complete README with:
- Purpose and hybrid approach explanation
- Architecture diagram (components and data flow)
- Detailed component descriptions
- Usage examples
- Marker format specification
- Key design decisions

---

## Demo Output Comparison

### Example 1: Syntax Error → SIMPLE Prompt

**Prompt type:** `SIMPLE (error-line)`

**Prompt format:**
```
Fix the error in the code below.

## Error
Line 1: Fix: invalid syntax. Perhaps you forgot a comma?

## Problem
Calculate the sum of numbers in a list.

## Code with Error Marked
[marked code block]

## Instructions
- Fix the marked block at line 1
- Remove all marker lines
- Return the corrected code
```

**Key features:**
- Direct error message at top
- No verbose test case listings
- Clear line number reference
- Short and focused (659 chars total)

---

### Example 2: Logic Error → RICH Prompt

**Prompt type:** `RICH (test I/O)`

**Prompt format:**
```
Fix the code by resolving all [ERROR START/END] blocks.

## Problem
Return the maximum value in the list.

## Function Signature
def find_max(numbers):

## Code with Errors Marked
def find_max(numbers):
    max_val = 0
    for n in numbers:
<<<<<<< [ERROR START: LOGIC_ERROR]
        if n > max_val:
=======
# TEST: find_max([-5, -2, -10])
# EXPECTED: -2
# ACTUAL: 0
# DIFF: Expected -2, got 0
pass  # TODO: Fix logic_error
>>>>>>> [ERROR END: LOGIC_ERROR]

## Instructions
- Replace each block with correct code
- Remove all markers
- Ensure the fixed code passes: [test case summary]
```

**Key features:**
- Full context with problem and function signature
- TEST/EXPECTED/ACTUAL in marker block
- Test case summary at bottom
- Complete information for logic debugging (786 chars total)

---

## Benefits

### 1. Better for Syntax/Runtime/Name Errors
- **Before:** Verbose prompt with test cases (not relevant for syntax errors)
- **After:** Concise prompt with exact error message and line number
- **Impact:** LLM gets exactly what it needs: "Line 1: invalid syntax" without extra noise

### 2. Accurate Localization
- **Before:** `traceback` always `None`, used middle-of-file estimate
- **After:** `traceback` populated from stderr, actual line from Python traceback
- **Impact:** Runtime error hunks point to the real failing line

### 3. Optimal for Logic Errors
- **Before:** Same verbose format (already good for logic)
- **After:** Same rich format preserved for logic errors
- **Impact:** Logic errors still get TEST/EXPECTED/ACTUAL context they need

### 4. Automatic Selection
- **Before:** One prompt format for all errors
- **After:** Auto-selects based on hunk error types
- **Impact:** No manual template selection needed; best format chosen automatically

---

## Files Modified

1. `APR/input/adapters.py` - Wire traceback from stderr
2. `APR/patch_generation/prompts.py` - Add simple template and auto-selection
3. `APR/patch_generation/demo.py` - Showcase both prompt types
4. `APR/patch_generation/README.md` - NEW: Architecture and usage docs
5. `APR/patch_generation/CHANGES.md` - NEW: This file

---

## Testing

Run the demo to see both prompt types:

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26
python3 -m APR.patch_generation.demo
```

**Output shows:**
- ✅ Syntax error → SIMPLE prompt (short, focused)
- ✅ Logic error → RICH prompt (with TEST/EXPECTED/ACTUAL)
- ✅ Both patches validate successfully
- ✅ Clear difference in prompt length and structure
