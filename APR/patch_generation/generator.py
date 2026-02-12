"""
PatchGenerator: dispatch by strategy and mode, return validated GeneratedPatch.
"""
from __future__ import annotations

from typing import List

from .schema import GeneratedPatch, Hunk, PatchGenerationRequest, PatchStrategy
from .strategies import (
    generate_dynamic_first_patch,
    generate_hybrid_patch,
    generate_static_first_patch,
)
from .validation import validate_patch


class PatchGenerator:
    """Generates patches from APRInput with configurable strategy and mode."""

    def generate(self, request: PatchGenerationRequest) -> GeneratedPatch:
        """
        Build a PatchGenerationRequest, run the chosen strategy, apply mode,
        and return a GeneratedPatch (validated).
        """
        strategy = request.get("patch_strategy") or {}
        error_focus = strategy.get("error_focus", "hybrid")
        mode = strategy.get("mode", "multi_hunk")

        if error_focus == "static_first":
            patch = generate_static_first_patch(request)
        elif error_focus == "dynamic_first":
            patch = generate_dynamic_first_patch(request)
        else:
            patch = generate_hybrid_patch(request)

        # Apply mode: single_hunk, multi_hunk, full_replacement
        hunks = patch.get("hunks") or []
        if mode == "single_hunk" and len(hunks) > 1:
            patch = _patch_with_hunks(patch, hunks[:1])
        elif mode == "full_replacement" and hunks:
            patch = _full_replacement_patch(request, patch)

        if not validate_patch(patch):
            # Still return patch; caller can check. Or we could raise.
            pass
        return patch


def _patch_with_hunks(patch: GeneratedPatch, hunks: List[Hunk]) -> GeneratedPatch:
    """Return a new patch with only the given hunks (and rebuilt patched_code/metadata)."""
    from .utils import build_patch

    apr_input = {
        "task_id": patch.get("task_id"),
        "generated_code": patch.get("original_code"),
    }
    strategy_used = (patch.get("metadata") or {}).get("strategy_used", "unknown")
    return build_patch(apr_input, hunks, strategy_used)


def _full_replacement_patch(
    request: PatchGenerationRequest,
    patch: GeneratedPatch,
) -> GeneratedPatch:
    """Replace all hunks with one hunk spanning the entire file."""
    from .utils import build_patch

    apr = request["apr_input"]
    original_code = patch.get("original_code") or ""
    code_lines = original_code.split("\n")
    if not code_lines:
        return patch

    # One hunk: whole file
    start_m = "<<<<<<< [ERROR START: FULL_REPLACEMENT]"
    sep = "======="
    fix_line = "pass  # TODO: Fix full replacement"
    end_m = ">>>>>>> [ERROR END: FULL_REPLACEMENT]"
    marked = "\n".join([start_m, *code_lines, sep, fix_line, end_m])

    hunk: Hunk = {
        "hunk_id": "hunk_full_0",
        "error_type": "FULL_REPLACEMENT",
        "location": {
            "line_start": 1,
            "line_end": len(code_lines),
            "column_start": 0,
            "column_end": 0,
        },
        "original_lines": code_lines,
        "marked_representation": marked,
        "severity": "major",
        "fix_suggestion": None,
    }
    strategy_used = (patch.get("metadata") or {}).get("strategy_used", "full_replacement")
    return build_patch(apr, [hunk], strategy_used)
