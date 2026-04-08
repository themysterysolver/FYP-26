import ast
import builtins
import json
import os

import pandas as pd


# https://docs.python.org/3/library/os.path.html
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Code generation", "Qwen")
)  # going out and joining in!

DATASETS = {
    "DS1000": {
        "path": os.path.join(BASE_DIR, "ds1k_gen.csv"),
        "code_column": "full_code",
        "task_id_column": "task_id",
        "output": "ast_ds1000_new.jsonl",
    },
    "HumanEval": {
        "path": os.path.join(BASE_DIR, "humaneval_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "ast_humaneval_new.jsonl",
    },
    "MBPP": {
        "path": os.path.join(BASE_DIR, "mbpp_gen.csv"),
        "code_column": "GENERATED_CODE",
        "task_id_column": "task_id",
        "output": "ast_mbpp_new.jsonl",
    },
}

OUTPUT_JSONL = "ast_results.jsonl"
OUTPUT_CSV = "ast_summary_new.csv"


# inheriting from ast.NodeVisitor class
# https://docs.python.org/3/library/ast.html#ast.NodeVisitor.generic_visit
class StructuralViolationVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self._error_keys = set()
        self.in_function = 0
        self.in_loop = 0

    def _record(self, error_type, node):
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", start)
        key = (error_type, start, end)
        if key in self._error_keys:
            return
        self._error_keys.add(key)
        self.errors.append(
            {
                "type": error_type,
                "start_line": start,
                "end_line": end,
            }
        )

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


class UndefinedVariableAnalyzer:
    """
    Flow-aware undefined variable analyzer.
    - Tracks definitely defined variables by scope.
    - Uses branch intersection for `if` and `try` paths.
    - Treats loop target vars as available inside loop body.
    - Handles lambda parameters as local definitions.
    """

    def __init__(self):
        self.errors = []
        self._error_keys = set()
        self._builtins = set(dir(builtins))

    def _record(self, name, node, scope):
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", start)
        key = ("undefined_variable", name, start, end, scope)
        if key in self._error_keys:
            return
        self._error_keys.add(key)
        self.errors.append(
            {
                "type": "undefined_variable",
                "name": name,
                "line": start,
                "end_line": end,
                "scope": scope,
            }
        )

    def analyze(self, tree):
        self.errors = []
        self._error_keys = set()
        self._analyze_block(tree.body, set(), set(), scope="module")
        return self.errors

    def _extract_names_from_target(self, target):
        names = set()
        if isinstance(target, ast.Name):
            names.add(target.id)
            return names
        for child in ast.iter_child_nodes(target):
            names.update(self._extract_names_from_target(child))
        return names

    def _extract_arg_names(self, args):
        names = set()
        for arg in getattr(args, "posonlyargs", []):
            names.add(arg.arg)
        for arg in args.args:
            names.add(arg.arg)
        if args.vararg:
            names.add(args.vararg.arg)
        for arg in args.kwonlyargs:
            names.add(arg.arg)
        if args.kwarg:
            names.add(args.kwarg.arg)
        return names

    def _is_defined(self, name, local_defs, visible_outer_defs):
        return name in local_defs or name in visible_outer_defs or name in self._builtins

    def _analyze_name_load(self, node, local_defs, visible_outer_defs, scope):
        if not self._is_defined(node.id, local_defs, visible_outer_defs):
            self._record(node.id, node, scope)

    def _analyze_expr(self, node, local_defs, visible_outer_defs, scope):
        if node is None:
            return

        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            self._analyze_name_load(node, local_defs, visible_outer_defs, scope)
            return

        if isinstance(node, ast.Lambda):
            # Defaults are evaluated in outer scope.
            for default in node.args.defaults:
                self._analyze_expr(default, local_defs, visible_outer_defs, scope)
            for default in node.args.kw_defaults:
                self._analyze_expr(default, local_defs, visible_outer_defs, scope)

            lambda_local = self._extract_arg_names(node.args)
            lambda_outer = local_defs | visible_outer_defs
            self._analyze_expr(
                node.body,
                local_defs=lambda_local,
                visible_outer_defs=lambda_outer,
                scope="lambda",
            )
            return

        if isinstance(node, ast.ListComp):
            self._analyze_comprehension(node.generators, node.elt, local_defs, visible_outer_defs, scope)
            return

        if isinstance(node, ast.SetComp):
            self._analyze_comprehension(node.generators, node.elt, local_defs, visible_outer_defs, scope)
            return

        if isinstance(node, ast.GeneratorExp):
            self._analyze_comprehension(node.generators, node.elt, local_defs, visible_outer_defs, scope)
            return

        if isinstance(node, ast.DictComp):
            self._analyze_comprehension(
                node.generators,
                (node.key, node.value),
                local_defs,
                visible_outer_defs,
                scope,
            )
            return

        for child in ast.iter_child_nodes(node):
            self._analyze_expr(child, local_defs, visible_outer_defs, scope)

    def _analyze_comprehension(self, generators, elt_or_pair, local_defs, visible_outer_defs, scope):
        comp_local = set()
        for gen in generators:
            # iter expression sees outer scope + previous comp vars.
            self._analyze_expr(gen.iter, local_defs | comp_local, visible_outer_defs, scope)
            target_names = self._extract_names_from_target(gen.target)
            comp_local.update(target_names)
            for if_expr in gen.ifs:
                self._analyze_expr(if_expr, local_defs | comp_local, visible_outer_defs, scope)

        if isinstance(elt_or_pair, tuple):
            key, value = elt_or_pair
            self._analyze_expr(key, local_defs | comp_local, visible_outer_defs, scope)
            self._analyze_expr(value, local_defs | comp_local, visible_outer_defs, scope)
        else:
            self._analyze_expr(elt_or_pair, local_defs | comp_local, visible_outer_defs, scope)

    def _analyze_function_def(self, node, local_defs, visible_outer_defs, scope):
        # Decorators/returns/defaults are in outer scope.
        for dec in node.decorator_list:
            self._analyze_expr(dec, local_defs, visible_outer_defs, scope)
        self._analyze_expr(getattr(node, "returns", None), local_defs, visible_outer_defs, scope)

        for default in node.args.defaults:
            self._analyze_expr(default, local_defs, visible_outer_defs, scope)
        for default in node.args.kw_defaults:
            self._analyze_expr(default, local_defs, visible_outer_defs, scope)

        # Function name becomes defined in current scope.
        local_defs.add(node.name)

        fn_local = self._extract_arg_names(node.args)
        fn_outer = local_defs | visible_outer_defs
        self._analyze_block(node.body, fn_local, fn_outer, scope="function")

    def _analyze_class_def(self, node, local_defs, visible_outer_defs, scope):
        for dec in node.decorator_list:
            self._analyze_expr(dec, local_defs, visible_outer_defs, scope)
        for base in node.bases:
            self._analyze_expr(base, local_defs, visible_outer_defs, scope)
        for key in node.keywords:
            self._analyze_expr(key.value, local_defs, visible_outer_defs, scope)

        local_defs.add(node.name)
        # Class body executes in a new local namespace with outer visibility.
        class_outer = local_defs | visible_outer_defs
        self._analyze_block(node.body, set(), class_outer, scope="class")

    def _analyze_stmt(self, stmt, local_defs, visible_outer_defs, scope):
        if isinstance(stmt, ast.Assign):
            self._analyze_expr(stmt.value, local_defs, visible_outer_defs, scope)
            for target in stmt.targets:
                local_defs.update(self._extract_names_from_target(target))
            return

        if isinstance(stmt, ast.AnnAssign):
            self._analyze_expr(stmt.annotation, local_defs, visible_outer_defs, scope)
            self._analyze_expr(stmt.value, local_defs, visible_outer_defs, scope)
            if isinstance(stmt.target, ast.Name):
                local_defs.add(stmt.target.id)
            else:
                local_defs.update(self._extract_names_from_target(stmt.target))
            return

        if isinstance(stmt, ast.AugAssign):
            # x += 1 must read x first.
            self._analyze_expr(stmt.target, local_defs, visible_outer_defs, scope)
            self._analyze_expr(stmt.value, local_defs, visible_outer_defs, scope)
            local_defs.update(self._extract_names_from_target(stmt.target))
            return

        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._analyze_function_def(stmt, local_defs, visible_outer_defs, scope)
            return

        if isinstance(stmt, ast.ClassDef):
            self._analyze_class_def(stmt, local_defs, visible_outer_defs, scope)
            return

        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                local_defs.add(alias.asname if alias.asname else alias.name.split(".")[0])
            return

        if isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                if alias.name == "*":
                    continue
                local_defs.add(alias.asname if alias.asname else alias.name)
            return

        if isinstance(stmt, ast.If):
            self._analyze_expr(stmt.test, local_defs, visible_outer_defs, scope)
            before = set(local_defs)
            then_defs = self._analyze_block(stmt.body, set(before), visible_outer_defs, scope)
            else_start = set(before)
            else_defs = (
                self._analyze_block(stmt.orelse, else_start, visible_outer_defs, scope)
                if stmt.orelse
                else else_start
            )
            local_defs.clear()
            local_defs.update(then_defs & else_defs)
            return

        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            self._analyze_expr(stmt.iter, local_defs, visible_outer_defs, scope)
            loop_defs = set(local_defs)
            loop_defs.update(self._extract_names_from_target(stmt.target))
            self._analyze_block(stmt.body, loop_defs, visible_outer_defs, scope)
            self._analyze_block(stmt.orelse, set(local_defs), visible_outer_defs, scope)
            # Conservative: loop may not run; do not promote loop-body defs.
            return

        if isinstance(stmt, ast.While):
            self._analyze_expr(stmt.test, local_defs, visible_outer_defs, scope)
            self._analyze_block(stmt.body, set(local_defs), visible_outer_defs, scope)
            self._analyze_block(stmt.orelse, set(local_defs), visible_outer_defs, scope)
            # Conservative: loop may not run.
            return

        if isinstance(stmt, ast.Try):
            before = set(local_defs)

            normal_defs = self._analyze_block(stmt.body, set(before), visible_outer_defs, scope)
            if stmt.orelse:
                normal_defs = self._analyze_block(stmt.orelse, normal_defs, visible_outer_defs, scope)

            path_defs = [normal_defs]
            for handler in stmt.handlers:
                if handler.type is not None:
                    self._analyze_expr(handler.type, before, visible_outer_defs, scope)
                handler_defs = set(before)
                if handler.name:
                    handler_defs.add(handler.name)
                handler_defs = self._analyze_block(handler.body, handler_defs, visible_outer_defs, scope)
                path_defs.append(handler_defs)

            merged = set.intersection(*path_defs) if path_defs else before
            if stmt.finalbody:
                merged = self._analyze_block(stmt.finalbody, merged, visible_outer_defs, scope)

            local_defs.clear()
            local_defs.update(merged)
            return

        if isinstance(stmt, ast.With):
            working = set(local_defs)
            for item in stmt.items:
                self._analyze_expr(item.context_expr, working, visible_outer_defs, scope)
                if item.optional_vars is not None:
                    working.update(self._extract_names_from_target(item.optional_vars))
            self._analyze_block(stmt.body, working, visible_outer_defs, scope)
            # Do not promote optional vars outside in conservative mode.
            return

        if isinstance(stmt, ast.Raise):
            self._analyze_expr(stmt.exc, local_defs, visible_outer_defs, scope)
            self._analyze_expr(stmt.cause, local_defs, visible_outer_defs, scope)
            return

        if isinstance(stmt, ast.Assert):
            self._analyze_expr(stmt.test, local_defs, visible_outer_defs, scope)
            self._analyze_expr(stmt.msg, local_defs, visible_outer_defs, scope)
            return

        if isinstance(stmt, ast.Delete):
            # Deleting a name means it is no longer definitely defined.
            for target in stmt.targets:
                names = self._extract_names_from_target(target)
                for name in names:
                    if name in local_defs:
                        local_defs.remove(name)
            return

        if isinstance(stmt, ast.Expr):
            self._analyze_expr(stmt.value, local_defs, visible_outer_defs, scope)
            return

        if isinstance(stmt, ast.Return):
            self._analyze_expr(stmt.value, local_defs, visible_outer_defs, scope)
            return

        if isinstance(stmt, ast.Match):
            self._analyze_expr(stmt.subject, local_defs, visible_outer_defs, scope)
            before = set(local_defs)
            case_defs = []
            for case in stmt.cases:
                case_local = set(before)
                case_local.update(self._extract_names_from_target(case.pattern))
                self._analyze_expr(case.guard, case_local, visible_outer_defs, scope)
                case_defs.append(self._analyze_block(case.body, case_local, visible_outer_defs, scope))
            if case_defs:
                local_defs.clear()
                local_defs.update(set.intersection(*case_defs))
            return

        # Generic fallback for statements not explicitly handled.
        for child in ast.iter_child_nodes(stmt):
            if isinstance(child, ast.stmt):
                self._analyze_stmt(child, local_defs, visible_outer_defs, scope)
            else:
                self._analyze_expr(child, local_defs, visible_outer_defs, scope)

    def _analyze_block(self, statements, local_defs, visible_outer_defs, scope):
        for stmt in statements:
            self._analyze_stmt(stmt, local_defs, visible_outer_defs, scope)
        return local_defs


# main ast checking
def analyze_ast(code: str):
    """
    Here we analyse AST and record syntax/indentation/structural errors.
    This v2 also records undefined variable usage using flow-aware checks.
    """
    result = {
        "ast_parsed": False,
        "syntax_error": 0,
        "indentation_error": 0,
        "structural_error": 0,
        "undefined_variable_error": 0,
        "error_type": None,
        "line": None,
        "message": None,
        "structural_details": [],
        "undefined_variable_details": [],
    }

    try:
        tree = ast.parse(code)
        result["ast_parsed"] = True

        structural_visitor = StructuralViolationVisitor()
        structural_visitor.visit(tree)
        if structural_visitor.errors:
            result["structural_error"] = len(structural_visitor.errors)
            result["structural_details"] = structural_visitor.errors

        undef_analyzer = UndefinedVariableAnalyzer()
        undef_errors = undef_analyzer.analyze(tree)
        if undef_errors:
            result["undefined_variable_error"] = len(undef_errors)
            result["undefined_variable_details"] = undef_errors

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


def run_poc():
    poc_code = """
def foo(x):
    if x > 0:
        return x
    else:
        return y
"""
    poc_result = analyze_ast(poc_code)
    print("POC result:")
    print(json.dumps(poc_result, indent=2))
    return poc_result


def run_ast_pipeline():
    all_records = []

    for dataset, dfp in DATASETS.items():
        print(f"Processing {dataset}...")

        df = pd.read_csv(dfp["path"])
        with open(dfp["output"], "w", encoding="utf-8") as out:
            for _, row in df.iterrows():
                code = str(row.get(dfp["code_column"], ""))
                sample_id = row.get(dfp["task_id_column"])
                ast_result = analyze_ast(code)

                record = {
                    "dataset": dataset,
                    "task_id": sample_id,
                    **ast_result,
                }

                out.write(json.dumps(record) + "\n")
                all_records.append(record)

        print(f"Saved -> {dfp['output']}")

    summary_df = pd.DataFrame(all_records)
    summary_df.to_csv(OUTPUT_CSV, index=False)

    print(f"Full AST results saved -> {OUTPUT_CSV}")
    print("AST analysis completed for all datasets.")


if __name__ == "__main__":
    #run_poc()
    run_ast_pipeline()
