# Error Message Mismatch Analysis

**Date:** February 13, 2026  
**Comparison:** `dynamic_execution_results.csv` vs `hallucination_master_table.csv`

## Summary

Found **73 mismatches** between the two CSV files when comparing error messages for the same task IDs.

## Types of Mismatches

### 1. Error Message Format Differences (Most Common)
- **Pattern:** `<string>` vs `<unknown>` in error messages
- **Example:**
  - Exec: `expected an indented block after function definition on line 4 (<string>, line 6)`
  - Master: `expected an indented block after function definition on line 4 (<unknown>, line 5)`
- **Count:** ~30+ instances
- **Cause:** Different execution contexts (dynamic execution uses `<string>`, static analysis uses `<unknown>`)

### 2. Line Number Differences
- **Pattern:** Line numbers differ by 1-2 lines
- **Example:** Exec reports line 6, Master reports line 5
- **Cause:** Different ways of counting lines in the execution context (with/without wrapper code)

### 3. Completely Different Errors (Same Task)
These are more serious discrepancies where the actual error type differs:

| Task ID | Dynamic Execution Error | Master Table Error | Impact |
|---------|------------------------|-------------------|--------|
| DS0063 | `Invalid value '1' for dtype 'str'...` | `expected an indented block...` | Different error detected |
| DS0120 | `read_csv() got an unexpected keyword argument 'delim_whitespace'` | `expected an indented block...` | Library version difference (pandas) |
| DS0183 | `module 'numpy' has no attribute 'NAN'` | `expected an indented block...` | Library version difference (numpy) |
| DS0204 | `Invalid value '3.5' for dtype 'int64'` | `expected an indented block...` | Different error priority |
| DS0222 | `StringMethods.rsplit() takes from 1 to 2 positional arguments but 3 were given` | `expected an indented block...` | Library API change |
| DS0372 | `No module named 'scipy'` | `expected an indented block...` | Missing dependency |
| DS0397 | `No module named 'scipy'` | `expected an indented block...` | Missing dependency |
| DS0447 | `No module named 'scipy'` | `expected an indented block...` | Missing dependency |

## Root Causes

1. **Execution Context Differences:**
   - Dynamic execution wraps code in `<string>` context
   - Static analysis (master table) uses `<unknown>` placeholder
   - Line numbers get offset due to wrapper code

2. **Library Version Differences:**
   - `pandas.read_csv()`: `delim_whitespace` parameter removed in newer versions
   - `numpy.NAN` vs `numpy.nan`: API standardization
   - String method signatures changed between pandas versions

3. **Error Detection Order:**
   - Static analysis (AST parsing) catches syntax errors first
   - Dynamic execution may hit runtime errors before syntax issues surface
   - Example: Missing scipy imports cause runtime ImportError instead of catching syntax issues

4. **Environment Differences:**
   - Dynamic execution runs in actual Python environment
   - Master table may use different analysis tools or library versions

## Recommendations

### For Consistency:
1. **Normalize error messages** by replacing `<string>` with `<unknown>` for comparison purposes
2. **Adjust line numbers** by accounting for wrapper code offset
3. **Re-run dynamic execution** with same library versions used for master table generation
4. **Install missing dependencies** (scipy) for complete testing

### For Future Analysis:
1. Store library versions alongside error messages
2. Use consistent execution contexts for both dynamic and static analysis
3. Implement error message normalization layer for cross-comparison
4. Document which errors take precedence (syntax vs runtime)

## Files Compared

- **Source 1:** `Hallucination detection/dynamic/dynamic_execution_results.csv` (30,969 rows)
- **Source 2:** `APR/ANALYSIS/hallucination_master_table.csv` (22,429 rows)
- **Comparison Script:** `compare_errors.py`

## Next Steps

1. ✅ Install dependencies locally (pandas, numpy, matplotlib)
2. ⚠️ Consider installing scipy for complete coverage
3. 🔄 Optionally re-run dynamic_execution.py to update results with current environment
4. 📊 Update master table with normalized error messages if needed
