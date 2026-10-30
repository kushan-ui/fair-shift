"""
FAIRSHIFT Optimization Model using Google OR-Tools CP-SAT
Formulates binary decision variables x[i, j] and enforces hard constraints and objectives.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set
from ortools.sat.python import cp_model

from models.applicant import Applicant
from models.program import Program
from models.allocation import Assignment
from optimizer.objectives import get_preference_weight, PRESERVATION_BONUS

@dataclass
class OptimizationOutput:
    solver_status: str # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID
    solve_duration_sec: float
    assignments: List[Assignment]
    objective_value: Optional[float] = None
    preference_score: float = 0.0
    assignments_changed: int = 0
    preserved_assignments_count: int = 0
    total_assigned: int = 0
    total_unassigned: int = 0
    is_optimal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

class AllocationOptimizer:
    """
    CP-SAT Optimization Engine for Fair Seat Allocation.
    Encapsulates decision variable creation, hard constraint enforcement,
    and multi-objective lexicographic policies.
    """

    def __init__(
        self,
        applicants: List[Applicant],
        programs: List[Program],
        existing_assignments: Optional[Dict[str, str]] = None, # applicant_id -> program_id
        enforced_assignments: Optional[Dict[str, str]] = None, # applicant_id -> program_id (for appeals)
        policy: str = "LEXICOGRAPHIC_PREFERENCE_FIRST",
        time_limit_seconds: int = 15,
        random_seed: int = 42
    ):
        self.applicants = applicants
        self.programs = programs
        self.existing_assignments = existing_assignments or {}
        self.enforced_assignments = enforced_assignments or {}
        self.policy = policy
        self.time_limit_seconds = time_limit_seconds
        self.random_seed = random_seed

        # Fast lookup maps
        self.applicant_map: Dict[str, Applicant] = {a.id: a for a in applicants}
        self.program_map: Dict[str, Program] = {p.id: p for p in programs}

    def solve(self) -> OptimizationOutput:
        start_time = time.time()

        # Step 0: Pre-flight validation of input models
        if not self.programs:
            return OptimizationOutput(
                solver_status="MODEL_INVALID",
                solve_duration_sec=round(time.time() - start_time, 4),
                assignments=[],
                error_message="No training programs available for allocation."
            )

        # Check enforced assignments validity (e.g. for appeals)
        for app_id, prog_id in self.enforced_assignments.items():
            app = self.applicant_map.get(app_id)
            prog = self.program_map.get(prog_id)
            if not app:
                return OptimizationOutput(
                    solver_status="MODEL_INVALID",
                    solve_duration_sec=round(time.time() - start_time, 4),
                    assignments=[],
                    error_message=f"Enforced applicant '{app_id}' does not exist."
                )
            if not prog:
                return OptimizationOutput(
                    solver_status="MODEL_INVALID",
                    solve_duration_sec=round(time.time() - start_time, 4),
                    assignments=[],
                    error_message=f"Enforced program '{prog_id}' does not exist."
                )
            if app.is_withdrawn or app.status == "WITHDRAWN":
                return OptimizationOutput(
                    solver_status="INFEASIBLE",
                    solve_duration_sec=round(time.time() - start_time, 4),
                    assignments=[],
                    error_message=f"Cannot assign withdrawn applicant '{app.id}'."
                )
            if not prog.is_active:
                return OptimizationOutput(
                    solver_status="INFEASIBLE",
                    solve_duration_sec=round(time.time() - start_time, 4),
                    assignments=[],
                    error_message=f"Cannot assign to inactive program '{prog.id}'."
                )
            # Check eligibility
            applicant_attrs = set(app.eligibility_attributes or [])
            if any(req not in applicant_attrs for req in prog.required_attributes):
                return OptimizationOutput(
                    solver_status="INFEASIBLE",
                    solve_duration_sec=round(time.time() - start_time, 4),
                    assignments=[],
                    error_message=f"Applicant '{app.id}' lacks required eligibility attributes for program '{prog.id}'."
                )

        # Build CP-SAT Model
        model = cp_model.CpModel()

        # Decision variables: x[(applicant_id, program_id)] is binary {0, 1}
        x: Dict[Tuple[str, str], cp_model.IntVar] = {}
        applicant_candidate_programs: Dict[str, List[str]] = {a.id: [] for a in self.applicants}
        program_candidate_applicants: Dict[str, List[str]] = {p.id: [] for p in self.programs}

        # Filter candidate variables:
        # Only active, non-withdrawn applicants, active programs, eligible pairs, and ranked programs
        active_applicants = [a for a in self.applicants if not a.is_withdrawn and a.status != "WITHDRAWN"]
        active_programs = [p for p in self.programs if p.is_active and p.capacity >= 0]

        for app in active_applicants:
            applicant_attrs = set(app.eligibility_attributes or [])
            for pref in app.preferences:
                prog = self.program_map.get(pref.program_id)
                if not prog or not prog.is_active:
                    continue
                # Check eligibility
                if any(req not in applicant_attrs for req in prog.required_attributes):
                    continue

                var_name = f"x_{app.id}_{prog.id}"
                var = model.NewBoolVar(var_name)
                x[(app.id, prog.id)] = var
                applicant_candidate_programs[app.id].append(prog.id)
                program_candidate_applicants[prog.id].append(app.id)

        # Enforce hard constraints:
        # 1. At most one program assignment per applicant
        for app in active_applicants:
            candidate_progs = applicant_candidate_programs[app.id]
            if candidate_progs:
                model.AddAtMostOne([x[(app.id, p_id)] for p_id in candidate_progs])

        # 2. Program capacity constraint
        for prog in active_programs:
            candidate_apps = program_candidate_applicants[prog.id]
            if candidate_apps:
                model.Add(sum(x[(a_id, prog.id)] for a_id in candidate_apps) <= prog.capacity)

        # 3. Enforced assignments (e.g. for appeals)
        for app_id, prog_id in self.enforced_assignments.items():
            if (app_id, prog_id) in x:
                model.Add(x[(app_id, prog_id)] == 1)
            else:
                # Incompatible request
                return OptimizationOutput(
                    solver_status="INFEASIBLE",
                    solve_duration_sec=round(time.time() - start_time, 4),
                    assignments=[],
                    error_message=f"Enforced assignment {app_id} -> {prog_id} is ineligible or not ranked."
                )

        # Objectives Formulation
        # Preference utility expression
        preference_expr = []
        for app in active_applicants:
            for pref in app.preferences:
                if (app.id, pref.program_id) in x:
                    weight = get_preference_weight(pref.preference_rank)
                    preference_expr.append(weight * x[(app.id, pref.program_id)])

        total_preference_expr = cp_model.LinearExpr.Sum(preference_expr) if preference_expr else 0

        # Stability expression (preserving valid confirmed assignments)
        preservation_expr = []
        for app_id, prev_prog_id in self.existing_assignments.items():
            if (app_id, prev_prog_id) in x:
                # Check if still valid (active, eligible, program active)
                app = self.applicant_map.get(app_id)
                prog = self.program_map.get(prev_prog_id)
                if app and prog and not app.is_withdrawn and prog.is_active:
                    preservation_expr.append(x[(app_id, prev_prog_id)])

        total_preservation_expr = cp_model.LinearExpr.Sum(preservation_expr) if preservation_expr else 0

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(self.time_limit_seconds)
        solver.parameters.random_seed = self.random_seed
        solver.parameters.num_workers = 4

        # Execute optimization according to chosen policy
        if self.policy == "LEXICOGRAPHIC_PREFERENCE_FIRST":
            # Multi-phase solve:
            # Phase 1: Maximize preference satisfaction
            model.Maximize(total_preference_expr)
            phase1_status = solver.Solve(model)

            status_str = self._map_status(phase1_status)
            if status_str not in ("OPTIMAL", "FEASIBLE"):
                return self._build_result(solver, status_str, start_time, x, active_applicants)

            best_pref_score = int(solver.ObjectiveValue()) if phase1_status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0

            # Phase 2: Lock optimal preference score and maximize preservation of assignments
            if preservation_expr:
                model.Add(total_preference_expr >= best_pref_score)
                model.Maximize(total_preservation_expr)
                phase2_status = solver.Solve(model)
                final_status_str = self._map_status(phase2_status)
                return self._build_result(solver, final_status_str, start_time, x, active_applicants, best_pref_score)

            return self._build_result(solver, status_str, start_time, x, active_applicants, best_pref_score)

        elif self.policy == "LEXICOGRAPHIC_STABILITY_FIRST" and preservation_expr:
            # Phase 1: Maximize preservation
            model.Maximize(total_preservation_expr)
            phase1_status = solver.Solve(model)
            status_str = self._map_status(phase1_status)
            if status_str not in ("OPTIMAL", "FEASIBLE"):
                return self._build_result(solver, status_str, start_time, x, active_applicants)

            best_preservation = int(solver.ObjectiveValue())
            # Phase 2: Lock preservation and maximize preference
            model.Add(total_preservation_expr >= best_preservation)
            model.Maximize(total_preference_expr)
            phase2_status = solver.Solve(model)
            final_status_str = self._map_status(phase2_status)
            return self._build_result(solver, final_status_str, start_time, x, active_applicants)

        else: # BALANCED or Initial allocation
            # Weighted multi-objective: preference score + preservation bonus
            combined_objective = total_preference_expr
            if preservation_expr:
                combined_objective = total_preference_expr + (PRESERVATION_BONUS * total_preservation_expr)

            model.Maximize(combined_objective)
            solve_status = solver.Solve(model)
            status_str = self._map_status(solve_status)
            return self._build_result(solver, status_str, start_time, x, active_applicants)

    def _map_status(self, cp_status: int) -> str:
        if cp_status == cp_model.OPTIMAL:
            return "OPTIMAL"
        elif cp_status == cp_model.FEASIBLE:
            return "FEASIBLE"
        elif cp_status == cp_model.INFEASIBLE:
            return "INFEASIBLE"
        elif cp_status == cp_model.MODEL_INVALID:
            return "MODEL_INVALID"
        else:
            return "UNKNOWN"

    def _build_result(
        self,
        solver: cp_model.CpSolver,
        status_str: str,
        start_time: float,
        x: Dict[Tuple[str, str], cp_model.IntVar],
        active_applicants: List[Applicant],
        fixed_pref_score: Optional[int] = None
    ) -> OptimizationOutput:
        duration = round(time.time() - start_time, 4)

        if status_str not in ("OPTIMAL", "FEASIBLE"):
            return OptimizationOutput(
                solver_status=status_str,
                solve_duration_sec=duration,
                assignments=[],
                is_optimal=False,
                metadata={"wall_time": solver.WallTime(), "branches": solver.NumBranches()}
            )

        # Extract assignments
        assigned_list: List[Assignment] = []
        assigned_applicant_ids: Set[str] = set()
        total_pref_score = 0
        preserved_count = 0
        changed_count = 0

        for (app_id, prog_id), var in x.items():
            if solver.Value(var) == 1:
                app = self.applicant_map[app_id]
                pref_obj = next((p for p in app.preferences if p.program_id == prog_id), None)
                rank = pref_obj.preference_rank if pref_obj else None

                assigned_list.append(Assignment(
                    id=f"ASGN-{uuid.uuid4().hex[:8]}",
                    version_id="", # Assigned by service
                    applicant_id=app_id,
                    program_id=prog_id,
                    preference_rank=rank,
                    is_valid=True
                ))
                assigned_applicant_ids.add(app_id)

                if rank:
                    total_pref_score += get_preference_weight(rank)

                # Check against existing assignment
                prev_prog = self.existing_assignments.get(app_id)
                if prev_prog:
                    if prev_prog == prog_id:
                        preserved_count += 1
                    else:
                        changed_count += 1

        # Check existing assignments that lost their seat or changed
        for app_id, prev_prog in self.existing_assignments.items():
            if app_id not in assigned_applicant_ids:
                changed_count += 1

        total_active_apps = len(active_applicants)
        total_assigned = len(assigned_list)
        total_unassigned = total_active_apps - total_assigned

        return OptimizationOutput(
            solver_status=status_str,
            solve_duration_sec=duration,
            assignments=assigned_list,
            objective_value=float(solver.ObjectiveValue()),
            preference_score=float(fixed_pref_score if fixed_pref_score is not None else total_pref_score),
            assignments_changed=changed_count,
            preserved_assignments_count=preserved_count,
            total_assigned=total_assigned,
            total_unassigned=total_unassigned,
            is_optimal=(status_str == "OPTIMAL"),
            metadata={
                "wall_time": solver.WallTime(),
                "branches": solver.NumBranches(),
                "conflicts": solver.NumConflicts(),
                "policy": self.policy,
                "time_limit": self.time_limit_seconds
            }
        )
