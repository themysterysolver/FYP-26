"""
Patch generation: transform APRInput into GeneratedPatch with error markers for LLM repair.
"""
from .generator import PatchGenerator
from .prompts import REPAIR_PROMPT_TEMPLATE, build_repair_prompt, format_test_cases
from .schema import (
    GeneratedPatch,
    Hunk,
    PatchGenerationRequest,
    PatchMetadata,
    PatchStrategy,
)
from .validation import validate_patch


def generate_patch(request: PatchGenerationRequest) -> GeneratedPatch:
    """Convenience: generate a patch using default PatchGenerator."""
    return PatchGenerator().generate(request)


__all__ = [
    "PatchGenerator",
    "generate_patch",
    "GeneratedPatch",
    "Hunk",
    "PatchGenerationRequest",
    "PatchMetadata",
    "PatchStrategy",
    "validate_patch",
    "REPAIR_PROMPT_TEMPLATE",
    "build_repair_prompt",
    "format_test_cases",
]
