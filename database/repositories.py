"""
Repository layer for FAIRSHIFT.
Encapsulates all database queries and updates with parameterized SQL.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from database.db import get_db_cursor
from models.applicant import Applicant, Preference
from models.program import Program
from models.allocation import AllocationVersion, Assignment
from models.appeal import Appeal, AppealAnalysisResult

class ApplicantRepository:
    @staticmethod
    def get_all(include_withdrawn: bool = True) -> List[Applicant]:
        query = "SELECT id, full_name, email, eligibility_attributes, status, is_withdrawn, created_at FROM applicants"
        if not include_withdrawn:
            query += " WHERE is_withdrawn = 0 AND status != 'WITHDRAWN'"
        query += " ORDER BY id ASC"

        with get_db_cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            applicants = []
            for r in rows:
                attrs = json.loads(r["eligibility_attributes"] or "[]")
                app = Applicant(
                    id=r["id"],
                    full_name=r["full_name"],
                    email=r["email"] or "",
                    eligibility_attributes=attrs,
                    status=r["status"],
                    is_withdrawn=bool(r["is_withdrawn"]),
                    created_at=r["created_at"]
                )
                applicants.append(app)

            # Load preferences for all
            cursor.execute("SELECT applicant_id, program_id, preference_rank FROM applicant_preferences ORDER BY preference_rank ASC")
            pref_rows = cursor.fetchall()
            prefs_by_app: Dict[str, List[Preference]] = {}
            for pr in pref_rows:
                prefs_by_app.setdefault(pr["applicant_id"], []).append(
                    Preference(program_id=pr["program_id"], preference_rank=pr["preference_rank"])
                )

            for app in applicants:
                app.preferences = prefs_by_app.get(app.id, [])

            return applicants

    @staticmethod
    def get_by_id(applicant_id: str) -> Optional[Applicant]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, full_name, email, eligibility_attributes, status, is_withdrawn, created_at FROM applicants WHERE id = ?", (applicant_id,))
            row = cursor.fetchone()
            if not row:
                return None
            attrs = json.loads(row["eligibility_attributes"] or "[]")
            app = Applicant(
                id=row["id"],
                full_name=row["full_name"],
                email=row["email"] or "",
                eligibility_attributes=attrs,
                status=row["status"],
                is_withdrawn=bool(row["is_withdrawn"]),
                created_at=row["created_at"]
            )
            cursor.execute("SELECT program_id, preference_rank FROM applicant_preferences WHERE applicant_id = ? ORDER BY preference_rank ASC", (applicant_id,))
            for pr in cursor.fetchall():
                app.preferences.append(Preference(program_id=pr["program_id"], preference_rank=pr["preference_rank"]))
            return app

    @staticmethod
    def create(applicant: Applicant) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """INSERT INTO applicants (id, full_name, email, eligibility_attributes, status, is_withdrawn, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    applicant.id,
                    applicant.full_name,
                    applicant.email,
                    json.dumps(applicant.eligibility_attributes),
                    applicant.status,
                    1 if applicant.is_withdrawn else 0,
                    applicant.created_at
                )
            )
            for p in applicant.preferences:
                cursor.execute(
                    "INSERT INTO applicant_preferences (applicant_id, program_id, preference_rank) VALUES (?, ?, ?)",
                    (applicant.id, p.program_id, p.preference_rank)
                )

    @staticmethod
    def update(applicant: Applicant) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """UPDATE applicants
                   SET full_name = ?, email = ?, eligibility_attributes = ?, status = ?, is_withdrawn = ?
                   WHERE id = ?""",
                (
                    applicant.full_name,
                    applicant.email,
                    json.dumps(applicant.eligibility_attributes),
                    applicant.status,
                    1 if applicant.is_withdrawn else 0,
                    applicant.id
                )
            )
            cursor.execute("DELETE FROM applicant_preferences WHERE applicant_id = ?", (applicant.id,))
            for p in applicant.preferences:
                cursor.execute(
                    "INSERT INTO applicant_preferences (applicant_id, program_id, preference_rank) VALUES (?, ?, ?)",
                    (applicant.id, p.program_id, p.preference_rank)
                )

    @staticmethod
    def set_withdrawn(applicant_id: str, is_withdrawn: bool) -> None:
        status = "WITHDRAWN" if is_withdrawn else "ACTIVE"
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE applicants SET is_withdrawn = ?, status = ? WHERE id = ?",
                (1 if is_withdrawn else 0, status, applicant_id)
            )

    @staticmethod
    def bulk_create(applicants: List[Applicant]) -> None:
        with get_db_cursor(commit=True) as cursor:
            for a in applicants:
                cursor.execute(
                    """INSERT OR REPLACE INTO applicants (id, full_name, email, eligibility_attributes, status, is_withdrawn, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        a.id,
                        a.full_name,
                        a.email,
                        json.dumps(a.eligibility_attributes),
                        a.status,
                        1 if a.is_withdrawn else 0,
                        a.created_at
                    )
                )
                cursor.execute("DELETE FROM applicant_preferences WHERE applicant_id = ?", (a.id,))
                for p in a.preferences:
                    cursor.execute(
                        "INSERT INTO applicant_preferences (applicant_id, program_id, preference_rank) VALUES (?, ?, ?)",
                        (a.id, p.program_id, p.preference_rank)
                    )


class ProgramRepository:
    @staticmethod
    def get_all(include_inactive: bool = True) -> List[Program]:
        query = "SELECT id, name, description, capacity, required_attributes, is_active, created_at FROM programs"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY id ASC"

        with get_db_cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            programs = []
            for r in rows:
                reqs = json.loads(r["required_attributes"] or "[]")
                programs.append(Program(
                    id=r["id"],
                    name=r["name"],
                    description=r["description"] or "",
                    capacity=r["capacity"],
                    required_attributes=reqs,
                    is_active=bool(r["is_active"]),
                    created_at=r["created_at"]
                ))
            return programs

    @staticmethod
    def get_by_id(program_id: str) -> Optional[Program]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, name, description, capacity, required_attributes, is_active, created_at FROM programs WHERE id = ?", (program_id,))
            r = cursor.fetchone()
            if not r:
                return None
            reqs = json.loads(r["required_attributes"] or "[]")
            return Program(
                id=r["id"],
                name=r["name"],
                description=r["description"] or "",
                capacity=r["capacity"],
                required_attributes=reqs,
                is_active=bool(r["is_active"]),
                created_at=r["created_at"]
            )

    @staticmethod
    def create(program: Program) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """INSERT INTO programs (id, name, description, capacity, required_attributes, is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    program.id,
                    program.name,
                    program.description,
                    program.capacity,
                    json.dumps(program.required_attributes),
                    1 if program.is_active else 0,
                    program.created_at
                )
            )

    @staticmethod
    def update(program: Program) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """UPDATE programs
                   SET name = ?, description = ?, capacity = ?, required_attributes = ?, is_active = ?
                   WHERE id = ?""",
                (
                    program.name,
                    program.description,
                    program.capacity,
                    json.dumps(program.required_attributes),
                    1 if program.is_active else 0,
                    program.id
                )
            )

    @staticmethod
    def update_capacity(program_id: str, new_capacity: int, reason: str = "") -> None:
        if new_capacity < 0:
            raise ValueError("Capacity must be a non-negative integer.")

        with get_db_cursor(commit=True) as cursor:
            cursor.execute("SELECT capacity FROM programs WHERE id = ?", (program_id,))
            row = cursor.fetchone()
            old_cap = row["capacity"] if row else 0

            cursor.execute("UPDATE programs SET capacity = ? WHERE id = ?", (new_capacity, program_id))
            history_id = f"CAP-{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow().isoformat()
            cursor.execute(
                """INSERT INTO capacity_change_history (id, program_id, old_capacity, new_capacity, reason, changed_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (history_id, program_id, old_cap, new_capacity, reason, now)
            )

    @staticmethod
    def get_capacity_history(program_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """SELECT h.id, h.program_id, p.name as program_name, h.old_capacity, h.new_capacity, h.reason, h.changed_at
                   FROM capacity_change_history h
                   JOIN programs p ON h.program_id = p.id"""
        params = ()
        if program_id:
            query += " WHERE h.program_id = ?"
            params = (program_id,)
        query += " ORDER BY h.changed_at DESC"

        with get_db_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]


class AllocationRepository:
    @staticmethod
    def get_next_version_number() -> int:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT MAX(version_number) as max_v FROM allocation_versions")
            row = cursor.fetchone()
            if row and row["max_v"] is not None:
                return row["max_v"] + 1
            return 1

    @staticmethod
    def create_version(version: AllocationVersion) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """INSERT INTO allocation_versions
                   (id, version_number, name, status, policy, solver_status, solve_duration_sec,
                    preference_satisfaction_score, total_assigned, total_unassigned, assignments_changed,
                    is_validated, validation_result, created_at, parent_version_id, solver_metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    version.id,
                    version.version_number,
                    version.name,
                    version.status,
                    version.policy,
                    version.solver_status,
                    version.solve_duration_sec,
                    version.preference_satisfaction_score,
                    version.total_assigned,
                    version.total_unassigned,
                    version.assignments_changed,
                    1 if version.is_validated else 0,
                    version.validation_result,
                    version.created_at,
                    version.parent_version_id,
                    json.dumps(version.solver_metadata)
                )
            )

    @staticmethod
    def save_assignments(assignments: List[Assignment]) -> None:
        with get_db_cursor(commit=True) as cursor:
            for a in assignments:
                cursor.execute(
                    """INSERT OR REPLACE INTO assignments (id, version_id, applicant_id, program_id, preference_rank, is_valid, assigned_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (a.id, a.version_id, a.applicant_id, a.program_id, a.preference_rank, 1 if a.is_valid else 0, a.assigned_at)
                )

    @staticmethod
    def get_version(version_id: str) -> Optional[AllocationVersion]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM allocation_versions WHERE id = ?", (version_id,))
            r = cursor.fetchone()
            if not r:
                return None
            ver = AllocationVersion(
                id=r["id"],
                version_number=r["version_number"],
                name=r["name"],
                status=r["status"],
                policy=r["policy"],
                solver_status=r["solver_status"],
                solve_duration_sec=r["solve_duration_sec"],
                preference_satisfaction_score=r["preference_satisfaction_score"],
                total_assigned=r["total_assigned"],
                total_unassigned=r["total_unassigned"],
                assignments_changed=r["assignments_changed"],
                is_validated=bool(r["is_validated"]),
                validation_result=r["validation_result"],
                created_at=r["created_at"],
                parent_version_id=r["parent_version_id"],
                solver_metadata=json.loads(r["solver_metadata"] or "{}")
            )
            cursor.execute("SELECT * FROM assignments WHERE version_id = ? ORDER BY applicant_id ASC", (version_id,))
            ver.assignments = [
                Assignment(
                    id=a["id"],
                    version_id=a["version_id"],
                    applicant_id=a["applicant_id"],
                    program_id=a["program_id"],
                    preference_rank=a["preference_rank"],
                    is_valid=bool(a["is_valid"]),
                    assigned_at=a["assigned_at"]
                ) for a in cursor.fetchall()
            ]
            return ver

    @staticmethod
    def get_latest_committed_version() -> Optional[AllocationVersion]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id FROM allocation_versions WHERE status = 'COMMITTED' ORDER BY version_number DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return AllocationRepository.get_version(row["id"])

    @staticmethod
    def get_all_versions() -> List[AllocationVersion]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM allocation_versions ORDER BY version_number DESC")
            versions = []
            for r in cursor.fetchall():
                ver = AllocationVersion(
                    id=r["id"],
                    version_number=r["version_number"],
                    name=r["name"],
                    status=r["status"],
                    policy=r["policy"],
                    solver_status=r["solver_status"],
                    solve_duration_sec=r["solve_duration_sec"],
                    preference_satisfaction_score=r["preference_satisfaction_score"],
                    total_assigned=r["total_assigned"],
                    total_unassigned=r["total_unassigned"],
                    assignments_changed=r["assignments_changed"],
                    is_validated=bool(r["is_validated"]),
                    validation_result=r["validation_result"],
                    created_at=r["created_at"],
                    parent_version_id=r["parent_version_id"],
                    solver_metadata=json.loads(r["solver_metadata"] or "{}")
                )
                versions.append(ver)
            return versions

    @staticmethod
    def commit_version(version_id: str) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("UPDATE allocation_versions SET status = 'COMMITTED' WHERE id = ?", (version_id,))


class AppealRepository:
    @staticmethod
    def create_appeal(appeal: Appeal) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """INSERT INTO appeals (id, applicant_id, requested_program_id, reason, baseline_version_id, status, decision, decision_explanation, created_at, decided_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (appeal.id, appeal.applicant_id, appeal.requested_program_id, appeal.reason, appeal.baseline_version_id,
                 appeal.status, appeal.decision, appeal.decision_explanation, appeal.created_at, appeal.decided_at)
            )

    @staticmethod
    def get_all_appeals() -> List[Dict[str, Any]]:
        query = """SELECT a.*, ap.full_name as applicant_name, p.name as requested_program_name,
                          v.version_number as baseline_version_number
                   FROM appeals a
                   JOIN applicants ap ON a.applicant_id = ap.id
                   JOIN programs p ON a.requested_program_id = p.id
                   JOIN allocation_versions v ON a.baseline_version_id = v.id
                   ORDER BY a.created_at DESC"""
        with get_db_cursor() as cursor:
            cursor.execute(query)
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_appeal(appeal_id: str) -> Optional[Appeal]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM appeals WHERE id = ?", (appeal_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return Appeal(
                id=r["id"],
                applicant_id=r["applicant_id"],
                requested_program_id=r["requested_program_id"],
                reason=r["reason"],
                baseline_version_id=r["baseline_version_id"],
                status=r["status"],
                decision=r["decision"],
                decision_explanation=r["decision_explanation"],
                created_at=r["created_at"],
                decided_at=r["decided_at"]
            )

    @staticmethod
    def update_decision(appeal_id: str, decision: str, explanation: str) -> None:
        now = datetime.utcnow().isoformat()
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """UPDATE appeals
                   SET status = ?, decision = ?, decision_explanation = ?, decided_at = ?
                   WHERE id = ?""",
                ("APPROVED" if decision == "APPROVED" else "REJECTED", decision, explanation, now, appeal_id)
            )

    @staticmethod
    def save_analysis(res: AppealAnalysisResult) -> None:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """INSERT OR REPLACE INTO appeal_analysis_results
                   (id, appeal_id, solver_status, is_accommodatable, solve_duration_sec,
                    affected_applicants_count, affected_applicant_ids, preference_change_score,
                    impact_summary, alternative_version_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    res.id,
                    res.appeal_id,
                    res.solver_status,
                    1 if res.is_accommodatable else 0,
                    res.solve_duration_sec,
                    res.affected_applicants_count,
                    json.dumps(res.affected_applicant_ids),
                    res.preference_change_score,
                    res.impact_summary,
                    res.alternative_version_id,
                    res.created_at
                )
            )
            cursor.execute("UPDATE appeals SET status = 'ANALYZED' WHERE id = ? AND status = 'PENDING'", (res.appeal_id,))

    @staticmethod
    def get_analysis(appeal_id: str) -> Optional[AppealAnalysisResult]:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM appeal_analysis_results WHERE appeal_id = ? ORDER BY created_at DESC LIMIT 1", (appeal_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return AppealAnalysisResult(
                id=r["id"],
                appeal_id=r["appeal_id"],
                solver_status=r["solver_status"],
                is_accommodatable=bool(r["is_accommodatable"]),
                solve_duration_sec=r["solve_duration_sec"],
                affected_applicants_count=r["affected_applicants_count"],
                affected_applicant_ids=json.loads(r["affected_applicant_ids"] or "[]"),
                preference_change_score=r["preference_change_score"],
                impact_summary=r["impact_summary"],
                alternative_version_id=r["alternative_version_id"],
                created_at=r["created_at"]
            )


class AuditRepository:
    @staticmethod
    def log(event_type: str, outcome: str, details: Dict[str, Any],
            applicant_id: Optional[str] = None, program_id: Optional[str] = None,
            version_id: Optional[str] = None) -> str:
        log_id = f"AUD-{uuid.uuid4().hex[:10]}"
        now = datetime.utcnow().isoformat()
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(
                """INSERT INTO audit_logs (id, timestamp, event_type, applicant_id, program_id, allocation_version_id, details, outcome)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, now, event_type, applicant_id, program_id, version_id, json.dumps(details), outcome)
            )
        return log_id

    @staticmethod
    def get_logs(limit: int = 200, event_type: Optional[str] = None,
                 applicant_id: Optional[str] = None, program_id: Optional[str] = None,
                 version_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if applicant_id:
            query += " AND applicant_id = ?"
            params.append(applicant_id)
        if program_id:
            query += " AND program_id = ?"
            params.append(program_id)
        if version_id:
            query += " AND allocation_version_id = ?"
            params.append(version_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with get_db_cursor() as cursor:
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            logs = []
            for r in rows:
                item = dict(r)
                item["details"] = json.loads(item["details"] or "{}")
                logs.append(item)
            return logs
