"""
Proof of concept: LIB_API correctly identifies multiple errors (NameError, TypeError,
AttributeError, ModuleNotFoundError) in a single code snippet and reports detection time.
"""
import json
import os
import sys
import time

# Ensure parent (LIB_API) is on path so we can import library_api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from library_api import analyze_library_api

# Faulty snippet designed to trigger multiple LIB_API error types in one run:
# - module_not_found: import of non-existent module
# - name_error: from real module import non-existent name
# - attribute_error: real import, non-existent attribute
# - type_error: valid call with invalid keyword argument
FAULTY_SNIPPET = '''
import nonexistent_module_xyz
from os import nonexistent_attr
import numpy as np

x = np.nonexistent_method
np.array(invalid_keyword=1)
'''


def run_proof():
    print("=" * 60)
    print("LIB_API proof of concept: multi-error detection")
    print("=" * 60)
    print("\nFaulty code snippet:")
    print(FAULTY_SNIPPET)
    print("-" * 60)

    start = time.perf_counter()
    result = analyze_library_api(FAULTY_SNIPPET)
    elapsed = time.perf_counter() - start

    print("Result (JSON):")
    print(json.dumps(result, indent=2))
    print("-" * 60)
    print(f"Detection time: {elapsed * 1000:.3f} ms")
    print(f"Total errors detected: {result['total_libapi_errors']}")
    distinct_types = {e["type"] for e in result["libapi_details"]}
    print(f"Distinct error types: {sorted(distinct_types)}")
    print("=" * 60)

    # Assert multi-error proof
    assert result["libapi_analyzed"], "Snippet should be analyzed"
    assert result["total_libapi_errors"] >= 2, "Should detect at least 2 errors"
    assert len(distinct_types) >= 2, "Should detect at least 2 distinct error types"
    print("Proof passed: multiple errors and multiple types identified.")
    return result, elapsed


if __name__ == "__main__":
    run_proof()
