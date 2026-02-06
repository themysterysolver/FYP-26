import ast
import pandas as pd
import json
import os

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

#print(DATASETS)
# we will use jsonl over json

#inheriting from ast.NodeVisitor
#https://docs.python.org/3/library/ast.html#ast.NodeVisitor.generic_visit
class StructuralViolationVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.in_function = 0
        self.in_loop = 0

    def _record(self, error_type, node):
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", start)
        self.errors.append({
            "type": error_type,
            "start_line": start,
            "end_line": end
        })

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
            self._record("return_outside_function", node)
        self.generic_visit(node)

    def visit_Break(self, node):
        if self.in_loop == 0:
            self._record("break_outside_loop", node)

    def visit_Continue(self, node):
        if self.in_loop == 0:
            self._record("continue_outside_loop", node)


#main ast checking
def analyze_ast(code: str):
    '''
    here we analyse ast,
    we record syntax or indentation error which is caught first.

    '''
    result = {
        "ast_parsed": False,
        "syntax_error": 0,
        "indentation_error": 0,
        "structural_error": 0,
        "error_type": None,
        "line": None,
        "message": None,
        "structural_details": []   
    }

    try:
        tree = ast.parse(code)
        result["ast_parsed"] = True

        visitor = StructuralViolationVisitor()
        visitor.visit(tree)

        if visitor.errors:
            result["structural_error"] = len(visitor.errors)
            result["structural_details"] = visitor.errors

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


def run_ast_pipeline():
    for dataset, cfg in DATASETS.items():
        print(f"Processing {dataset}...")

        df = pd.read_csv(cfg["path"])
        out = open(cfg["output"], "w", encoding="utf-8")

        for idx, row in df.iterrows():
            code = str(row.get(cfg["code_column"], ""))

            # Prefer task_id if available
            if cfg["task_id_column"]:
                sample_id = row.get(cfg["task_id_column"])
            else:
                sample_id = idx   # fallback for DS1000

            ast_result = analyze_ast(code)

            record = {
                "dataset": dataset,
                "task_id": sample_id,
                **ast_result
            }

            out.write(json.dumps(record) + "\n")

        out.close()
        print(f"Saved → {cfg['output']}")

    print("AST analysis completed for all datasets.")

if __name__ == "__main__":
    run_ast_pipeline()
