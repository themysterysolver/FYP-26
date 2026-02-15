"""
DS-KG Context Provider for LLM Code Repair
-------------------------------------------
Provides structured API context from the DS-1000 Knowledge Graph
to augment LLM prompts when repairing generated code.

Usage:
    from kg_context import get_repair_context

    ctx = get_repair_context(code_with_markers, error_info)
    # ctx["context_summary"]  -> ready-to-inject text for LLM prompt
    # ctx["suggestions"]      -> structured list of KG API suggestions
"""

import re
import ast
import sys
import os
import json

# ======================================================
# Ensure UTIL/ is importable
# ======================================================

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "UTIL"))

from kg_util import (
    KG,
    detect_name_error,
    detect_attribute_error,
    detect_type_error,
    detect_module_not_found,
    suggest_name,
    suggest_attribute,
    suggest_type,
    suggest_module,
)

# ======================================================
# 1. Extract error region from markers
# ======================================================

_MARKER_RE = re.compile(
    r"\[ERROR START\]\s*\n?(.*?)\n?\s*\[ERROR END\]",
    re.DOTALL,
)


def extract_error_region(code):
    """Return the code between [ERROR START] and [ERROR END], plus surrounding context.

    Returns:
        dict with:
            - region: str   (trimmed code inside the markers)
            - context_before: str (up to 3 lines before the marker)
            - context_after:  str (up to 3 lines after the marker)
    """
    match = _MARKER_RE.search(code)
    if not match:
        return {"region": "", "context_before": "", "context_after": ""}

    region = match.group(1).strip()

    # Grab surrounding lines for context
    before_text = code[: match.start()]
    after_text = code[match.end() :]

    before_lines = before_text.rstrip("\n").split("\n")
    after_lines = after_text.lstrip("\n").split("\n")

    context_before = "\n".join(before_lines[-3:]).strip()
    context_after = "\n".join(after_lines[:3]).strip()

    return {
        "region": region,
        "context_before": context_before,
        "context_after": context_after,
    }


# ======================================================
# 2. Classify error type
# ======================================================

# Canonical error categories this module handles
_ERROR_CATEGORIES = {
    "NameError",
    "AttributeError",
    "TypeError",
    "ModuleNotFoundError",
}


def classify_error(error_info):
    """Determine the canonical error category from error_info.

    Tries error_info["error_type"] first, then falls back to
    regex detection on error_info["error_message"].

    Returns one of the _ERROR_CATEGORIES strings, or "Unknown".
    """
    etype = str(error_info.get("error_type", "")).strip()

    # Direct match (handle both "NameError" and "Failed: NameError: ...")
    for cat in _ERROR_CATEGORIES:
        if cat in etype:
            return cat

    # Fallback: regex on error_message
    msg = str(error_info.get("error_message", ""))

    if detect_name_error(msg):
        return "NameError"
    if detect_attribute_error(msg):
        return "AttributeError"
    if detect_module_not_found(msg):
        return "ModuleNotFoundError"
    if detect_type_error(msg):
        return "TypeError"

    # Also try the combined status string if provided
    status = str(error_info.get("status", ""))
    if status:
        if detect_name_error(status):
            return "NameError"
        if detect_attribute_error(status):
            return "AttributeError"
        if detect_module_not_found(status):
            return "ModuleNotFoundError"
        if detect_type_error(status):
            return "TypeError"

    return "Unknown"


# ======================================================
# 3. AST-analyze the error region for symbols
# ======================================================

class _SymbolExtractor(ast.NodeVisitor):
    """Walk an AST fragment and collect imports, attribute accesses, and calls."""

    def __init__(self):
        self.imports = []        # (module_name, alias_or_name)
        self.attributes = []     # (object_name, attr_name)
        self.calls = []          # function/method name strings

    # --- imports ---
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append((alias.name, alias.asname or alias.name))
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        mod = node.module or ""
        for alias in node.names:
            self.imports.append((f"{mod}.{alias.name}", alias.asname or alias.name))
        self.generic_visit(node)

    # --- attribute access ---
    def visit_Attribute(self, node):
        # Try to resolve the object name (e.g. df.values -> obj="df", attr="values")
        obj_name = _resolve_name(node.value)
        if obj_name:
            self.attributes.append((obj_name, node.attr))
        self.generic_visit(node)

    # --- function / method calls ---
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)


def _resolve_name(node):
    """Best-effort resolution of an AST node to a dotted name string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _resolve_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
    return None


def analyze_error_region(error_region, full_code=""):
    """Parse the error region (and optionally the full code for import context)
    and return extracted symbols.

    Returns dict with keys: imports, attributes, calls
    """
    result = {"imports": [], "attributes": [], "calls": []}

    # Combine full code imports with the error region for analysis
    code_to_parse = full_code if full_code else error_region

    try:
        tree = ast.parse(code_to_parse)
    except SyntaxError:
        # If full code fails, try just the error region
        try:
            tree = ast.parse(error_region)
        except SyntaxError:
            return result

    extractor = _SymbolExtractor()
    extractor.visit(tree)

    result["imports"] = extractor.imports
    result["attributes"] = extractor.attributes
    result["calls"] = extractor.calls

    return result


# ======================================================
# 4. Query the KG based on error type + symbols
# ======================================================

def _resolve_class_from_imports(obj_name, imports):
    """Try to map a variable/alias name to a known KG class.

    For example, if imports contain ("pandas", "pd") and code has
    pd.DataFrame(...), then obj_name="pd" resolves through the alias
    to look up known pandas classes.

    This also handles direct class names like "DataFrame".
    """
    # Direct lookup: the object name IS a class name in the KG
    if obj_name in KG["classes"]:
        return obj_name

    # Check if the object is an alias for a library, then skip
    # (e.g., pd is an alias for pandas -- not a class itself)
    # The attr access is what matters, handled by the caller.

    return None


def query_kg(error_type, error_info, parsed_symbols):
    """Dispatch to the appropriate suggestion engine(s).

    Returns a list of suggestion dicts.
    """
    suggestions = []
    msg = str(error_info.get("error_message", ""))
    status = str(error_info.get("status", ""))
    combined_msg = msg or status

    # Also consider libapi_details if provided
    libapi_details = error_info.get("libapi_details", [])
    if isinstance(libapi_details, str):
        try:
            libapi_details = json.loads(libapi_details)
        except (json.JSONDecodeError, TypeError):
            libapi_details = []

    if error_type == "NameError":
        # From error message
        symbol = detect_name_error(combined_msg)
        if symbol:
            suggestions.extend(suggest_name(symbol))

        # Also try names from the error region's calls that aren't in KG
        for call_name in parsed_symbols.get("calls", []):
            if call_name not in KG["functions"] and call_name not in KG["classes"]:
                suggestions.extend(suggest_name(call_name))

        # From libapi_details
        for detail in libapi_details:
            if detail.get("type") == "name_error":
                name = detail.get("name", "")
                if name and name != symbol:
                    suggestions.extend(suggest_name(name))

    elif error_type == "AttributeError":
        # From error message
        parsed = detect_attribute_error(combined_msg)
        if parsed:
            cls, attr = parsed
            suggestions.extend(suggest_attribute(cls, attr))

        # From AST-extracted attributes in the error region
        for obj_name, attr_name in parsed_symbols.get("attributes", []):
            resolved = _resolve_class_from_imports(obj_name, parsed_symbols.get("imports", []))
            if resolved:
                suggestions.extend(suggest_attribute(resolved, attr_name))

        # From libapi_details
        for detail in libapi_details:
            if detail.get("type") == "attribute_error":
                obj = detail.get("object", "")
                attr = detail.get("attribute", "")
                if obj and attr:
                    suggestions.extend(suggest_attribute(obj, attr))

    elif error_type == "TypeError":
        # From error message
        func = detect_type_error(combined_msg)
        if func:
            suggestions.extend(suggest_type(func))

        # From calls in the error region
        for call_name in parsed_symbols.get("calls", []):
            if call_name in KG["functions"]:
                suggestions.extend(suggest_type(call_name))

        # From libapi_details
        for detail in libapi_details:
            if detail.get("type") == "type_error":
                fn = detail.get("function", "")
                if fn:
                    suggestions.extend(suggest_type(fn))

    elif error_type == "ModuleNotFoundError":
        # From error message
        mod = detect_module_not_found(combined_msg)
        if mod:
            suggestions.extend(suggest_module(mod))

        # From imports in the error region
        for mod_name, _ in parsed_symbols.get("imports", []):
            top_level = mod_name.split(".")[0]
            if top_level not in KG["libraries"]:
                suggestions.extend(suggest_module(top_level))

        # From libapi_details
        for detail in libapi_details:
            if detail.get("type") == "module_not_found":
                mod_name = detail.get("module", "")
                if mod_name:
                    suggestions.extend(suggest_module(mod_name))

    # Deduplicate by api name
    seen = set()
    unique = []
    for s in suggestions:
        key = s.get("api", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


# ======================================================
# 5. Format context for LLM prompt
# ======================================================

def _format_suggestion(i, s):
    """Format a single suggestion dict into readable text."""
    lines = [f"{i}. {s['api']} ({s['type']})"]

    if s.get("required_params"):
        lines.append(f"   - Required params: {', '.join(s['required_params'])}")
    if s.get("optional_params"):
        lines.append(f"   - Optional params: {', '.join(s['optional_params'])}")
    if s.get("belongs_to"):
        lines.append(f"   - Belongs to: {s['belongs_to']}")
    if s.get("methods"):
        lines.append(f"   - Methods: {', '.join(s['methods'][:5])}")
    if s.get("attributes"):
        lines.append(f"   - Attributes: {', '.join(s['attributes'][:5])}")
    if s.get("parent"):
        lines.append(f"   - Parent: {s['parent']}")
    if s.get("description"):
        lines.append(f"   - Description: {s['description']}")

    return "\n".join(lines)


def format_context(error_region_info, error_type, suggestions):
    """Build a human-readable context_summary string for LLM prompt injection.

    Args:
        error_region_info: dict from extract_error_region()
        error_type: str
        suggestions: list of suggestion dicts

    Returns:
        str - formatted text block
    """
    parts = []

    parts.append(f"Error Type: {error_type}")
    parts.append("")

    if error_region_info.get("region"):
        parts.append("Error Region:")
        for line in error_region_info["region"].split("\n"):
            parts.append(f"  {line}")
        parts.append("")

    if error_region_info.get("context_before"):
        parts.append("Context Before Error:")
        for line in error_region_info["context_before"].split("\n"):
            parts.append(f"  {line}")
        parts.append("")

    if suggestions:
        parts.append("KG API Suggestions:")
        for i, s in enumerate(suggestions, 1):
            parts.append(_format_suggestion(i, s))
            parts.append("")
    else:
        parts.append("No KG suggestions found for this error.")
        parts.append("")

    return "\n".join(parts).strip()


# ======================================================
# Public API
# ======================================================

def get_repair_context(code, error_info):
    """Given error-marked code and error details, return KG-based context for LLM repair.

    Args:
        code (str): Python code with [ERROR START] / [ERROR END] markers
            around the buggy region.
        error_info (dict): Error metadata with keys:
            - error_type (str): e.g. "NameError", "AttributeError",
              "TypeError", "ModuleNotFoundError"
            - error_message (str): the full error message
            - status (str, optional): combined status string
              (e.g. "Failed: NameError: name 'foo' is not defined")
            - libapi_details (list[dict] | str, optional): structured
              error details from hallucination_master_table.csv

    Returns:
        dict with:
            - error_region (str): code between the markers
            - error_type (str): classified error category
            - suggestions (list[dict]): KG API suggestions with
              signatures, params, descriptions
            - context_summary (str): formatted text block ready to
              inject into an LLM repair prompt
    """
    # Step 1: Extract error region
    region_info = extract_error_region(code)

    # Step 2: Classify error
    error_type = classify_error(error_info)

    # Step 3: AST-analyze the error region (plus full code for import context)
    # Strip markers from full code before parsing
    clean_code = _MARKER_RE.sub(lambda m: m.group(1), code)
    parsed_symbols = analyze_error_region(region_info["region"], clean_code)

    # Step 4: Query the KG
    suggestions = query_kg(error_type, error_info, parsed_symbols)

    # Step 5: Format context summary
    context_summary = format_context(region_info, error_type, suggestions)

    return {
        "error_region": region_info["region"],
        "error_type": error_type,
        "suggestions": suggestions,
        "context_summary": context_summary,
    }
