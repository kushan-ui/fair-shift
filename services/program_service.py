"""
Program Service for managing training programs, capacities, and eligibility requirements.
"""

from typing import List, Optional, Dict, Any
from models.program import Program
from database.repositories import ProgramRepository, AllocationRepository
from services.audit_service import AuditService

class ProgramService:
    @staticmethod
    def get_all_programs(include_inactive: bool = True) -> List[Program]:
        return ProgramRepository.get_all(include_inactive=include_inactive)

    @staticmethod
    def get_program_by_id(program_id: str) -> Optional[Program]:
        return ProgramRepository.get_by_id(program_id)

    @staticmethod
    def create_program(
        program_id: str,
        name: str,
        capacity: int,
        description: str = "",
        required_attributes: Optional[List[str]] = None
    ) -> Program:
        if not program_id or not program_id.strip():
            raise ValueError("Program ID cannot be empty.")
        if not name or not name.strip():
            raise ValueError("Program name cannot be empty.")
        if capacity < 0:
            raise ValueError("Program capacity must be greater than or equal to 0.")

        existing = ProgramRepository.get_by_id(program_id)
        if existing:
            raise ValueError(f"Program with ID '{program_id}' already exists.")

        program = Program(
            id=program_id.strip(),
            name=name.strip(),
            capacity=capacity,
            description=description.strip(),
            required_attributes=required_attributes or []
        )
        ProgramRepository.create(program)
        AuditService.log(
            event_type="PROGRAM_CREATED",
            outcome="SUCCESS",
            details={"id": program.id, "name": program.name, "capacity": program.capacity},
            program_id=program.id
        )
        return program

    @staticmethod
    def update_program(program: Program) -> None:
        ProgramRepository.update(program)
        AuditService.log(
            event_type="PROGRAM_UPDATED",
            outcome="SUCCESS",
            details={"id": program.id, "name": program.name, "capacity": program.capacity},
            program_id=program.id
        )

    @staticmethod
    def change_capacity(program_id: str, new_capacity: int, reason: str = "") -> Dict[str, Any]:
        if new_capacity < 0:
            raise ValueError("Capacity must be non-negative.")

        prog = ProgramRepository.get_by_id(program_id)
        if not prog:
            raise ValueError(f"Program '{program_id}' not found.")

        old_capacity = prog.capacity

        # Check latest committed version to detect if current enrollment exceeds new capacity
        latest_ver = AllocationRepository.get_latest_committed_version()
        current_enrollment = 0
        warning_message = None
        if latest_ver:
            current_enrollment = sum(1 for a in latest_ver.assignments if a.program_id == program_id)
            if new_capacity < current_enrollment:
                warning_message = (
                    f"Warning: New capacity ({new_capacity}) is lower than current committed enrollment "
                    f"({current_enrollment}). A reallocation is strongly recommended to resolve over-subscription."
                )

        ProgramRepository.update_capacity(program_id, new_capacity, reason)
        AuditService.log(
            event_type="CAPACITY_CHANGED",
            outcome="SUCCESS",
            details={"program_id": program_id, "old_capacity": old_capacity, "new_capacity": new_capacity, "reason": reason},
            program_id=program_id
        )

        return {
            "program_id": program_id,
            "old_capacity": old_capacity,
            "new_capacity": new_capacity,
            "current_enrollment": current_enrollment,
            "warning": warning_message
        }

    @staticmethod
    def get_capacity_history(program_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return ProgramRepository.get_capacity_history(program_id=program_id)
