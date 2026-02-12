"""
Utilities for patch generation: markdown stripping, patch building, error localization.
"""
from __future__ import annotations

import re
import uuid
from typing import Any, List

from .schema import GeneratedPatch, Hunk, PatchMetadata
from ..input.schema import APRInput, DynamicResult


MARKER_FORMAT_VERSION = "1.0"


def strip_markdown_fences(code: str) -> str:
    """Remove markdown code fences (e.g. ```python ... ```) from generated code."""
    if not code or not code.strip():
        return code
    text = code.strip()
    # Match optional language and opening fence
    open_match = re.match(r"^```(?:\w*)\s*\n?", text)
    if open_match:
        text = text[open_match.end() :]
    if text.endswith("```"):
        text = text[: text.rfind("```")].rstrip()
    return text


def _extract_marker_block(marked_representation: str) -> str:
    """Extract the block from <<<<<<< to end of line containing >>>>>>> (inclusive) for insertion into patched_code."""
    start_marker = "<<<<<<<"
    end_marker = ">>>>>>>"
    start_idx = marked_representation.find(start_marker)
    end_idx = marked_representation.find(end_marker)
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        return marked_representation
    # Include full closing line (e.g. ">>>>>>> [ERROR END: LOGIC_ERROR]")
    after_end = end_idx + len(end_marker)
    newline = marked_representation.find("\n", after_end)
    end_idx = newline + 1 if newline != -1 else len(marked_representation)
    return marked_representation[start_idx:end_idx]


def build_patch(
    apr_input: APRInput,
    hunks: List[Hunk],
    strategy_used: str,
) -> GeneratedPatch:
    """Assemble GeneratedPatch from APR input and list of hunks."""
    original_code = strip_markdown_fences(apr_input.get("generated_code", "") or "")
    code_lines = original_code.split("\n")
    task_id = apr_input.get("task_id", "")

    # Sort hunks by line_start descending so we replace from bottom up and indices stay valid
    sorted_hunks = sorted(
        hunks,
        key=lambda h: (h.get("location") or {}).get("line_start", 0),
        reverse=True,
    )

    for h in sorted_hunks:
        loc = h.get("location") or {}
        line_start = loc.get("line_start", 1)
        line_end = loc.get("line_end", line_start)
        start_idx = max(0, line_start - 1)
        end_idx = min(len(code_lines), line_end)
        block = _extract_marker_block(h.get("marked_representation", ""))
        block_lines = block.split("\n")
        code_lines = code_lines[:start_idx] + block_lines + code_lines[end_idx:]

    patched_code = "\n".join(code_lines)
    critical_count = sum(1 for h in hunks if h.get("severity") == "critical")

    return {
        "patch_id": str(uuid.uuid4()),
        "task_id": task_id,
        "original_code": original_code,
        "patched_code": patched_code,
        "hunks": hunks,
        "metadata": {
            "total_hunks": len(hunks),
            "critical_hunks": critical_count,
            "strategy_used": strategy_used,
            "marker_format_version": MARKER_FORMAT_VERSION,
        },
    }


def parse_traceback_line(tb_line: str) -> int | None:
    """Parse a traceback line for file path and line number; return 1-based line number or None."""
    # Format: "  File \"path\", line N, in ..."
    match = re.search(r'line\s+(\d+)', tb_line, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def localize_error_by_traceback(
    code_lines: List[str],
    traceback: List[str] | None,
    failing_test: dict[str, Any] | None,
) -> int:
    """Infer 1-based error line from traceback; fallback to estimate."""
    if traceback:
        for line in reversed(traceback):
            line_no = parse_traceback_line(line)
            if line_no is not None and 1 <= line_no <= len(code_lines):
                return line_no
    return estimate_error_line(code_lines, None)


def estimate_error_line(code_lines: List[str], dynamic_result: DynamicResult | None) -> int:
    """Estimate 1-based line when traceback is missing (e.g. middle of code)."""
    if not code_lines:
        return 1
    # Prefer middle of file as a rough guess
    return (len(code_lines) // 2) + 1


def find_function_end_line(code_lines: List[str], function_name: str) -> int | None:
    """
    Heuristic: find 1-based line after the last line of the function body.
    Looks for 'def function_name' then next 'def' at same indent or EOF.
    Returns None if function not found.
    """
    import re
    pattern = re.compile(r"^\s*def\s+" + re.escape(function_name) + r"\s*\(")
    def_start = None
    base_indent = None
    for i, line in enumerate(code_lines):
        if pattern.match(line):
            def_start = i + 1  # 1-based
            # Indent of function body (next non-empty line)
            for j in range(i + 1, len(code_lines)):
                if code_lines[j].strip():
                    base_indent = len(code_lines[j]) - len(code_lines[j].lstrip())
                    break
            break
    if def_start is None:
        return None
    if base_indent is None:
        return min(def_start + 1, len(code_lines))
    # Find next line with same or less indent (next def or end of block)
    for i in range(def_start, len(code_lines)):  # def_start is 1-based, so line index i
        idx = i  # 0-based
        if idx >= len(code_lines):
            break
        stripped = code_lines[idx].strip()
        if not stripped:
            continue
        current_indent = len(code_lines[idx]) - len(code_lines[idx].lstrip())
        if current_indent <= base_indent and stripped.startswith("def "):
            return max(def_start, i - 1)  # 1-based: last line of function body (before next def)
    return len(code_lines)  # EOF: last line of file is end of function
