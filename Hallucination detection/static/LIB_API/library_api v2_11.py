import ast
import pandas as pd
import json
import os
import importlib
import builtins
from types import ModuleType

# =========================
# PATH CONFIG
# =========================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Code generation", "Qwen")
)

DATASETS = {
    "DS1000": {
        "path": os.path.join(BASE_DIR, "ds1k_gen.csv"),
        "code_column": "full_code",
        "task_id_column": "task_id",
        "output": "libapi_ds1000.jsonl"
    },
    "HumanEval": {
        "path": os.path.join(BASE_DIR, "humaneval_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "libapi_humaneval.jsonl"
    },
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "libapi_mbpp.jsonl"
    }
}

BUILTINS = set(dir(builtins))


# =========================
# SAFE MODULE LOADER
# =========================

def safe_import_module(module_name):
    """
    # FIX: Ignore environment-dependent missing modules
    Only return module if actually importable.
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        return None
    except Exception:
        # FIX: Ignore runtime import side-effects
        return None


# =========================
# VISITOR
# =========================

class LibraryAPIVistor(ast.NodeVisitor):
    def __init__(self):
        self.imports = {}
        self.errors = []

    # =========================
    # IMPORT HANDLING
    # =========================

    def visit_Import(self, node):
        for alias in node.names:
            module = safe_import_module(alias.name)

            if module is None:
                # FIX: DO NOT classify missing install as hallucination
                continue

            # FIX: Preserve full module name (no .split("."))
            name = alias.asname or alias.name
            self.imports[name] = module

    def visit_ImportFrom(self, node):
        if node.module is None:
            return

        module = safe_import_module(node.module)

        if module is None:
            # FIX: Ignore missing install
            return

        for alias in node.names:

            # FIX: Proper handling of import *
            if alias.name == "*":
                for attr in dir(module):
                    try:
                        self.imports[attr] = getattr(module, attr)
                    except Exception:
                        pass
                continue

            name = alias.asname or alias.name

            try:
                if hasattr(module, alias.name):
                    self.imports[name] = getattr(module, alias.name)
                else:
                    self.errors.append({
                        "type": "name_error",
                        "name": alias.name,
                        "line": node.lineno
                    })
            except Exception:
                # FIX: Avoid reflection crash
                pass

    # =========================
    # ATTRIBUTE RESOLUTION
    # =========================

    def resolve_attribute_chain(self, node):
        """
        # FIX: Proper chained attribute resolution
        Example:
        scipy.integrate.quad
        """
        parts = []

        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value

        if isinstance(node, ast.Name):
            parts.append(node.id)
        else:
            return None

        return list(reversed(parts))

    def visit_Attribute(self, node):
        chain = self.resolve_attribute_chain(node)

        if chain is None:
            self.generic_visit(node)
            return

        base_name = chain[0]

        if base_name in self.imports:
            obj = self.imports[base_name]

            # Traverse remaining attributes
            for attr in chain[1:]:
                try:
                    if hasattr(obj, attr):
                        obj = getattr(obj, attr)
                    else:
                        self.errors.append({
                            "type": "attribute_error",
                            "object": base_name,
                            "attribute": attr,
                            "line": node.lineno
                        })
                        break
                except Exception:
                    # FIX: Avoid C-extension reflection failure
                    break

        self.generic_visit(node)

    # =========================
    # FUNCTION CALL CHECK
    # =========================

    def visit_Call(self, node):
        """
        # FIX: Removed inspect.signature logic
        Signature inspection is unstable for C-extensions.
        Now only checks existence of callable attribute.
        """

        if isinstance(node.func, ast.Attribute):
            chain = self.resolve_attribute_chain(node.func)

            if chain is not None:
                base_name = chain[0]

                if base_name in self.imports:
                    obj = self.imports[base_name]

                    for attr in chain[1:]:
                        try:
                            if hasattr(obj, attr):
                                obj = getattr(obj, attr)
                            else:
                                self.errors.append({
                                    "type": "attribute_error",
                                    "object": base_name,
                                    "attribute": attr,
                                    "line": node.lineno
                                })
                                break
                        except Exception:
                            break

        self.generic_visit(node)


# =========================
# ANALYSIS FUNCTION
# =========================

def analyze_library_api(code: str):
    result = {
        "libapi_analyzed": False,
        "name_error": 0,
        "attribute_error": 0,
        "module_not_found": 0,  # kept for schema consistency
        "total_libapi_errors": 0,
        "libapi_details": []
    }

    try:
        tree = ast.parse(code)
        visitor = LibraryAPIVistor()
        visitor.visit(tree)

        result["libapi_analyzed"] = True
        result["libapi_details"] = visitor.errors

        for err in visitor.errors:
            if err["type"] in result:
                result[err["type"]] += 1

        result["total_libapi_errors"] = len(visitor.errors)

    except Exception:
        pass

    return result


# =========================
# PIPELINE
# =========================

def run_library_api_pipeline():
    all_rows = []

    for dataset, cfg in DATASETS.items():
        print(f"Processing Library/API analysis for {dataset}...")

        df = pd.read_csv(cfg["path"])
        out = open(cfg["output"], "w", encoding="utf-8")

        for idx, row in df.iterrows():
            code = str(row.get(cfg["code_column"], ""))

            sample_id = row.get(cfg["task_id_column"], idx)

            libapi_result = analyze_library_api(code)

            record = {
                "dataset": dataset,
                "task_id": sample_id,
                **libapi_result
            }

            out.write(json.dumps(record) + "\n")
            all_rows.append(record)

        out.close()
        print(f"Saved → {cfg['output']}")

    pd.DataFrame(all_rows).to_csv("libapi_summary.csv", index=False)
    print("Library/API analysis completed.")


if __name__ == "__main__":
    run_library_api_pipeline()