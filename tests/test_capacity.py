"""
Tests verifying that program seat capacities are strictly respected,
including zero-capacity cohorts and severe over-subscription.
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from optimizer.solver_service import SolverService
from validation.allocation_validator import AllocationValidator

def test_seat_capacity_cap_is_respected():
    # Capacity is 2
    prog = Program(id="PROG-CAP2", name="Small Cohort", capacity=2)

    # 5 applicants all want PROG-CAP2 as #1
    applicants = []
    for i in range(5):
        applicants.append(Applicant(
            id=f"APP-{i}",
            full_name=f"Applicant {i}",
            preferences=[Preference(program_id="PROG-CAP2", preference_rank=1)]
        ))

    opt = SolverService.run_allocation(applicants=applicants, programs=[prog])

    assert opt.solver_status in ("OPTIMAL", "FEASIBLE")
    assert len(opt.assignments) == 2 # strictly at most 2 seats
    assert opt.total_assigned == 2
    assert opt.total_unassigned == 3

    val = AllocationValidator.validate(opt.assignments, applicants, [prog])
    assert val.is_valid is True

def test_zero_seat_program():
    prog = Program(id="PROG-ZERO", name="Zero Cap", capacity=0)
    app = Applicant(
        id="APP-Z",
        full_name="Applicant Z",
        preferences=[Preference(program_id="PROG-ZERO", preference_rank=1)]
    )

    opt = SolverService.run_allocation(applicants=[app], programs=[prog])
    assert len(opt.assignments) == 0
    assert opt.total_unassigned == 1
