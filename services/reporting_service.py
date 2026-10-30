"""
Reporting and Analytics Service for FAIRSHIFT.
Aggregates live database metrics, preference satisfaction rates, capacity utilization,
and exportable summaries.
"""

from typing import Dict, Any, List, Optional
from database.repositories import (
    ApplicantRepository, ProgramRepository, AllocationRepository,
    AppealRepository, AuditRepository
)

class ReportingService:
    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        """Calculates live metrics from actual database tables."""
        applicants = ApplicantRepository.get_all(include_withdrawn=True)
        programs = ProgramRepository.get_all(include_inactive=True)
        latest_ver = AllocationRepository.get_latest_committed_version()
        appeals = AppealRepository.get_all_appeals()
        capacity_history = ProgramRepository.get_capacity_history()

        total_applicants = len(applicants)
        active_applicants = sum(1 for a in applicants if not a.is_withdrawn and a.status != "WITHDRAWN")
        withdrawn_applicants = total_applicants - active_applicants

        total_programs = len(programs)
        active_programs = sum(1 for p in programs if p.is_active)
        total_capacity = sum(p.capacity for p in programs if p.is_active)

        pending_appeals = sum(1 for ap in appeals if ap["status"] == "PENDING")

        assigned_applicants = 0
        unassigned_applicants = active_applicants
        available_seats = total_capacity
        first_pref_satisfied = 0
        top_three_satisfied = 0
        assignments_changed = 0
        last_allocation_time = None
        solver_status = "NONE"
        validation_result = "NONE"

        program_enrollments: Dict[str, int] = {p.id: 0 for p in programs}
        preference_distribution: Dict[str, int] = {
            "1st Choice": 0,
            "2nd Choice": 0,
            "3rd Choice": 0,
            "4th+ Choice": 0,
            "Unassigned": active_applicants
        }

        if latest_ver:
            assigned_applicants = latest_ver.total_assigned
            unassigned_applicants = latest_ver.total_unassigned
            available_seats = max(0, total_capacity - assigned_applicants)
            assignments_changed = latest_ver.assignments_changed
            last_allocation_time = latest_ver.created_at
            solver_status = latest_ver.solver_status
            validation_result = latest_ver.validation_result

            for asgn in latest_ver.assignments:
                program_enrollments[asgn.program_id] = program_enrollments.get(asgn.program_id, 0) + 1
                if asgn.preference_rank == 1:
                    first_pref_satisfied += 1
                    preference_distribution["1st Choice"] += 1
                elif asgn.preference_rank == 2:
                    top_three_satisfied += 1
                    preference_distribution["2nd Choice"] += 1
                elif asgn.preference_rank == 3:
                    top_three_satisfied += 1
                    preference_distribution["3rd Choice"] += 1
                elif asgn.preference_rank and asgn.preference_rank >= 4:
                    preference_distribution["4th+ Choice"] += 1

            # Include 1st choice in top 3
            top_three_satisfied += first_pref_satisfied
            preference_distribution["Unassigned"] = unassigned_applicants

        first_pref_rate = (first_pref_satisfied / active_applicants * 100) if active_applicants > 0 else 0.0
        top_three_rate = (top_three_satisfied / active_applicants * 100) if active_applicants > 0 else 0.0

        # Program capacity table data
        program_summary = []
        for p in programs:
            enrolled = program_enrollments.get(p.id, 0)
            remaining = max(0, p.capacity - enrolled)
            utilization = (enrolled / p.capacity * 100) if p.capacity > 0 else 0.0
            program_summary.append({
                "program_id": p.id,
                "name": p.name,
                "capacity": p.capacity,
                "enrolled": enrolled,
                "remaining_seats": remaining,
                "utilization_pct": round(utilization, 1),
                "is_active": p.is_active
            })

        recent_logs = AuditRepository.get_logs(limit=10)

        return {
            "total_applicants": total_applicants,
            "active_applicants": active_applicants,
            "withdrawn_applicants": withdrawn_applicants,
            "total_programs": total_programs,
            "active_programs": active_programs,
            "total_capacity": total_capacity,
            "assigned_applicants": assigned_applicants,
            "unassigned_applicants": unassigned_applicants,
            "available_seats": available_seats,
            "first_pref_satisfied": first_pref_satisfied,
            "first_pref_rate": round(first_pref_rate, 1),
            "top_three_satisfied": top_three_satisfied,
            "top_three_rate": round(top_three_rate, 1),
            "assignments_changed": assignments_changed,
            "pending_appeals": pending_appeals,
            "last_allocation_time": last_allocation_time,
            "solver_status": solver_status,
            "validation_result": validation_result,
            "program_summary": program_summary,
            "preference_distribution": preference_distribution,
            "recent_capacity_changes": capacity_history[:5],
            "recent_audit_logs": recent_logs,
            "latest_version": latest_ver
        }

    @staticmethod
    def get_assignment_table_data(version_id: Optional[str] = None) -> List[Dict[str, Any]]:
        ver = AllocationRepository.get_version(version_id) if version_id else AllocationRepository.get_latest_committed_version()
        if not ver:
            return []

        applicants = {a.id: a for a in ApplicantRepository.get_all(include_withdrawn=True)}
        programs = {p.id: p for p in ProgramRepository.get_all(include_inactive=True)}

        rows = []
        for a in ver.assignments:
            app = applicants.get(a.applicant_id)
            prog = programs.get(a.program_id)
            rows.append({
                "Applicant ID": a.applicant_id,
                "Applicant Name": app.full_name if app else "Unknown",
                "Assigned Program ID": a.program_id,
                "Program Name": prog.name if prog else "Unknown",
                "Preference Rank": a.preference_rank if a.preference_rank else "Unranked",
                "Status": "Confirmed" if a.is_valid else "Invalid",
                "Assigned At": a.assigned_at
            })
        return rows
