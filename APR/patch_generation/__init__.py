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

# KG integration (optional - gracefully handle if not available)
try:
    from .kg_integration import (
        ErrorSignature,
        build_kg_context,
        detect_library,
        extract_error_signatures,
        query_kg_for_errors,
        score_kg_relevance,
    )
    KG_INTEGRATION_AVAILABLE = True
except ImportError:
    KG_INTEGRATION_AVAILABLE = False
    ErrorSignature = None  # type: ignore
    build_kg_context = None  # type: ignore
    detect_library = None  # type: ignore
    extract_error_signatures = None  # type: ignore
    query_kg_for_errors = None  # type: ignore
    score_kg_relevance = None  # type: ignore


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
    # KG integration
    "ErrorSignature",
    "build_kg_context",
    "detect_library",
    "extract_error_signatures",
    "query_kg_for_errors",
    "score_kg_relevance",
    "KG_INTEGRATION_AVAILABLE",
]
