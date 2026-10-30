"""
Allocation Service for coordinating CP-SAT optimization, independent validation,
historical versioning, and commit workflows.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from models.applicant import Applicant
from models.program import Program
from models.allocation import AllocationVersion, Assignment
from database.repositories import ApplicantRepository, ProgramRepository, AllocationRepository
from optimizer.solver_service import SolverService
from validation.allocation_validator import AllocationValidator, ValidationResult
from services.audit_service import AuditService

class AllocationService:
    @staticmethod
    def generate_allocation(
        name: str = "",
        policy: str = "LEXICOGRAPHIC_PREFERENCE_FIRST",
        use_baseline_as_anchor: bool = False,
        baseline_version_id: Optional[str] = None,
        time_limit_seconds: int = 15,
        random_seed: int = 42,
        auto_commit: bool = True
    ) -> Tuple[AllocationVersion, ValidationResult]:
        """
        Executes CP-SAT allocation solver, independently validates the result,
        and saves version records with full audit trail.
        """
        applicants = ApplicantRepository.get_all(include_withdrawn=True)
        programs = ProgramRepository.get_all(include_inactive=True)

        existing_assignments: Dict[str, str] = {}
        parent_id = None

        if use_baseline_as_anchor:
            baseline = None
            if baseline_version_id:
                baseline = AllocationRepository.get_version(baseline_version_id)
            else:
                baseline = AllocationRepository.get_latest_committed_version()

            if baseline:
                parent_id = baseline.id
                existing_assignments = {a.applicant_id: a.program_id for a in baseline.assignments if a.is_valid}

        # Run CP-SAT solver
        opt_output = SolverService.run_allocation(
            applicants=applicants,
            programs=programs,
            existing_assignments=existing_assignments,
            policy=policy,
            time_limit_seconds=time_limit_seconds,
            random_seed=random_seed
        )

        version_num = AllocationRepository.get_next_version_number()
        version_id = f"VER-{uuid.uuid4().hex[:8]}"
        ver_name = name or f"Allocation Run v{version_num}"

        # Assign version ID to generated assignments
        for asgn in opt_output.assignments:
            asgn.version_id = version_id

        # Independent Validation
        if opt_output.solver_status in ("OPTIMAL", "FEASIBLE"):
            val_result = AllocationValidator.validate(
                assignments=opt_output.assignments,
                applicants=applicants,
                programs=programs
            )
        else:
            val_result = ValidationResult(
                status="FAIL",
                violations=[],
                total_assignments_checked=0,
                assigned_applicants_count=0
            )

        is_validated = (val_result.status == "PASS")
        status = "COMMITTED" if (auto_commit and is_validated) else "DRAFT"

        # Build Version Model
        version = AllocationVersion(
            id=version_id,
            version_number=version_num,
            name=ver_name,
            status=status,
            policy=policy,
            solver_status=opt_output.solver_status,
            solve_duration_sec=opt_output.solve_duration_sec,
            preference_satisfaction_score=opt_output.preference_score,
            total_assigned=opt_output.total_assigned,
            total_unassigned=opt_output.total_unassigned,
            assignments_changed=opt_output.assignments_changed,
            is_validated=is_validated,
            validation_result=val_result.status,
            created_at=datetime.utcnow().isoformat(),
            parent_version_id=parent_id,
            solver_metadata=opt_output.metadata,
            assignments=opt_output.assignments
        )

        # Persist version and assignments
        AllocationRepository.create_version(version)
        if opt_output.assignments:
            AllocationRepository.save_assignments(opt_output.assignments)

        # Audit Log
        AuditService.log(
            event_type="ALLOCATION_RUN",
            outcome="SUCCESS" if is_validated else "FAILED_VALIDATION" if opt_output.solver_status in ("OPTIMAL", "FEASIBLE") else opt_output.solver_status,
            details={
                "version_number": version_num,
                "solver_status": opt_output.solver_status,
                "validation_status": val_result.status,
                "assigned": opt_output.total_assigned,
                "unassigned": opt_output.total_unassigned,
                "score": opt_output.preference_score,
                "duration": opt_output.solve_duration_sec,
                "violations_count": len(val_result.violations)
            },
            version_id=version_id
        )

        return version, val_result

    @staticmethod
    def commit_version(version_id: str) -> AllocationVersion:
        version = AllocationRepository.get_version(version_id)
        if not version:
            raise ValueError(f"Allocation version '{version_id}' not found.")

        if not version.is_validated or version.validation_result != "PASS":
            raise ValueError("Cannot commit an allocation version that has not passed independent validation.")

        AllocationRepository.commit_version(version_id)
        version.status = "COMMITTED"

        AuditService.log(
            event_type="ALLOCATION_COMMITTED",
            outcome="SUCCESS",
            details={"version_id": version_id, "version_number": version.version_number},
            version_id=version_id
        )
        return version

    @staticmethod
    def get_latest_committed() -> Optional[AllocationVersion]:
        return AllocationRepository.get_latest_committed_version()

    @staticmethod
    def get_version(version_id: str) -> Optional[AllocationVersion]:
        return AllocationRepository.get_version(version_id)

    @staticmethod
    def get_all_versions() -> List[AllocationVersion]:
        return AllocationRepository.get_all_versions()

    @staticmethod
    def compare_versions(version_a_id: str, version_b_id: str) -> Dict[str, Any]:
        """Compares two allocation versions and identifies individual applicant shifts."""
        ver_a = AllocationRepository.get_version(version_a_id)
        ver_b = AllocationRepository.get_version(version_b_id)
        if not ver_a or not ver_b:
            raise ValueError("One or both allocation versions could not be found.")

        map_a: Dict[str, Assignment] = {asgn.applicant_id: asgn for asgn in ver_a.assignments}
        map_b: Dict[str, Assignment] = {asgn.applicant_id: asgn for asgn in ver_b.assignments}

        all_app_ids = sorted(list(set(map_a.keys()) | set(map_b.keys())))
        changes = []
        preserved = 0

        for app_id in all_app_ids:
            asgn_a = map_a.get(app_id)
            asgn_b = map_b.get(app_id)

            prog_a = asgn_a.program_id if asgn_a else "UNASSIGNED"
            rank_a = asgn_a.preference_rank if asgn_a else None
            prog_b = asgn_b.program_id if asgn_b else "UNASSIGNED"
            rank_b = asgn_b.preference_rank if asgn_b else None

            if prog_a == prog_b and prog_a != "UNASSIGNED":
                preserved += 1
            elif prog_a != prog_b:
                changes.append({
                    "applicant_id": app_id,
                    "previous_program": prog_a,
                    "previous_rank": rank_a,
                    "new_program": prog_b,
                    "new_rank": rank_b,
                    "change_type": "GAINED_SEAT" if prog_a == "UNASSIGNED" else ("LOST_SEAT" if prog_b == "UNASSIGNED" else "REASSIGNED")
                })

        return {
            "version_a": {"id": ver_a.id, "number": ver_a.version_number, "name": ver_a.name, "assigned": ver_a.total_assigned},
            "version_b": {"id": ver_b.id, "number": ver_b.version_number, "name": ver_b.name, "assigned": ver_b.total_assigned},
            "preserved_count": preserved,
            "changed_count": len(changes),
            "changes": changes
        }
