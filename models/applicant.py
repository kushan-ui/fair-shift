"""Applicant domain model"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
import json
from datetime import datetime

@dataclass
class Preference:
    program_id: str
    preference_rank: int

@dataclass
class Applicant:
    id: str
    full_name: str
    email: str = ""
    eligibility_attributes: List[str] = field(default_factory=list)
    status: str = "ACTIVE"
    is_withdrawn: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    preferences: List[Preference] = field(default_factory=list)

    @property
    def is_eligible_for(self, required_attributes: List[str]) -> bool:
        if not required_attributes:
            return True
        applicant_attrs = set(self.eligibility_attributes)
        return all(req in applicant_attrs for req in required_attributes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "eligibility_attributes": self.eligibility_attributes,
            "status": self.status,
            "is_withdrawn": int(self.is_withdrawn),
            "created_at": self.created_at,
            "preferences": [{"program_id": p.program_id, "rank": p.preference_rank} for p in self.preferences]
        }
