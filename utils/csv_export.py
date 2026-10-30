"""
CSV Export utility for FAIRSHIFT
Exports applicants, programs, allocations, and audit logs to standardized CSV.
"""

import csv
import io
import json
from typing import List, Dict, Any
from models.applicant import Applicant
from models.program import Program
from models.allocation import AllocationVersion

def export_applicants_to_csv(applicants: List[Applicant]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "full_name", "email", "status", "is_withdrawn", "eligibility_attributes", "preferences"])

    for a in applicants:
        attrs_str = ";".join(a.eligibility_attributes)
        prefs_str = ";".join([p.program_id for p in sorted(a.preferences, key=lambda x: x.preference_rank)])
        writer.writerow([a.id, a.full_name, a.email, a.status, 1 if a.is_withdrawn else 0, attrs_str, prefs_str])

    return output.getvalue()


def export_programs_to_csv(programs: List[Program]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "capacity", "description", "required_attributes", "is_active"])

    for p in programs:
        reqs_str = ";".join(p.required_attributes)
        writer.writerow([p.id, p.name, p.capacity, p.description, reqs_str, 1 if p.is_active else 0])

    return output.getvalue()


def export_allocation_to_csv(version: AllocationVersion, applicants_map: Dict[str, Applicant], programs_map: Dict[str, Program]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "version_id", "version_number", "applicant_id", "applicant_name",
        "assigned_program_id", "program_name", "preference_rank", "is_valid", "assigned_at"
    ])

    for asgn in version.assignments:
        app = applicants_map.get(asgn.applicant_id)
        prog = programs_map.get(asgn.program_id)
        writer.writerow([
            version.id,
            version.version_number,
            asgn.applicant_id,
            app.full_name if app else "Unknown",
            asgn.program_id,
            prog.name if prog else "Unknown",
            asgn.preference_rank if asgn.preference_rank is not None else "",
            1 if asgn.is_valid else 0,
            asgn.assigned_at
        ])

    return output.getvalue()


def export_audit_logs_to_csv(logs: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "event_type", "applicant_id", "program_id", "allocation_version_id", "outcome", "details"])

    for l in logs:
        writer.writerow([
            l.get("id"),
            l.get("timestamp"),
            l.get("event_type"),
            l.get("applicant_id") or "",
            l.get("program_id") or "",
            l.get("allocation_version_id") or "",
            l.get("outcome"),
            json.dumps(l.get("details") or {})
        ])

    return output.getvalue()
