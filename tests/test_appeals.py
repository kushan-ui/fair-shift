"""
Tests for counterfactual appeal evaluation: feasible appeals vs proven infeasible appeals.
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from optimizer.solver_service import SolverService

def test_appeal_accommodated_successfully():
    # Program A has 1 seat. APP-1 was assigned.
    # APP-2 appeals to get into PROG-A.
    prog_a = Program(id="PROG-A", name="Prog A", capacity=1)
    prog_b = Program(id="PROG-B", name="Prog B", capacity=1)

    app1 = Applicant(
        id="APP-1",
        full_name="App 1",
        preferences=[
            Preference(program_id="PROG-A", preference_rank=1),
            Preference(program_id="PROG-B", preference_rank=2)
        ]
    )
    app2 = Applicant(
        id="APP-2",
        full_name="App 2",
        preferences=[
            Preference(program_id="PROG-A", preference_rank=1)
        ]
    )

    baseline = {"APP-1": "PROG-A"}

    # Counterfactual: force APP-2 -> PROG-A
    opt = SolverService.run_allocation(
        applicants=[app1, app2],
        programs=[prog_a, prog_b],
        existing_assignments=baseline,
        enforced_assignments={"APP-2": "PROG-A"}
    )

    assert opt.solver_status in ("OPTIMAL", "FEASIBLE")
    asgn_map = {a.applicant_id: a.program_id for a in opt.assignments}
    assert asgn_map["APP-2"] == "PROG-A"
    # APP-1 is shifted to PROG-B
    assert asgn_map["APP-1"] == "PROG-B"

def test_appeal_proven_infeasible_due_to_capacity():
    # Capacity is 1, but APP-2 has no eligibility or PROG-A capacity is 0
    prog_a = Program(id="PROG-A", name="Prog A", capacity=0)
    app1 = Applicant(
        id="APP-1",
        full_name="App 1",
        preferences=[Preference(program_id="PROG-A", preference_rank=1)]
    )
    opt = SolverService.run_allocation(
        applicants=[app1],
        programs=[prog_a],
        enforced_assignments={"APP-1": "PROG-A"}
    )
    assert opt.solver_status == "INFEASIBLE"
