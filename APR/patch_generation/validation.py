"""
Validate that a GeneratedPatch has well-formed markers before sending to LLM.
"""
from __future__ import annotations

from .schema import GeneratedPatch, Hunk


def validate_patch(patch: GeneratedPatch) -> bool:
    """
    Ensure markers are well-formed: exactly one START/END pair per hunk,
    matching error types, original lines present between START and =======.
    """
    hunks = patch.get("hunks") or []
    for hunk in hunks:
        marked = hunk.get("marked_representation", "")
        error_type = hunk.get("error_type", "")

        if marked.count("<<<<<<< [ERROR START:") != 1:
            return False
        if marked.count(">>>>>>> [ERROR END:") != 1:
            return False
        if marked.count("=======") != 1:
            return False

        # Error types must match
        try:
            start_part = marked.split("<<<<<<< [ERROR START: ")[1]
            start_type = start_part.split("]")[0].strip()
            end_part = marked.split(">>>>>>> [ERROR END: ")[1]
            end_type = end_part.split("]")[0].strip()
            if start_type != end_type or start_type != error_type:
                return False
        except (IndexError, AttributeError):
            return False

        # Original lines must appear between START and =======
        left_block = marked.split("=======")[0]
        original_lines = hunk.get("original_lines") or []
        original_joined = "\n".join(original_lines)
        if original_joined and original_joined not in left_block:
            return False

    return True
