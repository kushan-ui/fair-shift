"""
Audit Service for recording append-only operational events and audit log lookups.
"""

from typing import Dict, Any, Optional, List
from database.repositories import AuditRepository

class AuditService:
    @staticmethod
    def log(
        event_type: str,
        outcome: str,
        details: Dict[str, Any],
        applicant_id: Optional[str] = None,
        program_id: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> str:
        return AuditRepository.log(
            event_type=event_type,
            outcome=outcome,
            details=details,
            applicant_id=applicant_id,
            program_id=program_id,
            version_id=version_id
        )

    @staticmethod
    def get_logs(
        limit: int = 200,
        event_type: Optional[str] = None,
        applicant_id: Optional[str] = None,
        program_id: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return AuditRepository.get_logs(
            limit=limit,
            event_type=event_type,
            applicant_id=applicant_id,
            program_id=program_id,
            version_id=version_id
        )
