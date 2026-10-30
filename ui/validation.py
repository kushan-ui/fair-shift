"""
PAGE 7: INDEPENDENT VALIDATION
Independent constraint auditor that validates allocations outside the CP-SAT solver.
Ensures zero-tolerance for over-capacity, ineligibility, duplicates, and invalid states.
"""

import streamlit as st
import pandas as pd
from services.allocation_service import AllocationService
from services.applicant_service import ApplicantService
from services.program_service import ProgramService
from validation.allocation_validator import AllocationValidator

def render_validation():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Independent Allocation Validator
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Audits raw assignment records against immutable ground truth database tables.
                Operates completely independently from the optimization solver.
            </p>
        </div>
    """, unsafe_allow_html=True)

    versions = AllocationService.get_all_versions()
    if not versions:
        st.info("No allocation versions available to audit.")
        return

    applicants = ApplicantService.get_all_applicants(include_withdrawn=True)
    programs = ProgramService.get_all_programs(include_inactive=True)

    v_options = {f"v{v.version_number} — {v.name} (Status: {v.status})": v.id for v in versions}
    sel_ver_label = st.selectbox("Select Allocation Version to Audit", list(v_options.keys()))
    sel_ver_id = v_options[sel_ver_label]

    version = AllocationService.get_version(sel_ver_id)

    st.markdown("### Execution & Audit Checks")
    st.markdown("""
    The independent validator verifies the following mandatory invariant rules:
    - **RULE 1**: At most one assignment per active applicant (No duplicate seats).
    - **RULE 2**: No withdrawn or inactive applicant receives an active assignment.
    - **RULE 3**: Applicant must strictly satisfy all required eligibility prerequisites.
    - **RULE 4**: Enrolled seats must not exceed the program's official capacity quota.
    - **RULE 5**: Inactive or deprecated programs must not receive assignments.
    - **RULE 6**: Referential integrity (both applicant and program exist in database).
    - **RULE 7**: Assigned program must be on the applicant's declared preference list.
    """)

    if st.button("🛡️ Execute Independent Validation Audit", type="primary"):
        val_res = AllocationValidator.validate(version.assignments, applicants, programs)
        st.session_state[f"audit_val_{version.id}"] = val_res

    val_res = st.session_state.get(f"audit_val_{version.id}")
    if val_res:
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)

        if val_res.is_valid:
            st.success(f"✅ AUDIT PASSED: Version v{version.version_number} strictly satisfies all mandatory hard constraints across {val_res.total_assignments_checked} assignments.")
        else:
            st.error(f"❌ AUDIT FAILED: Version v{version.version_number} contains {len(val_res.violations)} violation(s).")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Audit Status", val_res.status)
        with c2:
            st.metric("Assignments Inspected", val_res.total_assignments_checked)
        with c3:
            st.metric("Total Violations", len(val_res.violations))

        if val_res.violations:
            st.markdown("#### Violation Breakdown")
            v_rows = []
            for v in val_res.violations:
                v_rows.append({
                    "Rule Code": v.rule_code,
                    "Severity": v.severity,
                    "Applicant ID": v.applicant_id or "—",
                    "Program ID": v.program_id or "—",
                    "Description": v.description
                })
            st.dataframe(pd.DataFrame(v_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Zero rule violations detected.")

        # Capacity utilization breakdown
        st.markdown("#### Program Quota Compliance Check")
        prog_map = {p.id: p for p in programs}
        quota_rows = []
        for pid, enrolled in val_res.program_enrollment.items():
            p = prog_map.get(pid)
            cap = p.capacity if p else 0
            is_over = enrolled > cap
            quota_rows.append({
                "Program ID": pid,
                "Program Name": p.name if p else "—",
                "Seat Capacity": cap,
                "Enrolled Count": enrolled,
                "Status": "EXCEEDED ⚠️" if is_over else "Compliant ✅"
            })
        st.dataframe(pd.DataFrame(quota_rows), use_container_width=True, hide_index=True)
