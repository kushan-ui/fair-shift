"""
FAIRSHIFT - Configuration Module
Transparent Allocation. Minimal Disruption. Verifiable Decisions.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = os.environ.get("FAIRSHIFT_DB_PATH", str(DATA_DIR / "fairshift.db"))

# Solver configuration
DEFAULT_SOLVER_TIME_LIMIT_SECONDS = 15
MAX_SOLVER_TIME_LIMIT_SECONDS = 60
DEFAULT_RANDOM_SEED = 42

# Optimization weights / policy
# Priority 1: Maximize preference score
# Priority 2: Minimize disruption to confirmed previous assignments
PREFERENCE_SCORES = {
    1: 100,
    2: 70,
    3: 45,
    4: 25,
    5: 10
}
DEFAULT_UNASSIGNED_PENALTY = 200
DEFAULT_REASSIGNMENT_PENALTY = 50

# Application Metadata
APP_NAME = "FAIRSHIFT"
APP_SUBTITLE = "Transparent Allocation. Minimal Disruption. Verifiable Decisions."
APP_VERSION = "1.0.0"
