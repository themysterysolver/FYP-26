"""
sample_kg_util_demo.py
----------------------
A walkthrough of every function in kg_util.py showing
what it does, what it takes in, and what it returns.

Run from:  APR/DS-KG/UTIL/
    python sample_kg_util_demo.py
"""

import json
from kg_util import (
    KG,
    detect_name_error,
    detect_attribute_error,
    detect_type_error,
    detect_module_not_found,
    rank,
    build_function,
    build_method,
    build_class,
    suggest_name,
    suggest_attribute,
    suggest_type,
    suggest_module,
)


def pretty(obj):
    """Helper to print dicts/lists nicely."""
    print(json.dumps(obj, indent=2, default=str))


# =============================================================
# 1. THE KNOWLEDGE GRAPH (KG) — what got loaded at import time
# =============================================================
print("=" * 65)
print("1. KG CONTENTS OVERVIEW")
print("=" * 65)
print(f"  Functions loaded : {len(KG['functions'])}")
print(f"  Classes loaded   : {len(KG['classes'])}")
print(f"  Modules loaded   : {len(KG['modules'])}")
print(f"  Libraries        : {KG['libraries']}")
print()

# Show what a single function entry looks like
sample_func = "mean"
if sample_func in KG["functions"]:
    print(f'  Sample function node — KG["functions"]["{sample_func}"]:')
    pretty(KG["functions"][sample_func])
print()

# Show what a single class entry looks like
sample_class = "DataFrame"
if sample_class in KG["classes"]:
    node = KG["classes"][sample_class]
    print(f'  Sample class node — KG["classes"]["{sample_class}"]:')
    print(f'    node_type   : {node["node_type"]}')
    print(f'    module      : {node["module"]}')
    print(f'    description : {node["description"][:80]}...')
    print(f'    methods     : {node["methods"][:8]} ... ({len(node["methods"])} total)')
    print(f'    attributes  : {node["attributes"][:8]} ... ({len(node["attributes"])} total)')
print()


# =============================================================
# 2. ERROR DETECTORS — regex parsers that extract the key symbol
# =============================================================
print("=" * 65)
print("2. ERROR DETECTORS")
print("=" * 65)

# --- detect_name_error ---
msg1 = "Failed: NameError: name 'reshpe' is not defined"
result1 = detect_name_error(msg1)
print(f"  detect_name_error(\"{msg1}\")")
print(f"    -> {repr(result1)}")
print(f"    Extracted the undefined symbol: 'reshpe'")
print()

# --- detect_attribute_error ---
msg2 = "Failed: AttributeError: 'DataFrame' object has no attribute 'appeend'"
result2 = detect_attribute_error(msg2)
print(f"  detect_attribute_error(\"{msg2}\")")
print(f"    -> {result2}")
print(f"    Extracted class='DataFrame', attribute='appeend'")
print()

# --- detect_type_error ---
msg3 = "Failed: TypeError: concat() got an unexpected keyword argument 'join_axes'"
result3 = detect_type_error(msg3)
print(f"  detect_type_error(\"{msg3}\")")
print(f"    -> {repr(result3)}")
print(f"    Extracted the function name: 'concat'")
print()

# --- detect_module_not_found ---
msg4 = "Failed: ModuleNotFoundError: No module named 'skleran'"
result4 = detect_module_not_found(msg4)
print(f"  detect_module_not_found(\"{msg4}\")")
print(f"    -> {repr(result4)}")
print(f"    Extracted the misspelled module: 'skleran'")
print()


# =============================================================
# 3. RANK — fuzzy matching helper (difflib.get_close_matches)
# =============================================================
print("=" * 65)
print("3. RANK (fuzzy matching)")
print("=" * 65)

candidates = ["reshape", "reset_index", "resample", "replace"]
symbol = "reshpe"
matches = rank(symbol, candidates)
print(f'  rank("{symbol}", {candidates})')
print(f"    -> {matches}")
print(f"    Finds closest matches with cutoff=0.6, returns up to 2")
print()


# =============================================================
# 4. BUILDERS — format a KG node into a suggestion dict
# =============================================================
print("=" * 65)
print("4. BUILDERS (format KG nodes into suggestion dicts)")
print("=" * 65)

# build_function
if "mean" in KG["functions"] and KG["functions"]["mean"]["node_type"] == "function":
    print("  build_function('mean', KG['functions']['mean']):")
    pretty(build_function("mean", KG["functions"]["mean"]))
elif "mean" in KG["functions"]:
    # mean might be stored as a method (due to KG overwrite)
    print("  build_method('mean', KG['functions']['mean']):")
    pretty(build_method("mean", KG["functions"]["mean"]))
print()

# build_class
if "Series" in KG["classes"]:
    print("  build_class('Series', KG['classes']['Series']):")
    pretty(build_class("Series", KG["classes"]["Series"]))
print()


# =============================================================
# 5. SUGGESTION ENGINES — the main query functions
# =============================================================
print("=" * 65)
print("5. SUGGESTION ENGINES")
print("=" * 65)

# --- suggest_name ---
# Scenario: code has `reshpe(arr, (3,2))` but should be `reshape`
print('  suggest_name("reshpe")  [NameError: undefined symbol]')
pretty(suggest_name("reshpe"))
print()

# --- suggest_attribute ---
# Scenario: code has `df.appeend(row)` but should be `df.append` or `df._append`
print('  suggest_attribute("DataFrame", "appeend")  [AttributeError]')
pretty(suggest_attribute("DataFrame", "appeend"))
print()

# --- suggest_type ---
# Scenario: code calls `concat()` with wrong keyword args
print('  suggest_type("concat")  [TypeError: wrong params]')
pretty(suggest_type("concat"))
print()

# --- suggest_module ---
# Scenario: code does `import skleran` but should be `sklearn`
print('  suggest_module("skleran")  [ModuleNotFoundError]')
pretty(suggest_module("skleran"))
print()


# =============================================================
# 6. END-TO-END — simulate the full pipeline for one error
# =============================================================
print("=" * 65)
print("6. END-TO-END EXAMPLE")
print("=" * 65)

error_msg = "Failed: AttributeError: 'Series' object has no attribute 'to_numpyy'"
print(f"  Error message: {error_msg}")
print()

# Step A: detect error type and extract symbols
parsed = detect_attribute_error(error_msg)
print(f"  Step A - detect_attribute_error -> class='{parsed[0]}', attr='{parsed[1]}'")

# Step B: query KG for suggestions
suggestions = suggest_attribute(parsed[0], parsed[1])
print(f"  Step B - suggest_attribute('{parsed[0]}', '{parsed[1]}'):")
pretty(suggestions)
print()

print("  The LLM can now use these suggestions to know that")
print("  'to_numpyy' should probably be 'to_numpy' and see its")
print("  correct signature and parameters.")
print()
print("Done!")
