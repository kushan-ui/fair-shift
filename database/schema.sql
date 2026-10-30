-- FAIRSHIFT Database Schema
-- Optimized for SQLite with Foreign Keys and Indexes

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS applicants (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT,
    eligibility_attributes TEXT DEFAULT '[]', -- JSON array of attribute tags, e.g. ["STEM", "CITIZEN", "VETERAN"]
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, WITHDRAWN
    is_withdrawn INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS programs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    required_attributes TEXT DEFAULT '[]', -- JSON array of required attribute tags
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applicant_preferences (
    applicant_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    preference_rank INTEGER NOT NULL CHECK (preference_rank >= 1),
    PRIMARY KEY (applicant_id, preference_rank),
    FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE,
    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS applicant_eligibility (
    applicant_id TEXT NOT NULL,
    attribute_name TEXT NOT NULL,
    attribute_value TEXT DEFAULT 'TRUE',
    PRIMARY KEY (applicant_id, attribute_name),
    FOREIGN KEY (applicant_id) REFERENCES applicants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS allocation_versions (
    id TEXT PRIMARY KEY,
    version_number INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL, -- DRAFT, COMMITTED, CANCELLED
    policy TEXT NOT NULL, -- LEXICOGRAPHIC_PREFERENCE_FIRST, LEXICOGRAPHIC_STABILITY_FIRST, BALANCED
    solver_status TEXT NOT NULL, -- OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID
    solve_duration_sec REAL DEFAULT 0.0,
    preference_satisfaction_score REAL DEFAULT 0.0,
    total_assigned INTEGER DEFAULT 0,
    total_unassigned INTEGER DEFAULT 0,
    assignments_changed INTEGER DEFAULT 0,
    is_validated INTEGER DEFAULT 0,
    validation_result TEXT, -- PASS / FAIL / JSON details
    created_at TEXT NOT NULL,
    parent_version_id TEXT,
    solver_metadata TEXT DEFAULT '{}',
    FOREIGN KEY (parent_version_id) REFERENCES allocation_versions(id)
);

CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    applicant_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    preference_rank INTEGER,
    is_valid INTEGER DEFAULT 1,
    assigned_at TEXT NOT NULL,
    UNIQUE (version_id, applicant_id),
    FOREIGN KEY (version_id) REFERENCES allocation_versions(id) ON DELETE CASCADE,
    FOREIGN KEY (applicant_id) REFERENCES applicants(id),
    FOREIGN KEY (program_id) REFERENCES programs(id)
);

CREATE TABLE IF NOT EXISTS capacity_change_history (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    old_capacity INTEGER NOT NULL,
    new_capacity INTEGER NOT NULL,
    reason TEXT,
    changed_at TEXT NOT NULL,
    FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appeals (
    id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    requested_program_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    baseline_version_id TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, ANALYZED, APPROVED, REJECTED
    decision TEXT, -- APPROVED, REJECTED
    decision_explanation TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    FOREIGN KEY (applicant_id) REFERENCES applicants(id),
    FOREIGN KEY (requested_program_id) REFERENCES programs(id),
    FOREIGN KEY (baseline_version_id) REFERENCES allocation_versions(id)
);

CREATE TABLE IF NOT EXISTS appeal_analysis_results (
    id TEXT PRIMARY KEY,
    appeal_id TEXT NOT NULL,
    solver_status TEXT NOT NULL,
    is_accommodatable INTEGER NOT NULL,
    solve_duration_sec REAL DEFAULT 0.0,
    affected_applicants_count INTEGER DEFAULT 0,
    affected_applicant_ids TEXT DEFAULT '[]', -- JSON array of applicant IDs
    preference_change_score REAL DEFAULT 0.0,
    impact_summary TEXT,
    alternative_version_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (appeal_id) REFERENCES appeals(id) ON DELETE CASCADE,
    FOREIGN KEY (alternative_version_id) REFERENCES allocation_versions(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    applicant_id TEXT,
    program_id TEXT,
    allocation_version_id TEXT,
    details TEXT DEFAULT '{}', -- JSON details
    outcome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_runs (
    id TEXT PRIMARY KEY,
    baseline_version_id TEXT NOT NULL,
    name TEXT NOT NULL,
    changes_applied TEXT DEFAULT '{}', -- JSON changes (capacities, withdrawals)
    solver_status TEXT NOT NULL,
    is_valid INTEGER DEFAULT 0,
    is_committed INTEGER DEFAULT 0,
    committed_version_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (baseline_version_id) REFERENCES allocation_versions(id)
);

-- Indexes for performance and lookup
CREATE INDEX IF NOT EXISTS idx_assignments_version ON assignments(version_id);
CREATE INDEX IF NOT EXISTS idx_assignments_applicant ON assignments(applicant_id);
CREATE INDEX IF NOT EXISTS idx_assignments_program ON assignments(program_id);
CREATE INDEX IF NOT EXISTS idx_preferences_applicant ON applicant_preferences(applicant_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_appeals_status ON appeals(status);
