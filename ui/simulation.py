"""
PAGE 5: REAL-TIME REASSIGNMENT SIMULATION
Interactive sandbox for what-if scenarios (capacity cuts, applicant withdrawals, program deactivations).
Guarantees baseline immutability until explicit administrative commit.
"""

import streamlit as st
import pandas as pd
from services.allocation_service import AllocationService
from services.program_service import ProgramService
from services.applicant_service import ApplicantService
from services.reassignment_service import ReassignmentService
from database.repositories import AllocationRepository

def render_simulation():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Real-Time Reassignment Simulation
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Test hypothetical disruption scenarios without mutating production records.
                Quantify displacement ripples, seat preservation, and net preference impacts.
            </p>
        </div>
    """, unsafe_allow_html=True)

    latest_ver = AllocationService.get_latest_committed()
    if not latest_ver:
        st.warning("A committed baseline allocation is required before running simulations. Please run an initial allocation first.")
        return

    programs = ProgramService.get_all_programs(include_inactive=True)
    applicants = ApplicantService.get_all_applicants(include_withdrawn=True)

    st.markdown(f"**Baseline Anchor:** Version `{latest_ver.version_number}` — *{latest_ver.name}* (Assigned: {latest_ver.total_assigned}, Score: {latest_ver.preference_satisfaction_score})")

    # Simulation Parameter Config
    st.subheader("1. Configure Hypothetical Disruptions")
    sim_col1, sim_col2 = st.columns(2)

    with sim_col1:
        st.markdown("**Program Capacity Adjustments**")
        prog_choices = [p.id for p in programs]
        sel_sim_pid = st.selectbox("Select Program to Adjust Capacity", prog_choices, key="sim_pid_sel")
        prog_obj = next((p for p in programs if p.id == sel_sim_pid), None)
        default_cap = prog_obj.capacity if prog_obj else 10
        new_sim_cap = st.number_input(f"Simulated Capacity for {sel_sim_pid} (Current: {default_cap})", min_value=0, max_value=200, value=default_cap, key="sim_cap_val")

        deact_progs = st.multiselect("Temporarily Deactivate Programs", [p.id for p in programs if p.is_active])

    with sim_col2:
        st.markdown("**Applicant Status Overrides**")
        active_apps = [f"{a.id} — {a.full_name}" for a in applicants if not a.is_withdrawn and a.status != "WITHDRAWN"]
        withdrawn_apps = [f"{a.id} — {a.full_name}" for a in applicants if a.is_withdrawn or a.status == "WITHDRAWN"]

        sim_withdrawals = st.multiselect("Simulate Applicant Withdrawals", active_apps, key="sim_withdrawals")
        sim_reactivations = st.multiselect("Simulate Applicant Reactivations", withdrawn_apps, key="sim_reactivations")

    sim_withdrawn_ids = [w.split(" — ")[0] for w in sim_withdrawals]
    sim_reactivated_ids = [r.split(" — ")[0] for r in sim_reactivations]

    cap_overrides = {}
    if new_sim_cap != default_cap:
        cap_overrides[sel_sim_pid] = new_sim_cap

    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    if st.button("🧪 Run What-If Simulation", type="primary", use_container_width=True):
        with st.spinner("Simulating mathematical reallocation with stability objective..."):
            sim_res = ReassignmentService.simulate_scenario(
                baseline_version_id=latest_ver.id,
                capacity_overrides=cap_overrides,
                withdrawn_applicant_ids=sim_withdrawn_ids,
                reactivated_applicant_ids=sim_reactivated_ids,
                inactive_program_ids=deact_progs
            )
            st.session_state["sim_result"] = sim_res

    # Display Simulation Results
    sim_res = st.session_state.get("sim_result")
    if sim_res:
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("2. Simulation Impact Analysis")

        # Key Metrics Row
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Solver Status", sim_res["solver_status"])
        with m2:
            st.metric("Validation", sim_res["validation_status"])
        with m3:
            st.metric(
                "Assigned Seats",
                sim_res["total_assigned"],
                delta=f"{sim_res['total_assigned'] - sim_res['baseline_assigned']:+d} vs Baseline",
                delta_color="normal"
            )
        with m4:
            st.metric(
                "Seats Preserved",
                sim_res["preserved_count"],
                delta="No Disruption",
                delta_color="normal"
            )
        with m5:
            st.metric(
                "Assignments Changed",
                sim_res["changed_count"],
                delta="Displaced / Reassigned",
                delta_color="inverse" if sim_res["changed_count"] > 0 else "off"
            )

        # Before-vs-After Comparison Table
        st.markdown("#### Before vs. After Assignment Shift Table")
        if sim_res["comparison_rows"]:
            df_comp = pd.DataFrame(sim_res["comparison_rows"])
            st.dataframe(df_comp, use_container_width=True, hide_index=True)
        else:
            st.success("Zero assignment disruptions! All existing confirmed seats were preserved.")

        # Commit Option with explicit confirmation
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("3. Production Commit Authorization")
        st.caption("Committing this simulation will promote the simulated allocation into a new permanent production version.")

        confirm_commit = st.checkbox("I authorize promoting this simulated scenario into the active allocation baseline.")
        if st.button("💾 Commit Scenario to Production", disabled=not confirm_commit, type="primary"):
            if not sim_res.get("validation_status") == "PASS":
                st.error("Cannot commit a simulation that has not passed independent validation.")
            else:
                with st.spinner("Committing simulation to database..."):
                    # Apply capacity changes if any
                    for pid, cap in cap_overrides.items():
                        ProgramService.change_capacity(pid, cap, "Applied from committed simulation scenario")
                    for wid in sim_withdrawn_ids:
                        ApplicantService.set_withdrawal_status(wid, True)
                    for rid in sim_reactivated_ids:
                        ApplicantService.set_withdrawal_status(rid, False)

                    # Generate new committed version anchoring on simulated assignments
                    ver, val = AllocationService.generate_allocation(
                        name="Committed Simulation Scenario",
                        policy="LEXICOGRAPHIC_PREFERENCE_FIRST",
                        use_baseline_as_anchor=True,
                        baseline_version_id=latest_ver.id,
                        auto_commit=True
                    )
                    st.success(f"Simulation committed as Version {ver.version_number}!")
                    del st.session_state["sim_result"]
                    st.rerun()
