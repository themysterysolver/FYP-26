import ast
import pandas as pd
import json
import os
import builtins

#https://docs.python.org/3/library/os.path.html
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Code generation", "Qwen")
)#going out and joining in!

DATASETS = {
    "DS1000": {
        "path": os.path.join(BASE_DIR, "ds1k_gen.csv"),
        "code_column": "full_code",
        "task_id_column": None,
        "output": "ast_ds1000.jsonl"
    },
    "HumanEval": {
        "path": os.path.join(BASE_DIR, "humaneval_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "ast_humaneval.jsonl"
    },
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "ast_mbpp.jsonl"
    }
}

OUTPUT_JSONL = "ast_results.jsonl"
OUTPUT_CSV = "ast_summary.csv"


BUILTINS = set(dir(builtins))
 

class SSAVisitor(ast.NodeVisitor):
    def __init__(self):
        self.scopes = [set()]
        self.errors = []
    # ---------- Helpers ----------
    def _define(self, name):
        self.scopes[-1].add(name)

    # def _is_defined(self, name):
    #     return any(name in scope for scope in reversed(self.scopes))
    def _is_defined(self, name):
        if name in BUILTINS:
            return True

        return any(name in scope for scope in reversed(self.scopes))

    # ---------- Common function logic ----------
    def _visit_function(self, node):
        self.scopes.append(set())

        # function arguments are definitions
        for arg in node.args.args:
            self._define(arg.arg)

        self.generic_visit(node)
        self.scopes.pop()

    # ---------- Function scopes ----------
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_function(node)

    # ---------- Loops ----------
    def visit_For(self, node):
        if isinstance(node.target, ast.Name):
            self._define(node.target.id)
        self.generic_visit(node)

    # ---------- Assignments ----------
    def visit_Assign(self, node):
        self.generic_visit(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._define(target.id)

    # ---------- Variable usage ----------
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            if not self._is_defined(node.id):
                self.errors.append({
                    "type": "use_before_definition",
                    "variable": node.id,
                    "line": node.lineno
                })

def analyze_ssa(code: str):
    result = {
        "ssa_analyzed": False,
        "undefined_variables": 0,
        "ssa_details": []
    }

    try:
        tree = ast.parse(code)
        visitor = SSAVisitor()
        visitor.visit(tree)

        result["ssa_analyzed"] = True
        result["undefined_variables"] = len(visitor.errors)
        result["ssa_details"] = visitor.errors

    except Exception:
        pass

    return result


def run_ssa_pipeline():
    all_rows = []

    for dataset, cfg in DATASETS.items():
        print(f"Processing SSA for {dataset}...")

        df = pd.read_csv(cfg["path"])
        out_file = cfg["output"].replace("ast_", "ssa_")
        out = open(out_file, "w", encoding="utf-8")

        for idx, row in df.iterrows():
            code = str(row.get(cfg["code_column"], ""))

            # Prefer task_id if available
            if cfg["task_id_column"]:
                sample_id = row.get(cfg["task_id_column"])
            else:
                sample_id = idx

            ssa_result = analyze_ssa(code)

            record = {
                "dataset": dataset,
                "task_id": sample_id,
                **ssa_result
            }

            out.write(json.dumps(record) + "\n")
            all_rows.append(record)

        out.close()
        print(f"Saved → {out_file}")

    # CSV summary for plotting / stats
    pd.DataFrame(all_rows).to_csv("ssa_summary.csv", index=False)
    print("SSA analysis completed for all datasets.")

if __name__ == "__main__":
    run_ssa_pipeline()