"""Optimizer package for FAIRSHIFT"""
from .allocation_model import AllocationOptimizer, OptimizationOutput
from .solver_service import SolverService
from .objectives import get_preference_weight, PRESERVATION_BONUS
