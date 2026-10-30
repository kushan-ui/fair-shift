"""
FAIRSHIFT Solver Service
High-level service interface to trigger CP-SAT optimization with timeout and exception safety.
"""

import logging
from typing import List, Dict, Optional
from models.applicant import Applicant
from models.program import Program
from optimizer.allocation_model import AllocationOptimizer, OptimizationOutput

logger = logging.getLogger(__name__)

class SolverService:
    @staticmethod
    def run_allocation(
        applicants: List[Applicant],
        programs: List[Program],
        existing_assignments: Optional[Dict[str, str]] = None,
        enforced_assignments: Optional[Dict[str, str]] = None,
        policy: str = "LEXICOGRAPHIC_PREFERENCE_FIRST",
        time_limit_seconds: int = 15,
        random_seed: int = 42
    ) -> OptimizationOutput:
        """Executes the CP-SAT allocation model safely with structured error trapping."""
        try:
            optimizer = AllocationOptimizer(
                applicants=applicants,
                programs=programs,
                existing_assignments=existing_assignments,
                enforced_assignments=enforced_assignments,
                policy=policy,
                time_limit_seconds=time_limit_seconds,
                random_seed=random_seed
            )
            return optimizer.solve()
        except Exception as e:
            logger.exception("Solver execution error")
            return OptimizationOutput(
                solver_status="UNKNOWN",
                solve_duration_sec=0.0,
                assignments=[],
                error_message=str(e),
                metadata={"exception": str(e)}
            )
