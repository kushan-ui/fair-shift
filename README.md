# FAIRSHIFT — Fair Allocation, Reassignment, and Impact Analysis System

> **Transparent Allocation. Minimal Disruption. Verifiable Decisions.**

FAIRSHIFT is an auditable decision-support platform that allocates limited training seats among applicants using mathematical constraint optimization (**Google OR-Tools CP-SAT**). It respects applicant eligibility, program capacities, ranked preferences, and existing valid assignments wherever possible.

The system minimizes unnecessary reassignment disruptions, evaluates appeals through counterfactual optimization, independently validates every allocation outside the solver, and transparently explains the consequences of allocation decisions.

---

## 🏗️ System Architecture

```
FAIRSHIFT/
├── app.py                      # Streamlit Enterprise UI application entrypoint
├── server.ts                   # Gateway proxy (runs on port 3000 with WebSocket support)
├── config.py                   # Global system constants, weights, and timeouts
├── requirements.txt            # Python dependencies
├── package.json                # Gateway and environment dependencies
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite connection manager, WAL mode, transaction isolation
│   ├── schema.sql              # Normalized database schema with indexes and foreign keys
│   └── repositories.py         # Type-safe parameterized repository layer
│
├── models/
│   ├── __init__.py
│   ├── applicant.py            # Applicant and Preference domain models
│   ├── program.py              # Training Program domain model
│   ├── allocation.py           # AllocationVersion and Assignment models
│   └── appeal.py               # Appeal and AppealAnalysisResult models
│
├── optimizer/
│   ├── __init__.py
│   ├── allocation_model.py     # CP-SAT binary formulation x[i, j], hard constraints, lexicographic phases
│   ├── solver_service.py       # Safe solver invocation and timeout trapping
│   └── objectives.py           # Preference rank utilities and preservation weights
│
├── validation/
│   ├── __init__.py
│   └── allocation_validator.py # Independent rule validator (strictly independent from optimizer)
│
├── services/
│   ├── __init__.py
│   ├── applicant_service.py    # Candidate lifecycle, preferences, and withdrawals
│   ├── program_service.py      # Cohort capacities, prerequisites, and capacity history
│   ├── allocation_service.py   # Solver orchestration, versioning, and commit gating
│   ├── reassignment_service.py # Non-destructive simulation sandbox
│   ├── appeal_service.py       # Counterfactual optimization and administrative decisions
│   ├── reporting_service.py    # Metric aggregation and analytics
│   └── audit_service.py        # Append-only operational audit logging
│
├── ui/
│   ├── __init__.py
│   ├── dashboard.py            # Page 1: Executive Dashboard with Plotly charts
│   ├── applicants.py           # Page 2: Applicant Directory, Roster, Registration, CSV
│   ├── programs.py             # Page 3: Program Management & Capacity History
│   ├── allocation.py           # Page 4: OR-Tools Optimization Engine & Version Compare
│   ├── simulation.py           # Page 5: What-If Sandbox & Disruption Comparison
│   ├── appeals.py              # Page 6: Counterfactual Appeal Workflow
│   ├── validation.py           # Page 7: Independent Constraint Auditor
│   ├── audit.py                # Page 8: Cryptographic Audit Trail & Event Inspector
│   └── reports.py              # Page 9: Analytical Exports & Solver Telemetry
│
├── utils/
│   ├── __init__.py
│   ├── demo_data.py            # 200 Synthetic Applicants & 10 Cohorts Generator
│   ├── csv_import.py           # Validating CSV importer
│   └── csv_export.py           # Comprehensive CSV exporter
│
└── tests/
    ├── test_database.py        # SQLite persistence and foreign keys
    ├── test_eligibility.py     # Hard eligibility enforcement
    ├── test_capacity.py        # Quota caps and zero-capacity programs
    ├── test_preferences.py     # Preference rank optimization
    ├── test_reassignment.py    # Stability preservation and minimal disruption
    ├── test_appeals.py         # Feasible vs infeasible appeals
    ├── test_validation.py      # Independent validator rule violation tests
    ├── test_solver_status.py   # Proves UNKNOWN != INFEASIBLE, FEASIBLE != OPTIMAL
    └── test_csv_and_workflow.py# CSV parsing and unvalidated commit prevention
```

---

## 🪟 Windows 10/11 Local Installation Instructions

### Step 1: Install Python
1. Download **Python 3.10, 3.11, or 3.12** from [python.org](https://www.python.org/downloads/).
2. During installation, **check the box**: `"Add python.exe to PATH"`.
3. Open Windows Terminal / Command Prompt (`cmd.exe`) and verify:
   ```cmd
   python --version
   ```

### Step 2: Open Project Folder and Create Virtual Environment
```cmd
cd path\to\fairshift
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Run the Application
Launch FAIRSHIFT using Streamlit:
```cmd
streamlit run app.py
```
Your default browser will open automatically to `http://localhost:8501`.

---

## 🐧 Linux / macOS Startup Instructions

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch application
streamlit run app.py --server.port 8501
```

---

## 🧪 Running the Automated Test Suite

FAIRSHIFT includes 25 unit and integration tests covering mathematical constraints, solver status mappings, independent validation, and database integrity:

```bash
# Run all tests with verbose output
python3 -m pytest -v

# Run with test coverage
python3 -m pytest -v tests/
```

### Verified Test Cases:
- `test_database.py`: Verifies SQLite table generation, foreign key constraints, and transactional consistency.
- `test_eligibility.py`: Confirms ineligible candidates are mathematically blocked from being assigned.
- `test_capacity.py`: Proves program quotas are strictly respected, including zero-seat programs.
- `test_preferences.py`: Verifies preference rank weight scoring and lexicographic Pareto optimization.
- `test_reassignment.py`: Verifies preservation of valid confirmed assignments during reallocation.
- `test_appeals.py`: Validates counterfactual re-optimization for feasible and infeasible appeals.
- `test_validation.py`: Tests independent detection of duplicate seats, withdrawn applicants, and capacity breaches.
- `test_solver_status.py`: Proves that `UNKNOWN` is never reported as `INFEASIBLE`, and `FEASIBLE` is never reported as `OPTIMAL` without proof.
- `test_csv_and_workflow.py`: Validates CSV error handling and ensures unvalidated versions cannot be committed.

---

## 📊 Lexicographic Optimization Model

FAIRSHIFT formulates a Mixed-Integer Linear Programming (MILP) problem solved with **Google OR-Tools CP-SAT**:

### Decision Variables:
$$x_{i,j} \in \{0, 1\}$$
where $x_{i,j} = 1$ if applicant $i$ is assigned to training program $j$, and $0$ otherwise.

### Hard Constraints:
1. **Uniqueness**: Each active applicant can receive at most one seat:
   $$\sum_{j} x_{i,j} \le 1, \quad \forall i \in \text{ActiveApplicants}$$
2. **Eligibility**: Candidate must hold all mandatory prerequisite tags:
   $$x_{i,j} = 0, \quad \text{if } \text{Prerequisites}(j) \not\subseteq \text{Attributes}(i)$$
3. **Capacity Quota**: Program seat limit cannot be exceeded:
   $$\sum_{i} x_{i,j} \le \text{Capacity}_j, \quad \forall j \in \text{ActivePrograms}$$
4. **Withdrawal Enforcement**:
   $$x_{i,j} = 0, \quad \forall j, \quad \text{if applicant is withdrawn}$$
5. **Preference Bounding**: Candidates are only assigned to programs they explicitly ranked.

### Multi-Phase Lexicographic Priorities:
- **Policy 1 (`LEXICOGRAPHIC_PREFERENCE_FIRST`)**:
  - **Phase 1**: Maximize total preference score $P^* = \max \sum_{i,j} w_{i,j} x_{i,j}$
  - **Phase 2**: Add constraint $\sum_{i,j} w_{i,j} x_{i,j} \ge P^*$, then maximize preserved confirmed seats $\sum_{i} x_{i, \text{prev}(i)}$.
- **Policy 2 (`LEXICOGRAPHIC_STABILITY_FIRST`)**:
  - **Phase 1**: Maximize seat preservation $S^* = \max \sum_{i} x_{i, \text{prev}(i)}$.
  - **Phase 2**: Add constraint $\sum_{i} x_{i, \text{prev}(i)} \ge S^*$, then maximize candidate preference satisfaction.

---

## 🔎 Solver Status Interpretation Guide

| Solver Status | Meaning | System Response |
| :--- | :--- | :--- |
| **`OPTIMAL`** | The solver found a solution and mathematically proved no better solution exists under the declared policy. | Version marked as optimal; eligible for commit upon passing validation. |
| **`FEASIBLE`** | The solver found a valid solution satisfying all hard constraints, but search stopped before proving global optimality (e.g., time limit). | Reported clearly as `FEASIBLE` (never falsely labeled `OPTIMAL`). |
| **`INFEASIBLE`** | The solver mathematically proved that no combination of assignments can satisfy all mandatory constraints. | Reported as `INFEASIBLE`. Specific conflicting constraints are diagnosed. |
| **`UNKNOWN`** | The solver reached the time limit without finding any feasible assignment, or encountered a non-fatal timeout. | Reported strictly as `UNKNOWN`. Never interpreted as `INFEASIBLE`. |
| **`MODEL_INVALID`** | Input validation detected missing programs or malformed parameters before calling the solver. | Pre-flight error returned; prevents solver execution. |

---

## 🔄 Resetting the Demo Database

To reset the database back to clean synthetic data:
1. Open the FAIRSHIFT application.
2. In the left sidebar, expand **🛠️ Demo Database Management**.
3. Click **Reset to Clean Demo Data**.
4. The system will wipe `data/fairshift.db`, re-apply `database/schema.sql`, re-populate 200 synthetic applicants and 10 cohorts, and immediately solve a clean baseline allocation.
