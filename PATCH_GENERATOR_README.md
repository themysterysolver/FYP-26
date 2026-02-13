# Patch Generator Tool

## Overview

The patch generator tool creates error-marked code patches for visualization and analysis. It combines fault information with generated code to produce patches that highlight specific error locations.

## Output Format

The tool generates `patched_code.csv` with the following structure:

### Columns

1. **Original fault_information.csv fields:**
   - `dataset`: Dataset name (MBPP, DS1000, etc.)
   - `status`: Status of the code (hallucinated, passed, etc.)
   - `task_id`: Unique task identifier
   - `ast_info`: AST analysis information
   - `cfg_info`: Control flow graph analysis information
   - `lib_info`: Library API usage analysis information
   - `dynamic_info`: Dynamic execution analysis information

2. **New fields:**
   - `generated_code`: Full generated code from hallucination_master_table.csv
   - `patched_code`: Code snippet with error markers showing the fault location
   - `error_source`: Which analysis detected the error (ast/cfg/lib/dynamic)
   - `error_type`: Specific type of error detected
   - `error_line_start`: Starting line number of the error (1-indexed)
   - `error_line_end`: Ending line number of the error (1-indexed)

### Patch Format

Each `patched_code` entry shows:
- 1 line of context above the error
- `<<<< [ERROR START]` marker
- The erroneous code lines
- `[ERROR FINISH] >>>>` marker
- 1 line of context below the error

**Example (single line error):**
```
    # Calculate the start date for the window
<<<< [ERROR START]
    start_date = row['date'] - pd.Timedelta(weeks=X)
[ERROR FINISH] >>>>
    
```

**Example (multi-line error):**
```
<<<< [ERROR START]
def next_smallest_palindrome(num):
    def is_palindrome(n):
        return str(n) == str(n)[::-1]

    if num < 0:
        return None

    # Start from the next number after num
    num += 1

    while not is_palindrome(num):
        num += 1

    return num
[ERROR FINISH] >>>>
```

## Usage

### Running the Generator

```bash
cd /Users/abhinavh.parthiban/Documents/FYP-26
python3 patch_generator.py
```

### Output

- **Input rows:** 1,491 (from fault_information.csv)
- **Output rows:** 1,452 (some entries have multiple errors, creating separate rows)
- **Output file:** `patched_code.csv`

### Error Source Distribution

Based on the current dataset:
- **dynamic:** 793 patches (runtime errors)
- **lib:** 461 patches (library API errors)
- **cfg:** 122 patches (control flow errors)
- **ast:** 76 patches (syntax/AST errors)

## Error Type Processing

### 1. AST Info
- **Field used:** `value` (line number)
- **Format:** JSON with `{"type": "...", "value": line_num, ...}`
- **Result:** Single line patch

### 2. CFG Info
- **Fields used:** `start_line` and `end_line`
- **Format:** List of dicts `[{'type': '...', 'start_line': N, 'end_line': M}]`
- **Result:** Range patch (multiple lines)
- **Multiple errors:** Creates separate rows

### 3. Lib Info
- **Field used:** `line`
- **Format:** List of dicts `[{'type': '...', 'line': N}]`
- **Result:** Single line patch
- **Multiple errors:** Creates separate rows

### 4. Dynamic Info
- **Field used:** `line_no`
- **Format:** JSON with `{"error_type": "...", "line_no": "N", ...}`
- **Result:** Single line patch
- **Note:** Skips entries where `line_no` is empty or invalid

## Multiple Errors

When a single task has multiple errors detected by different analyzers:
- Each error gets its own row in the output
- All rows share the same `generated_code`
- Each row has a unique `patched_code` highlighting only that specific error

Example: Task DS1000 DS0004 has 2 errors:
1. AST error on line 5 (IndentationError)
2. Dynamic error on line 2 (IndentationError)

This creates 2 separate rows in `patched_code.csv`.

## Data Quality Notes

### Warnings
Some entries generate warnings about invalid line numbers. This occurs when:
- Error detection reports a line number that exceeds the code length
- Generated code is incomplete or truncated
- Syntax errors prevent proper code generation

These entries are skipped automatically.

### Missing Data
- 2 rows from fault_information.csv have no matching generated_code
- These rows are included in processing but produce no patches if error info is missing

## Visualization Use Case

The `patched_code.csv` file is designed for visualization tools that need to:
1. Show the specific location of detected errors
2. Display context around the error
3. Compare different error types
4. Analyze error patterns across datasets

The patch format is similar to git merge conflict markers, making it familiar and easy to parse.
