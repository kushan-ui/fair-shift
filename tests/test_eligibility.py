"""
Tests proving that eligibility constraints are strictly enforced:
Ineligible applicants must never receive an active seat assignment.
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from optimizer.solver_service import SolverService
from validation.allocation_validator import AllocationValidator

def test_ineligible_applicant_is_not_assigned():
    # Program requires LIFE_SCIENCES
    prog = Program(
        id="PROG-BIO",
        name="Bioinformatics",
        capacity=5,
        required_attributes=["LIFE_SCIENCES"]
    )

    # Applicant only has STEM, lacks LIFE_SCIENCES
    app1 = Applicant(
        id="APP-NO-BIO",
        full_name="Bob Brown",
        eligibility_attributes=["STEM"],
        preferences=[Preference(program_id="PROG-BIO", preference_rank=1)]
    )

    # Applicant has LIFE_SCIENCES
    app2 = Applicant(
        id="APP-HAS-BIO",
        full_name="Carol White",
        eligibility_attributes=["LIFE_SCIENCES", "STEM"],
        preferences=[Preference(program_id="PROG-BIO", preference_rank=1)]
    )

    opt = SolverService.run_allocation(
        applicants=[app1, app2],
        programs=[prog]
    )

    assert opt.solver_status in ("OPTIMAL", "FEASIBLE")
    assigned_ids = [a.applicant_id for a in opt.assignments]
    assert "APP-NO-BIO" not in assigned_ids
    assert "APP-HAS-BIO" in assigned_ids

    # Validate with independent validator
    val = AllocationValidator.validate(opt.assignments, [app1, app2], [prog])
    assert val.is_valid is True

def test_multiple_eligibility_attributes_required():
    prog = Program(
        id="PROG-SEC",
        name="Cyber Ops",
        capacity=5,
        required_attributes=["STEM", "SECURITY_CLEARANCE"]
    )
    # Lacks security clearance
    app = Applicant(
        id="APP-1",
        full_name="Dave",
        eligibility_attributes=["STEM"],
        preferences=[Preference(program_id="PROG-SEC", preference_rank=1)]
    )
    opt = SolverService.run_allocation(applicants=[app], programs=[prog])
    assert len(opt.assignments) == 0
