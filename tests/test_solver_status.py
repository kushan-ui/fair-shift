"""
Tests proving strict adherence to solver statuses:
- UNKNOWN must NEVER be reported as INFEASIBLE
- FEASIBLE must NEVER be reported as OPTIMAL unless optimality is proven
- Invalid models must be rejected
- Empty applicant dataset handled safely
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from optimizer.solver_service import SolverService
from optimizer.allocation_model import AllocationOptimizer

def test_unknown_status_mapping():
    optimizer = AllocationOptimizer([], [])
    # 0 = cp_model.UNKNOWN
    mapped = optimizer._map_status(0)
    assert mapped == "UNKNOWN"
    assert mapped != "INFEASIBLE"

def test_feasible_not_reported_as_optimal():
    optimizer = AllocationOptimizer([], [])
    # 2 = cp_model.FEASIBLE
    mapped = optimizer._map_status(2)
    assert mapped == "FEASIBLE"
    assert mapped != "OPTIMAL"

def test_optimal_status_mapping():
    optimizer = AllocationOptimizer([], [])
    # 4 = cp_model.OPTIMAL
    mapped = optimizer._map_status(4)
    assert mapped == "OPTIMAL"

def test_infeasible_status_mapping():
    optimizer = AllocationOptimizer([], [])
    # 3 = cp_model.INFEASIBLE
    mapped = optimizer._map_status(3)
    assert mapped == "INFEASIBLE"
    assert mapped != "UNKNOWN"

def test_empty_applicant_dataset():
    prog = Program(id="PROG-1", name="P1", capacity=10)
    opt = SolverService.run_allocation(applicants=[], programs=[prog])
    # Empty set is trivially solvable with 0 assignments
    assert opt.solver_status in ("OPTIMAL", "FEASIBLE")
    assert len(opt.assignments) == 0
    assert opt.total_assigned == 0
    assert opt.total_unassigned == 0

def test_empty_program_dataset_returns_model_invalid():
    app = Applicant(id="APP-1", full_name="User", preferences=[Preference("P1", 1)])
    opt = SolverService.run_allocation(applicants=[app], programs=[])
    assert opt.solver_status == "MODEL_INVALID"
    assert opt.assignments == []
