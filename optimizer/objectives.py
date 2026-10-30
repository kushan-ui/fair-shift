"""
FAIRSHIFT Optimization Objectives and Utility Definitions
"""

from typing import Dict

# Ranked preference utilities
# Higher rank = higher satisfaction score
DEFAULT_RANK_WEIGHTS: Dict[int, int] = {
    1: 100,
    2: 75,
    3: 50,
    4: 30,
    5: 15,
    6: 10,
    7: 5,
    8: 3,
    9: 2,
    10: 1
}

def get_preference_weight(rank: int) -> int:
    """Returns integer weight for preference rank (for CP-SAT integer optimization)."""
    if rank in DEFAULT_RANK_WEIGHTS:
        return DEFAULT_RANK_WEIGHTS[rank]
    if rank > 10:
        return 1
    return 0

# Penalty for changing an existing valid assignment
PRESERVATION_BONUS = 500 # High priority on preserving valid baseline seats when requested
