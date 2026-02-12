# Data Column Reference

## Issue Fixed

The notebook code was using incorrect column names. This has been corrected.

## Actual Column Names in Your CSV Files

### Dynamic Analysis (`dynamic_summary.csv`)

**Actual columns:**
- `dataset` - Dataset name (MBPP, HumanEval, DS-1000)
- `task_id` - Unique task identifier
- `valid` - Boolean, whether the output is valid
- `error_type` - Type of error detected
- `hallucination_subtype` - Specific hallucination type
  - Values: `timeout`, `crash`, `wrong_output`, etc.
- `can_repair` - Boolean, whether automatic repair is possible
- `flaky` - Boolean, whether test is flaky
- `failure_count` - Number of failures
- `bva_total` - Total BVA tests
- `ecp_total` - Total ECP tests
- `bva_failures` - BVA test failures
- `ecp_failures` - ECP test failures
- `oracle_confidence` - Confidence level

**Fixed mapping:**
- OLD: `dynamic_df['status']`
- NEW: `dynamic_df['hallucination_subtype']`

### AST Analysis (`ast_summary.csv`)

**Actual columns:**
- `dataset` - Dataset name
- `task_id` - Task identifier
- `ast_parsed` - Boolean, whether AST parsing succeeded
- `syntax_error` - Boolean, syntax error present
- `indentation_error` - Boolean, indentation error present
- `structural_error` - Boolean, structural error present
- `error_type` - Type of error (e.g., 'NameError', 'SyntaxError')
- `line` - Line number of error
- `message` - Error message
- `structural_details` - Details about structural issues

**Usage:**
```python
# Check for syntax errors
syntax_count = ast_df['syntax_error'].sum()

# Check for specific error types
name_errors = (ast_df['error_type'] == 'NameError').sum()
```

### CFG Analysis (`cfg_summary.csv`)

**Actual columns:**
- `dataset` - Dataset name
- `task_id` - Task identifier
- `cfg_analyzed` - Boolean, whether CFG analysis succeeded
- `unreachable_code` - Count of unreachable code blocks
- `missing_return` - Count of missing return statements
- `cfg_details` - Detailed CFG information

**Usage:**
```python
# Count unreachable code
unreachable_total = cfg_df['unreachable_code'].sum()

# Count missing returns
missing_returns = cfg_df['missing_return'].sum()
```

### LIB_API Analysis (`libapi_summary.csv`)

**Actual columns:**
- `dataset` - Dataset name
- `task_id` - Task identifier
- `libapi_analyzed` - Boolean, analysis completed
- `name_error` - Count of name errors
- `attribute_error` - Count of attribute errors
- `type_error` - Count of type errors
- `module_not_found` - Count of missing modules
- `total_libapi_errors` - Total API errors
- `libapi_details` - Detailed error information

**Usage:**
```python
# Total API errors
api_errors = libapi_df['total_libapi_errors'].sum()
```

## What Was Fixed in the Notebook

### Cell 6: `generate_statistics_dashboard()`

**Before:**
```python
stats['dynamic_analysis']['timeouts'] = int((dynamic_df['status'] == 'timeout').sum())
stats['dynamic_analysis']['crashes'] = int((dynamic_df['status'] == 'crash').sum())
```

**After:**
```python
if 'hallucination_subtype' in dynamic_df.columns:
    stats['dynamic_analysis']['timeouts'] = int((dynamic_df['hallucination_subtype'] == 'timeout').sum())
    stats['dynamic_analysis']['crashes'] = int((dynamic_df['hallucination_subtype'] == 'crash').sum())
    stats['dynamic_analysis']['wrong_output'] = int((dynamic_df['hallucination_subtype'] == 'wrong_output').sum())
```

### Cell 85: Error counts visualization

**Fixed:** Uses `hallucination_subtype` with column existence check

## Testing the Fix

Run this in the notebook to verify:

```python
# Check what columns are actually available
print("Dynamic columns:", dynamic_df.columns.tolist())
print("AST columns:", ast_df.columns.tolist())
print("CFG columns:", cfg_df.columns.tolist())
print("LIB_API columns:", libapi_df.columns.tolist())

# Test statistics generation
stats = generate_statistics_dashboard()
print(stats)
```

## Why This Happened

The notebook was initially written based on expected schema, but your actual CSV files use different column names. The fixes add:

1. **Column existence checks** - Prevents KeyErrors
2. **Correct column names** - Uses actual column names from your data
3. **Graceful degradation** - Code works even if columns are missing

## Summary of Changes

- ✅ Fixed `generate_statistics_dashboard()` function
- ✅ Added column existence checks
- ✅ Updated all `status` → `hallucination_subtype` references
- ✅ Added fallbacks for missing columns
- ✅ Made code resilient to schema variations

The notebook should now run without KeyError exceptions!
