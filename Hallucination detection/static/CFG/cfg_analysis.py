import ast
import json
import pandas as pd
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

OUTPUT_JSONL = "cfg_results.jsonl"
OUTPUT_CSV = "cfg_summary.csv"

class CFGVisitor(ast.NodeVisitor):

    def __init__(self):
        self.unreachable = []
        self.missing_returns = []

    def _check_block_unreachable(self, statements):
        terminated = False
        for stmt in statements:
            if terminated:
                self.unreachable.append({
                    "type": "unreachable_code",
                    "start_line": stmt.lineno,
                    "end_line": getattr(stmt, "end_lineno", stmt.lineno)
                })
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminated = True

    def visit_FunctionDef(self, node):
        self._check_block_unreachable(node.body)
        self._check_missing_return(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self._check_block_unreachable(node.body)
        self._check_missing_return(node)
        self.generic_visit(node)

    def _block_returns(self, stmts):
        for stmt in stmts:
            if isinstance(stmt, ast.Return):
                return True

            if isinstance(stmt, ast.If):
                if stmt.orelse:
                    if self._block_returns(stmt.body) and self._block_returns(stmt.orelse):
                        return True
                else:
                    return False
        return False

    def _check_missing_return(self, node):
        if not self._block_returns(node.body):
            self.missing_returns.append({
                "type": "missing_return",
                "function": node.name,
                "start_line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })


def analyze_cfg(code: str):
    result = {
        "cfg_analyzed": False,
        "unreachable_code": 0,
        "missing_return": 0,
        "cfg_details": []
    }

    try:
        tree = ast.parse(code)
        visitor = CFGVisitor()
        visitor.visit(tree)

        result["cfg_analyzed"] = True
        result["unreachable_code"] = len(visitor.unreachable)
        result["missing_return"] = len(visitor.missing_returns)
        result["cfg_details"] = visitor.unreachable + visitor.missing_returns

    except Exception:
        pass
    return result

def run_cfg_pipeline():
    all_rows = []

    for dataset, cfg in DATASETS.items():
        print(f"Processing CFG for {dataset}...")

        df = pd.read_csv(cfg["path"])
        out_file = cfg["output"].replace("ast_", "cfg_")
        out = open(out_file, "w", encoding="utf-8")

        for idx, row in df.iterrows():
            code = str(row.get(cfg["code_column"], ""))

            # Prefer task_id if available
            if cfg["task_id_column"]:
                sample_id = row.get(cfg["task_id_column"])
            else:
                sample_id = idx

            cfg_result = analyze_cfg(code)

            record = {
                "dataset": dataset,
                "task_id": sample_id,
                **cfg_result
            }

            out.write(json.dumps(record) + "\n")
            all_rows.append(record)

        out.close()
        print(f"Saved → {out_file}")

    pd.DataFrame(all_rows).to_csv("cfg_summary.csv", index=False)
    print("CFG analysis completed for all datasets.")

if __name__ == "__main__":
    run_cfg_pipeline()
