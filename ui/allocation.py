"""
PAGE 4: ALLOCATION ENGINE
Google OR-Tools CP-SAT mathematical optimization interface.
Supports initial allocation, reassignment with stability anchoring, independent validation,
and historical version comparisons.
"""

import streamlit as st
import pandas as pd
from services.allocation_service import AllocationService
from services.applicant_service import ApplicantService
from services.program_service import ProgramService
from validation.allocation_validator import AllocationValidator
from utils.csv_export import export_allocation_to_csv

def render_allocation():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Optimization & Allocation Engine
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Mathematical constraint optimization powered by Google OR-Tools CP-SAT.
                Enforces hard eligibility and capacity constraints while optimizing preference satisfaction and stability.
            </p>
        </div>
    """, unsafe_allow_html=True)

    applicants = ApplicantService.get_all_applicants(include_withdrawn=True)
    programs = ProgramService.get_all_programs(include_inactive=True)
    app_map = {a.id: a for a in applicants}
    prog_map = {p.id: p for p in programs}

    versions = AllocationService.get_all_versions()
    latest_ver = AllocationService.get_latest_committed()

    # Controls Section
    st.markdown("### Allocation Run Controls")
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.5, 1.2, 1, 1.5])

    with ctrl_col1:
        run_policy = st.selectbox(
            "Optimization Policy",
            [
                ("LEXICOGRAPHIC_PREFERENCE_FIRST", "Preference-First (Lexicographic)"),
                ("LEXICOGRAPHIC_STABILITY_FIRST", "Stability-First (Preserve Existing)"),
                ("BALANCED", "Balanced (Preference + Stability Weight)")
            ],
            format_func=lambda x: x[1]
        )[0]

    with ctrl_col2:
        time_limit = st.slider("Solver Time Limit (s)", min_value=5, max_value=60, value=15, step=5)

    with ctrl_col3:
        seed_val = st.number_input("Random Seed", value=42, step=1)

    with ctrl_col4:
        run_name = st.text_input("Run Label (Optional)", placeholder="e.g. Fall 2026 Batch Allocation").strip()

    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)

    with btn_col1:
        if st.button("🚀 Generate Initial Allocation", type="primary", use_container_width=True):
            with st.spinner("Formulating CP-SAT model and solving..."):
                ver, val = AllocationService.generate_allocation(
                    name=run_name or "Initial Allocation",
                    policy=run_policy,
                    use_baseline_as_anchor=False,
                    time_limit_seconds=time_limit,
                    random_seed=seed_val,
                    auto_commit=True
                )
                if val.is_valid:
                    st.success(f"Allocation run completed ({ver.solver_status}) in {ver.solve_duration_sec}s. Passed validation!")
                else:
                    st.error(f"Allocation run completed with solver {ver.solver_status}, but failed validation with {len(val.violations)} violation(s).")
                st.rerun()

    with btn_col2:
        if st.button("🔄 Run Reallocation", use_container_width=True):
            if not latest_ver:
                st.warning("No committed baseline allocation exists to anchor reallocation. Please run initial allocation first.")
            else:
                with st.spinner("Executing stability-preserving reallocation..."):
                    ver, val = AllocationService.generate_allocation(
                        name=run_name or f"Reallocation (Anchor v{latest_ver.version_number})",
                        policy=run_policy,
                        use_baseline_as_anchor=True,
                        baseline_version_id=latest_ver.id,
                        time_limit_seconds=time_limit,
                        random_seed=seed_val,
                        auto_commit=True
                    )
                    st.success(f"Reallocation v{ver.version_number} generated! Preserved: {ver.total_assigned - ver.assignments_changed}, Changed: {ver.assignments_changed}.")
                    st.rerun()

    with btn_col3:
        if st.button("🛡️ Validate Current Roster", use_container_width=True):
            if not latest_ver:
                st.info("No active allocation to validate.")
            else:
                val = AllocationValidator.validate(latest_ver.assignments, applicants, programs)
                if val.is_valid:
                    st.success(f"Validation PASSED: All {val.total_assignments_checked} assignments respect capacity, eligibility, and uniqueness rules.")
                else:
                    st.error(f"Validation FAILED: {len(val.violations)} rule violations detected.")
                    for v in val.violations[:5]:
                        st.markdown(f"- **{v.rule_code}**: {v.description}")

    with btn_col4:
        if latest_ver:
            st.download_button(
                label="📥 Export Current Results",
                data=lambda: export_allocation_to_csv(
                    AllocationService.get_latest_committed() or latest_ver,
                    {a.id: a for a in ApplicantService.get_all_applicants(include_withdrawn=True)},
                    {p.id: p for p in ProgramService.get_all_programs(include_inactive=True)}
                ),
                file_name=f"fairshift_allocation_v{latest_ver.version_number}.csv",
                mime="text/csv",
                key="btn_dl_allocation_csv",
                use_container_width=True
            )
        else:
            st.button("📥 Export Results", disabled=True, use_container_width=True)

    # Active Allocation Summary
    st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)

    if latest_ver:
        st.subheader(f"Current Committed Allocation: {latest_ver.name} (v{latest_ver.version_number})")

        s1, s2, s3, s4, s5, s6 = st.columns(6)
        with s1:
            st.metric("Solver Status", latest_ver.solver_status)
        with s2:
            st.metric("Validation", latest_ver.validation_result)
        with s3:
            st.metric("Solve Time", f"{latest_ver.solve_duration_sec}s")
        with s4:
            st.metric("Total Assigned", latest_ver.total_assigned)
        with s5:
            st.metric("Unassigned", latest_ver.total_unassigned)
        with s6:
            st.metric("Assignments Changed", latest_ver.assignments_changed)

        # Tabular assignment view
        st.markdown("#### Assignment Roster")
        asgn_rows = []
        for a in latest_ver.assignments:
            app = app_map.get(a.applicant_id)
            prog = prog_map.get(a.program_id)
            asgn_rows.append({
                "Applicant ID": a.applicant_id,
                "Applicant Name": app.full_name if app else "—",
                "Program ID": a.program_id,
                "Program Name": prog.name if prog else "—",
                "Preference Rank": f"Rank #{a.preference_rank}" if a.preference_rank else "Unranked",
                "Eligibility Verified": "Yes" if app and prog and app.is_eligible_for(prog.required_attributes) else "No",
                "Status": "Confirmed" if a.is_valid else "Invalid"
            })

        if asgn_rows:
            st.dataframe(pd.DataFrame(asgn_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active assignments in current version.")
    else:
        st.info("No allocation version has been generated yet. Click 'Generate Initial Allocation' above to begin.")

    # Historical Version Comparison
    if len(versions) >= 2:
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("Historical Version Comparison")
        cmp_col1, cmp_col2 = st.columns(2)
        v_options = {f"v{v.version_number} — {v.name} ({v.solver_status})": v.id for v in versions}

        with cmp_col1:
            v_a_label = st.selectbox("Baseline Version (A)", list(v_options.keys()), index=1)
            v_a_id = v_options[v_a_label]
        with cmp_col2:
            v_b_label = st.selectbox("Comparison Version (B)", list(v_options.keys()), index=0)
            v_b_id = v_options[v_b_label]

        if v_a_id != v_b_id:
            cmp_res = AllocationService.compare_versions(v_a_id, v_b_id)
            st.markdown(f"**Preserved Assignments:** `{cmp_res['preserved_count']}` | **Shifted Assignments:** `{cmp_res['changed_count']}`")
            if cmp_res["changes"]:
                st.dataframe(pd.DataFrame(cmp_res["changes"]), use_container_width=True, hide_index=True)
            else:
                st.success("Both versions have identical assignments.")
