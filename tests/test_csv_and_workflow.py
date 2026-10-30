"""
Tests for CSV imports, validation gating on commit, and version comparisons.
"""

import pytest
from utils.csv_import import parse_applicants_csv, parse_programs_csv
from models.allocation import AllocationVersion, Assignment
from services.allocation_service import AllocationService
from database.repositories import AllocationRepository
from database.db import init_db

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_workflow.db")
    monkeypatch.setenv("FAIRSHIFT_DB_PATH", test_db)
    import config
    monkeypatch.setattr(config, "DB_PATH", test_db)
    init_db(force=True)

def test_csv_import_duplicate_id_detection():
    csv_text = """id,full_name,email,eligibility_attributes,preferences
APP-01,Alice,alice@example.com,STEM,PROG-A;PROG-B
APP-01,Duplicate Alice,dup@example.com,STEM,PROG-A
"""
    apps, errors = parse_applicants_csv(csv_text)
    assert len(apps) == 1
    assert any("Duplicate applicant ID" in e for e in errors)

def test_csv_import_invalid_capacity():
    csv_text = """id,name,capacity,description,required_attributes
PROG-1,Robotics,-5,Intro,-
PROG-2,AI,abc,Intro,-
"""
    progs, errors = parse_programs_csv(csv_text)
    assert len(progs) == 0
    assert len(errors) == 2

def test_unvalidated_allocation_cannot_be_committed():
    # Attempting to commit an unvalidated or failed version must raise an exception
    bad_version = AllocationVersion(
        id="VER-BAD",
        version_number=99,
        name="Bad Version",
        status="DRAFT",
        policy="BALANCED",
        solver_status="OPTIMAL",
        is_validated=False,
        validation_result="FAIL"
    )
    AllocationRepository.create_version(bad_version)

    with pytest.raises(ValueError, match="Cannot commit an allocation version that has not passed independent validation"):
        AllocationService.commit_version("VER-BAD")
