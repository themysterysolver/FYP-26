# LIB_API proof of concept: multi-error detection

This folder contains a proof of concept that **LIB_API correctly identifies multiple errors** (e.g. NameError, TypeError, AttributeError, ModuleNotFoundError) in a **single code snippet** and reports **how long detection took**.

## What it does

- **Faulty snippet:** A small Python snippet is defined that deliberately triggers several LIB_API error types:
  - `module_not_found`: `import nonexistent_module_xyz`
  - `name_error`: `from os import nonexistent_attr`
  - `attribute_error`: `np.nonexistent_method` (numpy has no such attribute)
  - `type_error`: `np.array(invalid_keyword=1)` (invalid keyword for `np.array`)

- **Detection time:** The script uses `time.perf_counter()` around the single call to `analyze_library_api(...)` and prints the elapsed time in **milliseconds**. This is the time for the entire detection (parse + AST visit + aggregation) for that one snippet.

- **Assertions:** It asserts that at least 2 errors and at least 2 distinct error types are reported, so the PoC doubles as a minimal correctness check.

## How to run

From the **LIB_API** directory (parent of `proof_of_concept`):

```bash
python proof_of_concept/proof_multi_error.py
```

Or from inside `proof_of_concept`:

```bash
cd proof_of_concept
python proof_multi_error.py
```

**Requirements:** Same as the main LIB_API module (e.g. `pandas` for `library_api.py`). If you get `ModuleNotFoundError: No module named 'pandas'`, install it or use the project’s virtual environment.

## Interpretation of “detection time”

The printed **detection time** is the wall-clock time for:

1. Parsing the snippet with `ast.parse(code)`
2. Running the `LibraryAPIVistor` over the AST
3. Building the result dict (counts and `libapi_details`)

It does **not** include loading the `library_api` module or any dataset I/O. For a single small snippet, this is typically well under a few milliseconds on a modern machine.
