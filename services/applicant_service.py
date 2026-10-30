"""
Applicant Service for managing applicant registration, preferences, withdrawals, and updates.
"""

from typing import List, Optional, Dict, Any
from models.applicant import Applicant, Preference
from database.repositories import ApplicantRepository
from services.audit_service import AuditService

class ApplicantService:
    @staticmethod
    def get_all_applicants(include_withdrawn: bool = True) -> List[Applicant]:
        return ApplicantRepository.get_all(include_withdrawn=include_withdrawn)

    @staticmethod
    def get_applicant_by_id(applicant_id: str) -> Optional[Applicant]:
        return ApplicantRepository.get_by_id(applicant_id)

    @staticmethod
    def create_applicant(
        applicant_id: str,
        full_name: str,
        email: str = "",
        eligibility_attributes: Optional[List[str]] = None,
        preferences: Optional[List[Preference]] = None
    ) -> Applicant:
        if not applicant_id or not applicant_id.strip():
            raise ValueError("Applicant ID cannot be empty.")
        if not full_name or not full_name.strip():
            raise ValueError("Applicant full name cannot be empty.")

        existing = ApplicantRepository.get_by_id(applicant_id)
        if existing:
            raise ValueError(f"Applicant with ID '{applicant_id}' already exists.")

        applicant = Applicant(
            id=applicant_id.strip(),
            full_name=full_name.strip(),
            email=email.strip(),
            eligibility_attributes=eligibility_attributes or [],
            preferences=preferences or []
        )
        ApplicantRepository.create(applicant)
        AuditService.log(
            event_type="APPLICANT_CREATED",
            outcome="SUCCESS",
            details={"id": applicant.id, "name": applicant.full_name, "prefs_count": len(applicant.preferences)},
            applicant_id=applicant.id
        )
        return applicant

    @staticmethod
    def update_applicant(applicant: Applicant) -> None:
        ApplicantRepository.update(applicant)
        AuditService.log(
            event_type="APPLICANT_UPDATED",
            outcome="SUCCESS",
            details={"id": applicant.id, "name": applicant.full_name},
            applicant_id=applicant.id
        )

    @staticmethod
    def set_withdrawal_status(applicant_id: str, is_withdrawn: bool) -> None:
        app = ApplicantRepository.get_by_id(applicant_id)
        if not app:
            raise ValueError(f"Applicant '{applicant_id}' not found.")

        ApplicantRepository.set_withdrawn(applicant_id, is_withdrawn)
        event_name = "APPLICANT_WITHDRAWN" if is_withdrawn else "APPLICANT_REACTIVATED"
        AuditService.log(
            event_type=event_name,
            outcome="SUCCESS",
            details={"applicant_id": applicant_id, "is_withdrawn": is_withdrawn},
            applicant_id=applicant_id
        )
