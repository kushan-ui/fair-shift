"""Allocation Version and Assignment models"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Assignment:
    id: str
    version_id: str
    applicant_id: str
    program_id: str
    preference_rank: Optional[int] = None
    is_valid: bool = True
    assigned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class AllocationVersion:
    id: str
    version_number: int
    name: str
    status: str # DRAFT, COMMITTED, CANCELLED
    policy: str # LEXICOGRAPHIC_PREFERENCE_FIRST, LEXICOGRAPHIC_STABILITY_FIRST, BALANCED
    solver_status: str # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID
    solve_duration_sec: float = 0.0
    preference_satisfaction_score: float = 0.0
    total_assigned: int = 0
    total_unassigned: int = 0
    assignments_changed: int = 0
    is_validated: bool = False
    validation_result: str = "PENDING"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    parent_version_id: Optional[str] = None
    solver_metadata: Dict[str, Any] = field(default_factory=dict)
    assignments: List[Assignment] = field(default_factory=list)
