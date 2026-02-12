"""
Patch generation request/response types (TypedDicts).
Transforms APRInput into GeneratedPatch with explicit error markers.
"""
from __future__ import annotations

from typing import List, Literal, Optional, TypedDict

# Re-use SourceLocation from APR input schema
from ..input.schema import APRInput, SourceLocation


# -----------------------------------------------------------------------------
# Patch strategy
# -----------------------------------------------------------------------------


class PatchStrategy(TypedDict, total=False):
    mode: Literal["single_hunk", "multi_hunk", "full_replacement"]
    error_focus: Literal["static_first", "dynamic_first", "hybrid"]
    include_suggestions: bool


# -----------------------------------------------------------------------------
# Patch generation request
# -----------------------------------------------------------------------------


class PatchGenerationRequest(TypedDict, total=False):
    apr_input: APRInput
    patch_strategy: PatchStrategy
    context_lines: int


# -----------------------------------------------------------------------------
# Hunk and patch output
# -----------------------------------------------------------------------------


class Hunk(TypedDict, total=False):
    hunk_id: str
    error_type: str
    location: SourceLocation
    original_lines: List[str]
    marked_representation: str
    severity: Literal["critical", "major", "minor"]
    fix_suggestion: Optional[str]


class PatchMetadata(TypedDict, total=False):
    total_hunks: int
    critical_hunks: int
    strategy_used: str
    marker_format_version: str


class GeneratedPatch(TypedDict, total=False):
    patch_id: str
    task_id: str
    original_code: str
    patched_code: str
    hunks: List[Hunk]
    metadata: PatchMetadata
