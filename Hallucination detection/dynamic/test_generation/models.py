from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GeneratedTestCase:
    case_id: str
    code: str
    expected_repr: str
    args_expr: str
    input_repr: str
    test_design_method: str  # original | bva | ecp
    equivalence_class: Optional[str] = None
    boundary_kind: Optional[str] = None
    source: str = "generated"


@dataclass
class TestSpec:
    dataset: str
    task_id: Any
    entry_point: Optional[str]
    code: str
    prompt: str
    original_tests: List[GeneratedTestCase] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
