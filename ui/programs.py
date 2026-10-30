"""
PAGE 3: TRAINING PROGRAM MANAGEMENT
Program catalog, seat capacity adjustments, required eligibility criteria,
live enrollment tracking, and capacity change audit trails.
"""

import streamlit as st
import pandas as pd
from models.program import Program
from services.program_service import ProgramService
from services.allocation_service import AllocationService
from utils.csv_export import export_programs_to_csv

def render_programs():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Training Program Management
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Configure program cohorts, adjust seat quotas, enforce prerequisites, and audit capacity history.
            </p>
        </div>
    """, unsafe_allow_html=True)

    programs = ProgramService.get_all_programs(include_inactive=True)
    latest_ver = AllocationService.get_latest_committed()
    assignments = latest_ver.assignments if latest_ver else []

    # Map current enrollment per program
    enrollment_counts = {p.id: 0 for p in programs}
    enrolled_applicants = {p.id: [] for p in programs}
    for a in assignments:
        if a.program_id in enrollment_counts:
            enrollment_counts[a.program_id] += 1
            enrolled_applicants[a.program_id].append(a.applicant_id)

    tab_overview, tab_adjust, tab_new = st.tabs([
        "🏢 Program Roster & Enrollment",
        "⚙️ Modify Seat Capacity",
        "➕ Add New Program"
    ])

    with tab_overview:
        prog_table = []
        for p in programs:
            enr = enrollment_counts.get(p.id, 0)
            avail = max(0, p.capacity - enr)
            util = f"{round((enr / p.capacity * 100), 1)}%" if p.capacity > 0 else "0%"
            prog_table.append({
                "Program ID": p.id,
                "Program Name": p.name,
                "Capacity": p.capacity,
                "Enrolled": enr,
                "Available": avail,
                "Utilization": util,
                "Required Prerequisites": ", ".join(p.required_attributes) if p.required_attributes else "Open Admission",
                "Status": "ACTIVE" if p.is_active else "INACTIVE"
            })

        st.dataframe(pd.DataFrame(prog_table), use_container_width=True, hide_index=True)

        # Enrolled Applicants Inspector
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("Cohort Roster Inspector")
        col_sel, col_roster = st.columns([1.5, 2.5])
        with col_sel:
            sel_pid = st.selectbox("Select Program", [p.id for p in programs])
            sel_prog = next((p for p in programs if p.id == sel_pid), None)
        with col_roster:
            if sel_prog:
                st.markdown(f"**Program:** {sel_prog.name} (`{sel_prog.id}`)")
                st.markdown(f"**Capacity:** {sel_prog.capacity} | **Enrolled:** {enrollment_counts.get(sel_prog.id, 0)}")
                cohort = enrolled_applicants.get(sel_prog.id, [])
                if cohort:
                    st.markdown("**Assigned Applicants:** " + ", ".join([f"`{aid}`" for aid in cohort]))
                else:
                    st.caption("No applicants currently assigned to this cohort.")

        # Export programs CSV
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Export Program Catalog (CSV)",
            data=lambda: export_programs_to_csv(ProgramService.get_all_programs(include_inactive=True)),
            file_name="fairshift_programs.csv",
            mime="text/csv",
            key="btn_dl_programs_csv"
        )

    with tab_adjust:
        st.subheader("Adjust Program Seat Capacity")
        st.caption("All capacity changes are recorded in the append-only capacity history audit log.")

        c_prog, c_cap, c_reason = st.columns([2, 1, 2])
        with c_prog:
            adj_pid = st.selectbox("Select Program to Adjust", [f"{p.id} — {p.name}" for p in programs], key="adj_sel")
            target_pid = adj_pid.split(" — ")[0]
            target_p = next((p for p in programs if p.id == target_pid), None)
        with c_cap:
            new_capacity = st.number_input(
                "New Capacity",
                min_value=0,
                max_value=500,
                value=target_p.capacity if target_p else 10,
                step=1
            )
        with c_reason:
            reason = st.text_input("Operational Justification", placeholder="e.g. Added secondary instructor").strip()

        if st.button("Apply Capacity Update", type="primary"):
            try:
                res = ProgramService.change_capacity(target_pid, new_capacity, reason)
                if res.get("warning"):
                    st.warning(res["warning"])
                else:
                    st.success(f"Updated capacity for {target_pid} from {res['old_capacity']} to {res['new_capacity']}.")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating capacity: {e}")

        # Show Capacity History Table
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("Capacity Change History")
        history = ProgramService.get_capacity_history()
        if history:
            h_rows = []
            for h in history:
                h_rows.append({
                    "Timestamp": h["changed_at"][:19].replace("T", " "),
                    "Program": h["program_name"],
                    "Old Capacity": h["old_capacity"],
                    "New Capacity": h["new_capacity"],
                    "Reason": h["reason"] or "—"
                })
            st.dataframe(pd.DataFrame(h_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No capacity modifications recorded.")

    with tab_new:
        st.subheader("Register a New Training Program")
        with st.form("new_program_form"):
            col_id, col_name, col_cap = st.columns([1, 2, 1])
            with col_id:
                np_id = st.text_input("Program ID *", placeholder="PROG-NEW").strip()
            with col_name:
                np_name = st.text_input("Program Name *", placeholder="Quantum Computing Fundamentals").strip()
            with col_cap:
                np_cap = st.number_input("Seat Capacity *", min_value=1, max_value=200, value=20, step=1)

            np_desc = st.text_area("Description", placeholder="Course scope, objectives, and prerequisites.")

            available_attrs = ["STEM", "SECURITY_CLEARANCE", "LIFE_SCIENCES", "FINANCE_MATH", "ENVIRONMENTAL_SCI", "VETERAN"]
            np_reqs = st.multiselect("Mandatory Prerequisites / Eligibility Tags", available_attrs)

            submit_new_prog = st.form_submit_button("Create Training Program", use_container_width=True)
            if submit_new_prog:
                if not np_id or not np_name:
                    st.error("Program ID and Name are required.")
                else:
                    try:
                        ProgramService.create_program(
                            program_id=np_id,
                            name=np_name,
                            capacity=np_cap,
                            description=np_desc,
                            required_attributes=np_reqs
                        )
                        st.success(f"Program '{np_name}' created successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create program: {e}")
