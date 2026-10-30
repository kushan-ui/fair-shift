"""
CSV Import utility for FAIRSHIFT
Parses applicant and program CSV files with robust input validation, duplicate detection,
and structured error reporting.
"""

import csv
import io
import json
from typing import List, Dict, Any, Tuple
from models.applicant import Applicant, Preference
from models.program import Program

def parse_applicants_csv(csv_content: str) -> Tuple[List[Applicant], List[str]]:
    """
    Parses applicant CSV string.
    Expected headers: id, full_name, email, eligibility_attributes, preferences
    Returns (valid_applicants, error_messages)
    """
    valid_applicants: List[Applicant] = []
    errors: List[str] = []
    seen_ids = set()

    reader = csv.DictReader(io.StringIO(csv_content))
    if not reader.fieldnames:
        return [], ["Empty or invalid CSV file."]

    # Normalize header names
    field_map = {f.strip().lower(): f for f in reader.fieldnames if f}

    id_col = field_map.get("id") or field_map.get("applicant_id")
    name_col = field_map.get("full_name") or field_map.get("name")
    email_col = field_map.get("email", "")
    attrs_col = field_map.get("eligibility_attributes") or field_map.get("attributes")
    prefs_col = field_map.get("preferences") or field_map.get("ranked_preferences")

    if not id_col or not name_col:
        return [], ["CSV must contain at least 'id' and 'full_name' columns."]

    row_idx = 1
    for row in reader:
        row_idx += 1
        raw_id = (row.get(id_col) or "").strip()
        raw_name = (row.get(name_col) or "").strip()

        if not raw_id:
            errors.append(f"Row {row_idx}: Missing applicant ID.")
            continue
        if not raw_name:
            errors.append(f"Row {row_idx}: Missing full name for applicant '{raw_id}'.")
            continue
        if raw_id in seen_ids:
            errors.append(f"Row {row_idx}: Duplicate applicant ID '{raw_id}' in CSV.")
            continue

        seen_ids.add(raw_id)
        email = (row.get(email_col) or "").strip() if email_col else ""

        # Parse eligibility attributes (semicolon or comma separated)
        attrs = []
        if attrs_col and row.get(attrs_col):
            raw_attrs = row[attrs_col].strip()
            if raw_attrs.startswith("[") and raw_attrs.endswith("]"):
                try:
                    attrs = json.loads(raw_attrs)
                except Exception:
                    attrs = [a.strip() for a in raw_attrs.strip("[]").replace('"', '').split(",") if a.strip()]
            else:
                delimiter = ";" if ";" in raw_attrs else ","
                attrs = [a.strip() for a in raw_attrs.split(delimiter) if a.strip()]

        # Parse preferences
        prefs = []
        if prefs_col and row.get(prefs_col):
            raw_prefs = row[prefs_col].strip()
            if raw_prefs.startswith("[") and raw_prefs.endswith("]"):
                try:
                    p_list = json.loads(raw_prefs)
                    prefs = [Preference(program_id=str(p), preference_rank=idx + 1) for idx, p in enumerate(p_list)]
                except Exception:
                    p_list = [p.strip() for p in raw_prefs.strip("[]").replace('"', '').split(",") if p.strip()]
                    prefs = [Preference(program_id=p, preference_rank=idx + 1) for idx, p in enumerate(p_list)]
            else:
                delimiter = ";" if ";" in raw_prefs else ","
                p_list = [p.strip() for p in raw_prefs.split(delimiter) if p.strip()]
                prefs = [Preference(program_id=p, preference_rank=idx + 1) for idx, p in enumerate(p_list)]

        valid_applicants.append(Applicant(
            id=raw_id,
            full_name=raw_name,
            email=email,
            eligibility_attributes=attrs,
            preferences=prefs
        ))

    return valid_applicants, errors


def parse_programs_csv(csv_content: str) -> Tuple[List[Program], List[str]]:
    """
    Parses program CSV string.
    Expected headers: id, name, capacity, description, required_attributes
    Returns (valid_programs, error_messages)
    """
    valid_programs: List[Program] = []
    errors: List[str] = []
    seen_ids = set()

    reader = csv.DictReader(io.StringIO(csv_content))
    if not reader.fieldnames:
        return [], ["Empty or invalid CSV file."]

    field_map = {f.strip().lower(): f for f in reader.fieldnames if f}

    id_col = field_map.get("id") or field_map.get("program_id")
    name_col = field_map.get("name") or field_map.get("program_name")
    cap_col = field_map.get("capacity") or field_map.get("seats")
    desc_col = field_map.get("description", "")
    reqs_col = field_map.get("required_attributes") or field_map.get("requirements")

    if not id_col or not name_col or not cap_col:
        return [], ["CSV must contain 'id', 'name', and 'capacity' columns."]

    row_idx = 1
    for row in reader:
        row_idx += 1
        raw_id = (row.get(id_col) or "").strip()
        raw_name = (row.get(name_col) or "").strip()
        raw_cap = (row.get(cap_col) or "").strip()

        if not raw_id:
            errors.append(f"Row {row_idx}: Missing program ID.")
            continue
        if not raw_name:
            errors.append(f"Row {row_idx}: Missing program name.")
            continue
        if raw_id in seen_ids:
            errors.append(f"Row {row_idx}: Duplicate program ID '{raw_id}'.")
            continue

        try:
            cap = int(raw_cap)
            if cap < 0:
                errors.append(f"Row {row_idx}: Capacity cannot be negative for '{raw_id}'.")
                continue
        except ValueError:
            errors.append(f"Row {row_idx}: Invalid integer capacity '{raw_cap}' for '{raw_id}'.")
            continue

        seen_ids.add(raw_id)
        desc = (row.get(desc_col) or "").strip() if desc_col else ""

        reqs = []
        if reqs_col and row.get(reqs_col):
            raw_reqs = row[reqs_col].strip()
            delimiter = ";" if ";" in raw_reqs else ","
            reqs = [r.strip() for r in raw_reqs.split(delimiter) if r.strip()]

        valid_programs.append(Program(
            id=raw_id,
            name=raw_name,
            description=desc,
            capacity=cap,
            required_attributes=reqs
        ))

    return valid_programs, errors
