import ast
import pandas as pd
import json
import os
import importlib
import inspect
import builtins

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
# VISITOR
# =========================

class LibraryAPIVistor(ast.NodeVisitor):
    def __init__(self):
        self.imports = {}
        self.errors = []

    # ---------- Imports ----------
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            try:
                self.imports[name] = importlib.import_module(alias.name)
            except Exception:
                self.errors.append({
                    "type": "module_not_found",
                    "module": alias.name,
                    "line": node.lineno
                })

    def visit_ImportFrom(self, node):
        if node.module is None:
            return

        try:
            module = importlib.import_module(node.module)
            for alias in node.names:
                name = alias.asname or alias.name
                if hasattr(module, alias.name):
                    self.imports[name] = getattr(module, alias.name)
                else:
                    self.errors.append({
                        "type": "name_error",
                        "name": alias.name,
                        "line": node.lineno
                    })
        except Exception:
            self.errors.append({
                "type": "module_not_found",
                "module": node.module,
                "line": node.lineno
            })


    # ---------- Attribute Access ----------
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            base = node.value.id
            attr = node.attr

            if base in self.imports:
                obj = self.imports[base]
                if not hasattr(obj, attr):
                    self.errors.append({
                        "type": "attribute_error",
                        "object": base,
                        "attribute": attr,
                        "line": node.lineno
                    })

        self.generic_visit(node)

    # ---------- Function Calls ----------
    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                base = node.func.value.id
                func_name = node.func.attr

                if base in self.imports:
                    obj = self.imports[base]
                    if hasattr(obj, func_name):
                        try:
                            sig = inspect.signature(getattr(obj, func_name))
                            for kw in node.keywords:
                                if kw.arg not in sig.parameters:
                                    self.errors.append({
                                        "type": "type_error",
                                        "function": func_name,
                                        "invalid_arg": kw.arg,
                                        "line": node.lineno
                                    })
                        except Exception:
                            pass
        self.generic_visit(node)

    # partial-key erro for all those whihc is generated!
    # def visit_Subscript(self, node):
    #     if isinstance(node.slice, ast.Constant):
    #         if isinstance(node.slice.value, str):
    #             self.errors.append({
    #                 "type": "potential_key_error",
    #                 "key": node.slice.value,
    #                 "line": node.lineno
    #             })
    #     self.generic_visit(node)


# =========================
# ANALYSIS FUNCTION
# =========================

def analyze_library_api(code: str):
    result = {
        "libapi_analyzed": False,
        "name_error": 0,
        "attribute_error": 0,
        "type_error": 0,
        "module_not_found": 0,
        # "potential_key_error": 0,
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

            if cfg["task_id_column"]:
                sample_id = row.get(cfg["task_id_column"])
            else:
                sample_id = idx

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
