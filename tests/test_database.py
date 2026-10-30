"""
Tests for database connection, transactions, and repository CRUD persistence.
"""

import os
import pytest
from database.db import init_db, reset_db
from database.repositories import ApplicantRepository, ProgramRepository, AllocationRepository, AuditRepository
from models.applicant import Applicant, Preference
from models.program import Program
from models.allocation import AllocationVersion, Assignment

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_fairshift.db")
    monkeypatch.setenv("FAIRSHIFT_DB_PATH", test_db)
    import config
    monkeypatch.setattr(config, "DB_PATH", test_db)
    init_db(force=True)
    yield
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass

def test_applicant_crud_and_persistence():
    ProgramRepository.create(Program(id="PROG-A", name="Program A", capacity=10))
    ProgramRepository.create(Program(id="PROG-B", name="Program B", capacity=10))

    app = Applicant(
        id="TEST-001",
        full_name="Alice Smith",
        email="alice@example.com",
        eligibility_attributes=["STEM", "CITIZEN"],
        preferences=[
            Preference(program_id="PROG-A", preference_rank=1),
            Preference(program_id="PROG-B", preference_rank=2)
        ]
    )
    ApplicantRepository.create(app)

    fetched = ApplicantRepository.get_by_id("TEST-001")
    assert fetched is not None
    assert fetched.full_name == "Alice Smith"
    assert "STEM" in fetched.eligibility_attributes
    assert len(fetched.preferences) == 2
    assert fetched.preferences[0].program_id == "PROG-A"

    # Test withdrawal update
    ApplicantRepository.set_withdrawn("TEST-001", True)
    withdrawn_app = ApplicantRepository.get_by_id("TEST-001")
    assert withdrawn_app.is_withdrawn is True
    assert withdrawn_app.status == "WITHDRAWN"

def test_program_capacity_history_tracking():
    prog = Program(
        id="TEST-PROG",
        name="Test Robotics",
        capacity=20,
        required_attributes=["STEM"]
    )
    ProgramRepository.create(prog)

    # Change capacity
    ProgramRepository.update_capacity("TEST-PROG", 15, "Budget adjustment")
    history = ProgramRepository.get_capacity_history("TEST-PROG")

    assert len(history) == 1
    assert history[0]["old_capacity"] == 20
    assert history[0]["new_capacity"] == 15
    assert history[0]["reason"] == "Budget adjustment"

def test_audit_log_append_only():
    log_id = AuditRepository.log(
        event_type="TEST_EVENT",
        outcome="SUCCESS",
        details={"key": "value"}
    )
    logs = AuditRepository.get_logs(limit=10, event_type="TEST_EVENT")
    assert len(logs) >= 1
    assert logs[0]["id"] == log_id
    assert logs[0]["details"]["key"] == "value"
