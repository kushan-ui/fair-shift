"""
Reassignment Simulation Service for hypothetical scenario modeling without mutating production data.
"""

from typing import List, Dict, Any, Optional, Tuple
from models.applicant import Applicant
from models.program import Program
from models.allocation import AllocationVersion, Assignment
from database.repositories import ApplicantRepository, ProgramRepository, AllocationRepository
from optimizer.solver_service import SolverService
from validation.allocation_validator import AllocationValidator, ValidationResult
from services.allocation_service import AllocationService

class ReassignmentService:
    @staticmethod
    def simulate_scenario(
        baseline_version_id: str,
        capacity_overrides: Optional[Dict[str, int]] = None,
        withdrawn_applicant_ids: Optional[List[str]] = None,
        reactivated_applicant_ids: Optional[List[str]] = None,
        inactive_program_ids: Optional[List[str]] = None,
        policy: str = "LEXICOGRAPHIC_PREFERENCE_FIRST",
        time_limit_seconds: int = 15
    ) -> Dict[str, Any]:
        """
        Runs a simulation sandbox on top of a baseline allocation.
        Does NOT commit changes or alter production database records.
        """
        baseline = AllocationRepository.get_version(baseline_version_id)
        if not baseline:
            raise ValueError(f"Baseline version '{baseline_version_id}' not found.")

        # Load fresh copies of applicants and programs
        applicants = ApplicantRepository.get_all(include_withdrawn=True)
        programs = ProgramRepository.get_all(include_inactive=True)

        capacity_overrides = capacity_overrides or {}
        withdrawn_ids = set(withdrawn_applicant_ids or [])
        reactivated_ids = set(reactivated_applicant_ids or [])
        inactive_progs = set(inactive_program_ids or [])

        # Apply sandbox overrides in memory
        sim_applicants = []
        for app in applicants:
            is_withdrawn = app.is_withdrawn
            status = app.status
            if app.id in withdrawn_ids:
                is_withdrawn = True
                status = "WITHDRAWN"
            elif app.id in reactivated_ids:
                is_withdrawn = False
                status = "ACTIVE"

            sim_applicants.append(Applicant(
                id=app.id,
                full_name=app.full_name,
                email=app.email,
                eligibility_attributes=list(app.eligibility_attributes),
                status=status,
                is_withdrawn=is_withdrawn,
                created_at=app.created_at,
                preferences=list(app.preferences)
            ))

        sim_programs = []
        for prog in programs:
            cap = capacity_overrides.get(prog.id, prog.capacity)
            is_active = False if prog.id in inactive_progs else prog.is_active
            sim_programs.append(Program(
                id=prog.id,
                name=prog.name,
                description=prog.description,
                capacity=cap,
                required_attributes=list(prog.required_attributes),
                is_active=is_active,
                created_at=prog.created_at
            ))

        baseline_assignment_map = {a.applicant_id: a for a in baseline.assignments if a.is_valid}
        existing_assignments_dict = {a.applicant_id: a.program_id for a in baseline.assignments if a.is_valid}

        # Run solver with existing assignments for stability
        opt_output = SolverService.run_allocation(
            applicants=sim_applicants,
            programs=sim_programs,
            existing_assignments=existing_assignments_dict,
            policy=policy,
            time_limit_seconds=time_limit_seconds
        )

        # Independent Validation of Scenario Output
        val_result = AllocationValidator.validate(
            assignments=opt_output.assignments,
            applicants=sim_applicants,
            programs=sim_programs
        )

        new_assignment_map = {a.applicant_id: a for a in opt_output.assignments}
        all_app_ids = sorted(list(set(baseline_assignment_map.keys()) | set(new_assignment_map.keys()) | {a.id for a in sim_applicants}))

        comparison_rows = []
        preserved_count = 0
        changed_count = 0

        sim_prog_map = {p.id: p for p in sim_programs}
        sim_app_map = {a.id: a for a in sim_applicants}

        for app_id in all_app_ids:
            old_asgn = baseline_assignment_map.get(app_id)
            new_asgn = new_assignment_map.get(app_id)
            app = sim_app_map.get(app_id)

            old_prog_id = old_asgn.program_id if old_asgn else "UNASSIGNED"
            old_rank = old_asgn.preference_rank if old_asgn else None
            new_prog_id = new_asgn.program_id if new_asgn else "UNASSIGNED"
            new_rank = new_asgn.preference_rank if new_asgn else None

            # Check if previous assignment was still valid under simulated conditions
            was_still_valid = False
            reason_for_change = "Preserved"
            if old_asgn and app:
                prog = sim_prog_map.get(old_asgn.program_id)
                eligible = prog and all(req in set(app.eligibility_attributes) for req in prog.required_attributes)
                active = prog and prog.is_active
                not_withdrawn = not app.is_withdrawn
                was_still_valid = bool(eligible and active and not_withdrawn)

            if old_prog_id == new_prog_id:
                if old_prog_id != "UNASSIGNED":
                    preserved_count += 1
                    reason_for_change = "Confirmed assignment preserved."
                else:
                    reason_for_change = "Remained unassigned."
            else:
                changed_count += 1
                if app and app.is_withdrawn:
                    reason_for_change = "Applicant was withdrawn."
                elif old_prog_id != "UNASSIGNED" and not was_still_valid:
                    reason_for_change = "Previous program became inactive, ineligible, or eliminated."
                elif old_prog_id == "UNASSIGNED" and new_prog_id != "UNASSIGNED":
                    reason_for_change = f"Assigned to {new_prog_id} (Rank {new_rank})."
                elif old_prog_id != "UNASSIGNED" and new_prog_id == "UNASSIGNED":
                    reason_for_change = "Displaced due to capacity constraint / priority trade-off."
                else:
                    reason_for_change = f"Reassigned from {old_prog_id} to {new_prog_id}."

                comparison_rows.append({
                    "applicant_id": app_id,
                    "applicant_name": app.full_name if app else "Unknown",
                    "previous_program": old_prog_id,
                    "previous_rank": old_rank,
                    "new_program": new_prog_id,
                    "new_rank": new_rank,
                    "previous_was_valid": was_still_valid,
                    "reason_for_change": reason_for_change
                })

        return {
            "baseline_version_id": baseline.id,
            "baseline_version_number": baseline.version_number,
            "solver_status": opt_output.solver_status,
            "solve_duration_sec": opt_output.solve_duration_sec,
            "validation_status": val_result.status,
            "validation_violations": [v.description for v in val_result.violations],
            "total_assigned": opt_output.total_assigned,
            "total_unassigned": opt_output.total_unassigned,
            "baseline_assigned": baseline.total_assigned,
            "baseline_unassigned": baseline.total_unassigned,
            "preference_score": opt_output.preference_score,
            "baseline_preference_score": baseline.preference_satisfaction_score,
            "preserved_count": preserved_count,
            "changed_count": changed_count,
            "comparison_rows": comparison_rows,
            "sim_assignments": opt_output.assignments,
            "sim_programs": sim_programs,
            "sim_applicants": sim_applicants
        }
