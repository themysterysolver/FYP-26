"""
KG Integration for Patch Generation
------------------------------------
Extract error signatures, query KG, and assemble context for repair prompts.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, TypedDict

from ..input.schema import APRInput
from .schema import GeneratedPatch, Hunk

try:
    # Try normal import first
    from ..DS_KG.engine import DSKGEngine, DSKGEntry
except (ImportError, ModuleNotFoundError):
    # Handle DS-KG hyphen issue - use importlib
    try:
        import importlib.util
        import os
        
        # Find the engine.py file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        engine_path = os.path.join(current_dir, "..", "DS-KG", "engine.py")
        
        if os.path.exists(engine_path):
            spec = importlib.util.spec_from_file_location("ds_kg_engine", engine_path)
            if spec and spec.loader:
                ds_kg_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ds_kg_module)
                DSKGEngine = ds_kg_module.DSKGEngine
                DSKGEntry = ds_kg_module.DSKGEntry
            else:
                DSKGEngine = None  # type: ignore
                DSKGEntry = None  # type: ignore
        else:
            DSKGEngine = None  # type: ignore
            DSKGEntry = None  # type: ignore
    except Exception:
        # Allow module to load even if engine not available yet
        DSKGEngine = None  # type: ignore
        DSKGEntry = None  # type: ignore


class ErrorSignature(TypedDict, total=False):
    """Structured error information for KG lookup."""
    error_type: str
    line_number: int
    api_name: Optional[str]
    library: Optional[str]
    api_calls: List[Dict[str, str]]  # For scope-based lookup


def detect_library(code: str) -> Optional[str]:
    """
    Detect which DS library is being used from imports.
    
    Args:
        code: Source code string
    
    Returns:
        Library name (numpy, pandas, etc.) or None
    """
    # Common library aliases
    library_patterns = {
        "numpy": [r"import\s+numpy", r"import\s+numpy\s+as\s+np", r"from\s+numpy"],
        "pandas": [r"import\s+pandas", r"import\s+pandas\s+as\s+pd", r"from\s+pandas"],
        "matplotlib": [r"import\s+matplotlib", r"from\s+matplotlib"],
        "seaborn": [r"import\s+seaborn", r"import\s+seaborn\s+as\s+sns", r"from\s+seaborn"],
        "scipy": [r"import\s+scipy", r"from\s+scipy"],
        "sklearn": [r"import\s+sklearn", r"from\s+sklearn"],
    }
    
    for library, patterns in library_patterns.items():
        for pattern in patterns:
            if re.search(pattern, code):
                return library
    
    return None


def extract_api_from_hunk(hunk: Hunk) -> Optional[str]:
    """
    Extract API name from hunk's original code.
    
    Args:
        hunk: Hunk with error information
    
    Returns:
        API name if found (e.g., "array", "DataFrame")
    """
    original_lines = hunk.get("original_lines", [])
    if not original_lines:
        return None
    
    # Join lines and look for API calls
    code = "\n".join(original_lines)
    
    # Pattern: object.method() or function()
    # Look for identifier followed by ( or .
    patterns = [
        r'\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # .method()
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',     # function()
        r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\[',     # array indexing
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, code)
        if matches:
            # Return first non-common name
            for match in matches:
                if match not in ["self", "print", "len", "str", "int", "float", "list", "dict"]:
                    return match
    
    return None


def extract_apis_in_scope(code: str, location: Dict[str, int]) -> List[Dict[str, str]]:
    """
    Extract API calls near the error location.
    
    Args:
        code: Full source code
        location: Error location with line_start, line_end
    
    Returns:
        List of API calls with library and name
    """
    line_start = location.get("line_start", 1)
    line_end = location.get("line_end", line_start)
    
    # Get surrounding lines (±5 lines)
    lines = code.split("\n")
    start_idx = max(0, line_start - 6)
    end_idx = min(len(lines), line_end + 5)
    
    scope_code = "\n".join(lines[start_idx:end_idx])
    
    # Extract API calls
    api_calls = []
    
    # Pattern: library.api() or alias.api()
    pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
    matches = re.findall(pattern, scope_code)
    
    for obj, method in matches:
        # Try to map to known libraries
        library = None
        if obj in ["np", "numpy"]:
            library = "numpy"
        elif obj in ["pd", "pandas"]:
            library = "pandas"
        elif obj in ["plt", "matplotlib"]:
            library = "matplotlib"
        elif obj in ["sns", "seaborn"]:
            library = "seaborn"
        
        api_calls.append({
            "object": obj,
            "name": method,
            "library": library or obj,
        })
    
    return api_calls[:5]  # Limit to 5 API calls


def extract_error_signatures(
    apr_input: APRInput,
    patch: GeneratedPatch
) -> List[ErrorSignature]:
    """
    Extract structured error info for KG lookup.
    
    Args:
        apr_input: Full APR input with code and analysis
        patch: Generated patch with hunks
    
    Returns:
        List of error signatures for KG queries
    """
    signatures: List[ErrorSignature] = []
    code = apr_input.get("generated_code", "")
    library = detect_library(code)
    
    for hunk in patch.get("hunks", []):
        sig: ErrorSignature = {
            "error_type": hunk.get("error_type", "UNKNOWN"),
            "line_number": hunk.get("location", {}).get("line_start", 1),
            "api_name": None,
            "library": library,
            "api_calls": [],
        }
        
        error_type = sig["error_type"]
        
        # Extract API name based on error type
        if error_type == "API_ERROR":
            # Use static_library_api if available
            static_lib = apr_input.get("static_library_api", {})
            api_calls = static_lib.get("api_calls", [])
            
            # Find API call at error line
            for api_call in api_calls:
                api_loc = api_call.get("location", {})
                if api_loc.get("line_start") == sig["line_number"]:
                    sig["api_name"] = api_call.get("method")
                    sig["library"] = api_call.get("library")
                    break
            
            # Fallback: extract from hunk
            if not sig["api_name"]:
                sig["api_name"] = extract_api_from_hunk(hunk)
        
        elif error_type == "UNDEFINED_NAME":
            # Check if undefined name is in static analysis
            static_ast = apr_input.get("static_ast", {})
            undefined_names = static_ast.get("undefined_names", [])
            
            for undef in undefined_names:
                undef_loc = undef.get("location", {})
                if undef_loc.get("line_start") == sig["line_number"]:
                    sig["api_name"] = undef.get("name")
                    break
        
        elif error_type in {"LOGIC_ERROR", "RUNTIME_ERROR"}:
            # Extract API calls from surrounding context
            location = hunk.get("location", {})
            sig["api_calls"] = extract_apis_in_scope(code, location)
        
        signatures.append(sig)
    
    return signatures


def query_kg_for_errors(
    kg_engine: Any,  # DSKGEngine
    signatures: List[ErrorSignature]
) -> List[Any]:  # List[DSKGEntry]
    """
    Query KG for each error signature.
    
    Args:
        kg_engine: Loaded DSKGEngine instance
        signatures: Error signatures to query
    
    Returns:
        List of relevant KG entries (deduplicated)
    """
    all_entries = []
    seen_paths = set()
    
    for sig in signatures:
        entries = []
        
        # Exact lookup for API errors with known library
        if sig.get("api_name") and sig.get("library"):
            entry = kg_engine.resolve_api_call(
                sig["library"],
                sig["api_name"]
            )
            if entry:
                entries.append(entry)
        
        # Fuzzy lookup for undefined names
        elif sig.get("api_name"):
            fuzzy_entries = kg_engine.get_by_name(sig["api_name"])
            entries.extend(fuzzy_entries[:3])  # Limit to 3 fuzzy matches
        
        # Lookup APIs in scope for logic/runtime errors
        elif sig.get("api_calls"):
            for api_call in sig["api_calls"]:
                lib = api_call.get("library")
                name = api_call.get("name")
                if lib and name:
                    entry = kg_engine.resolve_api_call(lib, name)
                    if entry:
                        entries.append(entry)
        
        # Deduplicate by path
        for entry in entries:
            path = entry.get("path", "")
            if path and path not in seen_paths:
                all_entries.append(entry)
                seen_paths.add(path)
    
    return all_entries


def score_kg_relevance(
    entry: Any,  # DSKGEntry
    signatures: List[ErrorSignature]
) -> float:
    """
    Score KG entry relevance to error signatures.
    
    Args:
        entry: KG entry to score
        signatures: List of error signatures
    
    Returns:
        Relevance score (higher is better)
    """
    score = 0.0
    entry_name = entry.get("name", "")
    entry_lib = entry.get("library", "")
    is_deprecated = entry.get("deprecated", False)
    has_params = bool(entry.get("parameters", {}).get("required"))
    
    for sig in signatures:
        error_type = sig.get("error_type", "")
        
        # Direct name match
        if entry_name == sig.get("api_name"):
            score += 10.0
        
        # Deprecated APIs are critical for AttributeError
        if is_deprecated and "AttributeError" in error_type:
            score += 8.0
        
        # Parameter info is valuable for TypeError
        if has_params and "TypeError" in error_type:
            score += 5.0
        
        # Library match
        if entry_lib == sig.get("library"):
            score += 3.0
        
        # Check if entry is in scope API calls
        for api_call in sig.get("api_calls", []):
            if entry_name == api_call.get("name"):
                score += 4.0
    
    # Penalty for deprecated if not directly relevant
    if is_deprecated and score < 5.0:
        score -= 2.0
    
    return max(0.0, score)


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Simple heuristic: ~4 characters per token.
    
    Args:
        text: Text to estimate
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


def format_kg_entry(entry: Any) -> str:  # DSKGEntry -> str
    """
    Format single KG entry as concise markdown.
    
    Args:
        entry: KG entry to format
    
    Returns:
        Markdown string
    """
    lines = []
    
    # Header
    path = entry.get("path", entry.get("name", "unknown"))
    lines.append(f"### {path}")
    
    # Deprecation warning
    if entry.get("deprecated"):
        alternatives = entry.get("alternatives", [])
        if alternatives:
            alts = ", ".join(alternatives)
            lines.append(f"**DEPRECATED**: Use {alts} instead")
        else:
            lines.append("**DEPRECATED**")
    
    # Parameters
    params = entry.get("parameters", {})
    required = params.get("required", [])
    optional = params.get("optional", [])
    
    if required:
        lines.append(f"**Required**: {required}")
    if optional:
        # Limit optional params to avoid bloat
        if len(optional) > 5:
            lines.append(f"**Optional**: {optional[:5]} and {len(optional)-5} more")
        else:
            lines.append(f"**Optional**: {optional}")
    
    # Return type
    returns = entry.get("returns", "")
    if returns and returns != "unknown":
        lines.append(f"**Returns**: {returns}")
    
    # Description (truncated)
    description = entry.get("description", "")
    if description:
        # Take first sentence or first 100 chars
        desc_short = description.split(".")[0][:100]
        if desc_short:
            lines.append(desc_short)
    
    # Methods for classes (for AttributeError debugging)
    methods = entry.get("methods", [])
    if methods and entry.get("node_type") == "class":
        # Show first 10 methods
        method_list = ", ".join(methods[:10])
        if len(methods) > 10:
            method_list += f" (+{len(methods)-10} more)"
        lines.append(f"**Methods**: {method_list}")
    
    return "\n".join(lines)


def build_kg_context(
    entries: List[Any],  # List[DSKGEntry]
    error_signatures: List[ErrorSignature],
    token_budget: int = 800
) -> str:
    """
    Assemble KG entries into prompt text within token budget.
    
    Args:
        entries: KG entries to include
        error_signatures: Error signatures for relevance scoring
        token_budget: Maximum tokens to use
    
    Returns:
        Formatted KG context string
    """
    if not entries:
        return ""
    
    # Score and sort by relevance
    scored = []
    for entry in entries:
        score = score_kg_relevance(entry, error_signatures)
        scored.append((score, entry))
    
    scored.sort(reverse=True, key=lambda x: x[0])
    
    # Build context within budget
    parts = []
    current_tokens = 0
    header_tokens = estimate_tokens("## API Documentation\n\n")
    current_tokens += header_tokens
    
    for score, entry in scored:
        formatted = format_kg_entry(entry)
        entry_tokens = estimate_tokens(formatted) + 2  # +2 for newlines
        
        if current_tokens + entry_tokens > token_budget:
            # Add truncation notice if we hit budget
            if parts:  # Only if we added at least one entry
                parts.append("\n*(Additional API docs omitted for brevity)*")
            break
        
        parts.append(formatted)
        current_tokens += entry_tokens
    
    if not parts:
        return ""
    
    return "\n\n".join(parts)
