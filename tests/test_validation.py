"""
Tests proving that independent validation correctly detects rule violations,
and that an invalid allocation CANNOT be committed as valid.
"""

import pytest
from models.applicant import Applicant, Preference
from models.program import Program
from models.allocation import Assignment, AllocationVersion
from validation.allocation_validator import AllocationValidator
from services.allocation_service import AllocationService

def test_validator_detects_multiple_assignments():
    app = Applicant(id="APP-1", full_name="John", preferences=[Preference("PROG-A", 1), Preference("PROG-B", 2)])
    prog_a = Program(id="PROG-A", name="A", capacity=2)
    prog_b = Program(id="PROG-B", name="B", capacity=2)

    asgns = [
        Assignment("1", "v1", "APP-1", "PROG-A", preference_rank=1),
        Assignment("2", "v1", "APP-1", "PROG-B", preference_rank=2)
    ]
    val = AllocationValidator.validate(asgns, [app], [prog_a, prog_b])
    assert val.is_valid is False
    assert any(v.rule_code == "MULTIPLE_ASSIGNMENTS" for v in val.violations)

def test_validator_detects_capacity_exceeded():
    app1 = Applicant(id="APP-1", full_name="A1", preferences=[Preference("PROG-A", 1)])
    app2 = Applicant(id="APP-2", full_name="A2", preferences=[Preference("PROG-A", 1)])
    prog_a = Program(id="PROG-A", name="A", capacity=1) # only 1 seat

    asgns = [
        Assignment("1", "v1", "APP-1", "PROG-A", preference_rank=1),
        Assignment("2", "v1", "APP-2", "PROG-A", preference_rank=1)
    ]
    val = AllocationValidator.validate(asgns, [app1, app2], [prog_a])
    assert val.is_valid is False
    assert any(v.rule_code == "CAPACITY_EXCEEDED" for v in val.violations)

def test_validator_detects_withdrawn_assigned():
    app = Applicant(id="APP-W", full_name="Withdrawn", is_withdrawn=True, status="WITHDRAWN", preferences=[Preference("PROG-A", 1)])
    prog = Program(id="PROG-A", name="A", capacity=2)
    asgns = [Assignment("1", "v1", "APP-W", "PROG-A", preference_rank=1)]

    val = AllocationValidator.validate(asgns, [app], [prog])
    assert val.is_valid is False
    assert any(v.rule_code == "WITHDRAWN_APPLICANT_ASSIGNED" for v in val.violations)

def test_validator_detects_ineligible_assigned():
    app = Applicant(id="APP-NO-PREREQ", full_name="No Prereq", eligibility_attributes=[], preferences=[Preference("PROG-STEM", 1)])
    prog = Program(id="PROG-STEM", name="STEM Cohort", capacity=5, required_attributes=["STEM"])
    asgns = [Assignment("1", "v1", "APP-NO-PREREQ", "PROG-STEM", preference_rank=1)]

    val = AllocationValidator.validate(asgns, [app], [prog])
    assert val.is_valid is False
    assert any(v.rule_code == "INELIGIBLE_APPLICANT_ASSIGNED" for v in val.violations)
