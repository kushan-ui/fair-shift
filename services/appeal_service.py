"""
Counterfactual Appeal Service for FAIRSHIFT.
Evaluates the mathematical impact of forcing an appealed seat assignment
against an immutable baseline allocation.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from models.appeal import Appeal, AppealAnalysisResult
from database.repositories import AppealRepository, AllocationRepository, ApplicantRepository, ProgramRepository
from optimizer.solver_service import SolverService
from validation.allocation_validator import AllocationValidator
from services.audit_service import AuditService

class AppealService:
    @staticmethod
    def submit_appeal(
        applicant_id: str,
        requested_program_id: str,
        reason: str,
        baseline_version_id: Optional[str] = None
    ) -> Appeal:
        if not applicant_id:
            raise ValueError("Applicant ID is required.")
        if not requested_program_id:
            raise ValueError("Requested Program ID is required.")
        if not reason or not reason.strip():
            raise ValueError("Appeal justification reason is required.")

        baseline = None
        if baseline_version_id:
            baseline = AllocationRepository.get_version(baseline_version_id)
        else:
            baseline = AllocationRepository.get_latest_committed_version()

        if not baseline:
            raise ValueError("No valid committed baseline allocation exists to appeal against.")

        applicant = ApplicantRepository.get_by_id(applicant_id)
        if not applicant:
            raise ValueError(f"Applicant '{applicant_id}' does not exist.")

        program = ProgramRepository.get_by_id(requested_program_id)
        if not program:
            raise ValueError(f"Program '{requested_program_id}' does not exist.")

        appeal_id = f"APL-{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        appeal = Appeal(
            id=appeal_id,
            applicant_id=applicant_id,
            requested_program_id=requested_program_id,
            reason=reason.strip(),
            baseline_version_id=baseline.id,
            status="PENDING",
            created_at=now
        )
        AppealRepository.create_appeal(appeal)

        AuditService.log(
            event_type="APPEAL_SUBMITTED",
            outcome="SUCCESS",
            details={
                "appeal_id": appeal_id,
                "applicant_id": applicant_id,
                "requested_program_id": requested_program_id,
                "baseline_version_id": baseline.id
            },
            applicant_id=applicant_id,
            program_id=requested_program_id,
            version_id=baseline.id
        )

        return appeal

    @staticmethod
    def run_counterfactual_analysis(appeal_id: str, time_limit_seconds: int = 15) -> AppealAnalysisResult:
        appeal = AppealRepository.get_appeal(appeal_id)
        if not appeal:
            raise ValueError(f"Appeal '{appeal_id}' not found.")

        baseline = AllocationRepository.get_version(appeal.baseline_version_id)
        if not baseline:
            raise ValueError(f"Baseline version '{appeal.baseline_version_id}' not found.")

        applicants = ApplicantRepository.get_all(include_withdrawn=True)
        programs = ProgramRepository.get_all(include_inactive=True)

        app = ApplicantRepository.get_by_id(appeal.applicant_id)
        prog = ProgramRepository.get_by_id(appeal.requested_program_id)

        # Baseline assignment map
        baseline_asgn_map = {a.applicant_id: a.program_id for a in baseline.assignments if a.is_valid}

        # Pre-check eligibility
        is_eligible = True
        eligibility_notes = []
        if prog and prog.required_attributes:
            app_attrs = set(app.eligibility_attributes or [])
            missing = [r for r in prog.required_attributes if r not in app_attrs]
            if missing:
                is_eligible = False
                eligibility_notes.append(f"Applicant lacks required attributes: {missing}")

        if not is_eligible:
            analysis = AppealAnalysisResult(
                id=f"RES-{uuid.uuid4().hex[:8]}",
                appeal_id=appeal.id,
                solver_status="INFEASIBLE",
                is_accommodatable=False,
                solve_duration_sec=0.01,
                affected_applicants_count=0,
                affected_applicant_ids=[],
                preference_change_score=0.0,
                impact_summary=f"Infeasible: Applicant does not satisfy program eligibility requirements ({', '.join(eligibility_notes)}).",
                created_at=datetime.utcnow().isoformat()
            )
            AppealRepository.save_analysis(analysis)
            AuditService.log(
                event_type="APPEAL_ANALYZED",
                outcome="INFEASIBLE_INELIGIBLE",
                details={"appeal_id": appeal.id, "reason": "Lacks required attributes"},
                applicant_id=appeal.applicant_id,
                program_id=appeal.requested_program_id,
                version_id=baseline.id
            )
            return analysis

        # Run counterfactual model: Force applicant_id -> requested_program_id
        # and anchor on other baseline assignments to minimize ripple effect
        opt_output = SolverService.run_allocation(
            applicants=applicants,
            programs=programs,
            existing_assignments=baseline_asgn_map,
            enforced_assignments={appeal.applicant_id: appeal.requested_program_id},
            policy="LEXICOGRAPHIC_PREFERENCE_FIRST",
            time_limit_seconds=time_limit_seconds
        )

        is_accommodatable = (opt_output.solver_status in ("OPTIMAL", "FEASIBLE"))
        affected_ids = []
        alt_asgn_map = {a.applicant_id: a.program_id for a in opt_output.assignments}

        if is_accommodatable:
            # Check validation
            val_result = AllocationValidator.validate(opt_output.assignments, applicants, programs)
            if not val_result.is_valid:
                is_accommodatable = False
                impact_summary = f"Accommodating request violated system constraints: {len(val_result.violations)} errors found."
            else:
                # Find affected applicants (excluding the appellant)
                for a_id, p_id in baseline_asgn_map.items():
                    if a_id != appeal.applicant_id and alt_asgn_map.get(a_id) != p_id:
                        affected_ids.append(a_id)

                delta_pref = opt_output.preference_score - baseline.preference_satisfaction_score
                delta_unassigned = opt_output.total_unassigned - baseline.total_unassigned

                impact_summary = (
                    f"Accommodatable ({opt_output.solver_status}). "
                    f"Accommodating this request alters assignments for {len(affected_ids)} other applicant(s). "
                    f"Net preference utility shift: {delta_pref:+.1f} points. "
                    f"Net unassigned applicant shift: {delta_unassigned:+d} applicant(s)."
                )
        else:
            if opt_output.solver_status == "INFEASIBLE":
                impact_summary = "Proven Infeasible: The program capacity or hard constraints cannot accommodate this assignment without violating rules."
            elif opt_output.solver_status == "UNKNOWN":
                impact_summary = f"Unresolved / Timeout: The solver reached the {time_limit_seconds}s limit without proving feasibility or infeasibility."
            else:
                impact_summary = f"Optimization failed with solver status {opt_output.solver_status}."

        analysis = AppealAnalysisResult(
            id=f"RES-{uuid.uuid4().hex[:8]}",
            appeal_id=appeal.id,
            solver_status=opt_output.solver_status,
            is_accommodatable=is_accommodatable,
            solve_duration_sec=opt_output.solve_duration_sec,
            affected_applicants_count=len(affected_ids),
            affected_applicant_ids=affected_ids,
            preference_change_score=opt_output.preference_score - baseline.preference_satisfaction_score if is_accommodatable else 0.0,
            impact_summary=impact_summary,
            created_at=datetime.utcnow().isoformat()
        )
        AppealRepository.save_analysis(analysis)

        AuditService.log(
            event_type="APPEAL_ANALYZED",
            outcome=opt_output.solver_status,
            details={
                "appeal_id": appeal.id,
                "accommodatable": is_accommodatable,
                "affected_count": len(affected_ids),
                "solver_status": opt_output.solver_status
            },
            applicant_id=appeal.applicant_id,
            program_id=appeal.requested_program_id,
            version_id=baseline.id
        )

        return analysis

    @staticmethod
    def record_decision(appeal_id: str, decision: str, explanation: str) -> None:
        if decision not in ("APPROVED", "REJECTED"):
            raise ValueError("Decision must be either APPROVED or REJECTED.")
        if not explanation or not explanation.strip():
            raise ValueError("An explicit administrative justification is required for appeal decisions.")

        appeal = AppealRepository.get_appeal(appeal_id)
        if not appeal:
            raise ValueError(f"Appeal '{appeal_id}' not found.")

        AppealRepository.update_decision(appeal_id, decision, explanation.strip())
        AuditService.log(
            event_type="APPEAL_DECISION",
            outcome=decision,
            details={"appeal_id": appeal_id, "decision": decision, "explanation": explanation.strip()},
            applicant_id=appeal.applicant_id,
            program_id=appeal.requested_program_id,
            version_id=appeal.baseline_version_id
        )

    @staticmethod
    def get_all_appeals() -> List[Dict[str, Any]]:
        return AppealRepository.get_all_appeals()

    @staticmethod
    def get_appeal_details(appeal_id: str) -> Tuple[Optional[Appeal], Optional[AppealAnalysisResult]]:
        app = AppealRepository.get_appeal(appeal_id)
        res = AppealRepository.get_analysis(appeal_id) if app else None
        return app, res
