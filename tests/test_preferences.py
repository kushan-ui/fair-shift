"""
Tests verifying preference rank utilities and preference-first lexicographic priority.
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from optimizer.solver_service import SolverService

def test_higher_preference_rank_is_preferred():
    # Program A has 1 seat, Program B has 1 seat
    prog_a = Program(id="PROG-A", name="Program A", capacity=1)
    prog_b = Program(id="PROG-B", name="Program B", capacity=1)

    # Applicant 1 prefers A (#1) then B (#2)
    app1 = Applicant(
        id="APP-1",
        full_name="User 1",
        preferences=[
            Preference(program_id="PROG-A", preference_rank=1),
            Preference(program_id="PROG-B", preference_rank=2)
        ]
    )
    # Applicant 2 prefers B (#1) then A (#2)
    app2 = Applicant(
        id="APP-2",
        full_name="User 2",
        preferences=[
            Preference(program_id="PROG-B", preference_rank=1),
            Preference(program_id="PROG-A", preference_rank=2)
        ]
    )

    opt = SolverService.run_allocation(
        applicants=[app1, app2],
        programs=[prog_a, prog_b],
        policy="LEXICOGRAPHIC_PREFERENCE_FIRST"
    )

    asgn_map = {a.applicant_id: a.program_id for a in opt.assignments}
    # Optimal matching gives both their 1st choices!
    assert asgn_map["APP-1"] == "PROG-A"
    assert asgn_map["APP-2"] == "PROG-B"
    assert opt.total_assigned == 2
    assert opt.is_optimal is True
