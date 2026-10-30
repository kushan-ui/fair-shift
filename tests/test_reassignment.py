"""
Tests verifying reassignment stability: minimizing unnecessary changes
to valid existing assignments.
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from optimizer.solver_service import SolverService

def test_existing_valid_assignments_are_preserved():
    # Two programs with capacity 1
    prog_a = Program(id="PROG-A", name="Program A", capacity=1)
    prog_b = Program(id="PROG-B", name="Program B", capacity=1)

    app1 = Applicant(
        id="APP-1",
        full_name="User 1",
        preferences=[
            Preference(program_id="PROG-A", preference_rank=1),
            Preference(program_id="PROG-B", preference_rank=2)
        ]
    )
    app2 = Applicant(
        id="APP-2",
        full_name="User 2",
        preferences=[
            Preference(program_id="PROG-A", preference_rank=1),
            Preference(program_id="PROG-B", preference_rank=2)
        ]
    )

    # Existing assignment: APP-1 was confirmed in PROG-A, APP-2 confirmed in PROG-B
    existing = {"APP-1": "PROG-A", "APP-2": "PROG-B"}

    opt = SolverService.run_allocation(
        applicants=[app1, app2],
        programs=[prog_a, prog_b],
        existing_assignments=existing,
        policy="LEXICOGRAPHIC_STABILITY_FIRST"
    )

    asgn_map = {a.applicant_id: a.program_id for a in opt.assignments}
    assert asgn_map["APP-1"] == "PROG-A"
    assert asgn_map["APP-2"] == "PROG-B"
    assert opt.assignments_changed == 0
    assert opt.preserved_assignments_count == 2

def test_withdrawn_applicant_is_not_preserved():
    prog = Program(id="PROG-A", name="Prog A", capacity=1)
    app = Applicant(
        id="APP-W",
        full_name="Withdrawn User",
        is_withdrawn=True,
        status="WITHDRAWN",
        preferences=[Preference(program_id="PROG-A", preference_rank=1)]
    )

    existing = {"APP-W": "PROG-A"}
    opt = SolverService.run_allocation(
        applicants=[app],
        programs=[prog],
        existing_assignments=existing
    )
    assert len(opt.assignments) == 0
