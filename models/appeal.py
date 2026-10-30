"""Appeal and Counterfactual Analysis models"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class Appeal:
    id: str
    applicant_id: str
    requested_program_id: str
    reason: str
    baseline_version_id: str
    status: str = "PENDING" # PENDING, ANALYZED, APPROVED, REJECTED
    decision: Optional[str] = None # APPROVED, REJECTED
    decision_explanation: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    decided_at: Optional[str] = None

@dataclass
class AppealAnalysisResult:
    id: str
    appeal_id: str
    solver_status: str
    is_accommodatable: bool
    solve_duration_sec: float = 0.0
    affected_applicants_count: int = 0
    affected_applicant_ids: List[str] = field(default_factory=list)
    preference_change_score: float = 0.0
    impact_summary: str = ""
    alternative_version_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
