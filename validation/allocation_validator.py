"""
FAIRSHIFT - Independent Allocation Validator
Independent validation module completely separate from the optimization solver.
Verifies all mandatory hard constraints, referential integrity, and business rules.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Any, Optional
from models.applicant import Applicant
from models.program import Program
from models.allocation import Assignment

@dataclass
class ValidationViolation:
    rule_code: str
    description: str
    applicant_id: Optional[str] = None
    program_id: Optional[str] = None
    severity: str = "ERROR" # ERROR or WARNING

@dataclass
class ValidationResult:
    status: str # PASS or FAIL
    violations: List[ValidationViolation] = field(default_factory=list)
    total_assignments_checked: int = 0
    assigned_applicants_count: int = 0
    program_enrollment: Dict[str, int] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "violations_count": len(self.violations),
            "violations": [
                {
                    "rule_code": v.rule_code,
                    "description": v.description,
                    "applicant_id": v.applicant_id,
                    "program_id": v.program_id,
                    "severity": v.severity
                }
                for v in self.violations
            ],
            "total_assignments_checked": self.total_assignments_checked,
            "assigned_applicants_count": self.assigned_applicants_count,
            "program_enrollment": self.program_enrollment
        }

class AllocationValidator:
    """Independent validator checking raw assignments against ground truth applicant and program records."""

    @classmethod
    def validate(
        cls,
        assignments: List[Assignment],
        applicants: List[Applicant],
        programs: List[Program]
    ) -> ValidationResult:
        violations: List[ValidationViolation] = []

        applicant_map: Dict[str, Applicant] = {a.id: a for a in applicants}
        program_map: Dict[str, Program] = {p.id: p for p in programs}

        seen_applicants: Set[str] = set()
        seen_pairs: Set[str] = set()
        program_enrollment: Dict[str, int] = {p.id: 0 for p in programs}

        for asgn in assignments:
            pair_key = f"{asgn.applicant_id}::{asgn.program_id}"
            if pair_key in seen_pairs:
                violations.append(ValidationViolation(
                    rule_code="DUPLICATE_RECORD",
                    description=f"Duplicate assignment record detected for applicant {asgn.applicant_id} and program {asgn.program_id}.",
                    applicant_id=asgn.applicant_id,
                    program_id=asgn.program_id
                ))
            seen_pairs.add(pair_key)

            # Rule 1: No applicant has multiple active assignments
            if asgn.applicant_id in seen_applicants:
                violations.append(ValidationViolation(
                    rule_code="MULTIPLE_ASSIGNMENTS",
                    description=f"Applicant {asgn.applicant_id} is assigned multiple times within the same allocation version.",
                    applicant_id=asgn.applicant_id,
                    program_id=asgn.program_id
                ))
            seen_applicants.add(asgn.applicant_id)

            # Rule 2: References existing applicant
            app = applicant_map.get(asgn.applicant_id)
            if not app:
                violations.append(ValidationViolation(
                    rule_code="UNKNOWN_APPLICANT",
                    description=f"Assignment references unknown applicant ID '{asgn.applicant_id}'.",
                    applicant_id=asgn.applicant_id,
                    program_id=asgn.program_id
                ))
                continue

            # Rule 3: No withdrawn applicant has active assignment
            if app.is_withdrawn or app.status == "WITHDRAWN":
                violations.append(ValidationViolation(
                    rule_code="WITHDRAWN_APPLICANT_ASSIGNED",
                    description=f"Applicant {app.id} is marked as withdrawn/inactive but received an assignment to {asgn.program_id}.",
                    applicant_id=app.id,
                    program_id=asgn.program_id
                ))

            # Rule 4: References existing program
            prog = program_map.get(asgn.program_id)
            if not prog:
                violations.append(ValidationViolation(
                    rule_code="UNKNOWN_PROGRAM",
                    description=f"Assignment references unknown program ID '{asgn.program_id}'.",
                    applicant_id=asgn.applicant_id,
                    program_id=asgn.program_id
                ))
                continue

            # Rule 5: No inactive program receives assignment
            if not prog.is_active:
                violations.append(ValidationViolation(
                    rule_code="INACTIVE_PROGRAM_ASSIGNED",
                    description=f"Program {prog.id} ('{prog.name}') is marked INACTIVE but was assigned applicant {app.id}.",
                    applicant_id=app.id,
                    program_id=prog.id
                ))

            # Rule 6: No ineligible applicant is assigned
            if prog.required_attributes:
                applicant_attrs = set(app.eligibility_attributes or [])
                missing_attrs = [req for req in prog.required_attributes if req not in applicant_attrs]
                if missing_attrs:
                    violations.append(ValidationViolation(
                        rule_code="INELIGIBLE_APPLICANT_ASSIGNED",
                        description=f"Applicant {app.id} lacks required attributes {missing_attrs} for program {prog.id} ('{prog.name}').",
                        applicant_id=app.id,
                        program_id=prog.id
                    ))

            # Count enrollment
            program_enrollment[prog.id] = program_enrollment.get(prog.id, 0) + 1

            # Rule 7: Preference rank validity check
            pref_match = next((p for p in app.preferences if p.program_id == prog.id), None)
            if pref_match:
                if asgn.preference_rank is not None and asgn.preference_rank != pref_match.preference_rank:
                    violations.append(ValidationViolation(
                        rule_code="INVALID_PREFERENCE_RANK",
                        description=f"Applicant {app.id} assigned to {prog.id} has recorded rank {asgn.preference_rank}, but preference rank is {pref_match.preference_rank}.",
                        applicant_id=app.id,
                        program_id=prog.id,
                        severity="WARNING"
                    ))
            else:
                # Assigned to a program not even on preference list
                violations.append(ValidationViolation(
                    rule_code="UNLISTED_PROGRAM_ASSIGNED",
                    description=f"Applicant {app.id} was assigned to program {prog.id} which is not on their ranked preference list.",
                    applicant_id=app.id,
                    program_id=prog.id
                ))

        # Rule 8: Program capacity checks
        for prog_id, enrolled in program_enrollment.items():
            prog = program_map.get(prog_id)
            if prog and enrolled > prog.capacity:
                violations.append(ValidationViolation(
                    rule_code="CAPACITY_EXCEEDED",
                    description=f"Program {prog.id} ('{prog.name}') exceeded seat capacity! Capacity: {prog.capacity}, Enrolled: {enrolled}.",
                    program_id=prog.id
                ))

        has_critical_error = any(v.severity == "ERROR" for v in violations)
        status = "FAIL" if has_critical_error else "PASS"

        return ValidationResult(
            status=status,
            violations=violations,
            total_assignments_checked=len(assignments),
            assigned_applicants_count=len(seen_applicants),
            program_enrollment=program_enrollment
        )
