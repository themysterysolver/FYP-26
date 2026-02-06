import ast
import pandas as pd
import json
import os

# ==============================
# CONFIG
# ==============================
DATASETS = {
    "DS1000": {
        "path": "ds1k_gen.csv",
        "code_column": "full_code"
    },
    "HumanEval": {
        "path": "humaneval_gen.csv",
        "code_column": "GENERATED_CODE"
    },
    "MBPP": {
        "path": "mbpp_gen.csv",
        "code_column": "GENERATED_CODE"
    }
}

OUTPUT_JSONL = "ast_results.jsonl"
OUTPUT_CSV = "ast_summary.csv"


# ==============================
# AST STRUCTURAL CHECKER
# ==============================
class StructuralViolationVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.in_function = 0
        self.in_loop = 0

    def visit_FunctionDef(self, node):
        self.in_function += 1
        self.generic_visit(node)
        self.in_function -= 1

    def visit_AsyncFunctionDef(self, node):
        self.in_function += 1
        self.generic_visit(node)
        self.in_function -= 1

    def visit_For(self, node):
        self.in_loop += 1
        self.generic_visit(node)
        self.in_loop -= 1

    def visit_While(self, node):
        self.in_loop += 1
        self.generic_visit(node)
        self.in_loop -= 1

    def visit_Return(self, node):
        if self.in_function == 0:
            self.errors.append(("return_outside_function", node.lineno))
        self.generic_visit(node)

    def visit_Break(self, node):
        if self.in_loop == 0:
            self.errors.append(("break_outside_loop", node.lineno))

    def visit_Continue(self, node):
        if self.in_loop == 0:
            self.errors.append(("continue_outside_loop", node.lineno))


# ==============================
# AST ANALYSIS FUNCTION
# ==============================
def analyze_ast(code: str):
    result = {
        "ast_parsed": False,
        "syntax_error": 0,
        "indentation_error": 0,
        "structural_error": 0,
        "error_type": None,
        "line": None,
        "message": None
    }

    try:
        tree = ast.parse(code)
        result["ast_parsed"] = True

        visitor = StructuralViolationVisitor()
        visitor.visit(tree)

        if visitor.errors:
            result["structural_error"] = len(visitor.errors)

    except IndentationError as e:
        result["indentation_error"] = 1
        result["error_type"] = "IndentationError"
        result["line"] = e.lineno
        result["message"] = str(e)

    except SyntaxError as e:
        result["syntax_error"] = 1
        result["error_type"] = "SyntaxError"
        result["line"] = e.lineno
        result["message"] = str(e)

    return result


# ==============================
# MAIN PIPELINE
# ==============================
def run_ast_pipeline():
    all_rows = []
    jsonl_out = open(OUTPUT_JSONL, "w", encoding="utf-8")

    for dataset, cfg in DATASETS.items():
        print(f"Processing {dataset}...")
        df = pd.read_csv(cfg["path"])

        for idx, row in df.iterrows():
            code = str(row.get(cfg["code_column"], ""))

            ast_result = analyze_ast(code)

            record = {
                "dataset": dataset,
                "sample_id": idx,
                **ast_result
            }

            jsonl_out.write(json.dumps(record) + "\n")
            all_rows.append(record)

    jsonl_out.close()

    pd.DataFrame(all_rows).to_csv(OUTPUT_CSV, index=False)
    print("AST analysis completed.")


if __name__ == "__main__":
    run_ast_pipeline()
