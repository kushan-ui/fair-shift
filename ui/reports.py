"""
PAGE 9: REPORTS AND ANALYTICS
Structured analytical reporting, cohort fulfillment metrics, solver performance telemetry,
and verifiable CSV audit exports.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from services.reporting_service import ReportingService
from services.allocation_service import AllocationService
from services.program_service import ProgramService
from services.applicant_service import ApplicantService
from services.appeal_service import AppealService
from utils.csv_export import export_allocation_to_csv

def render_reports():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Reports & Analytical Exports
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Comprehensive institutional reporting, solver telemetry, and data exports.
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab_alloc, tab_prog, tab_perf, tab_appeals = st.tabs([
        "📊 Current Allocation Report",
        "🏢 Program Cohort Utilization",
        "⚡ Solver Performance Telemetry",
        "⚖️ Appeal Impact Summary"
    ])

    latest_ver = AllocationService.get_latest_committed()
    applicants = ApplicantService.get_all_applicants(include_withdrawn=True)
    programs = ProgramService.get_all_programs(include_inactive=True)
    app_map = {a.id: a for a in applicants}
    prog_map = {p.id: p for p in programs}

    with tab_alloc:
        st.subheader("Applicant-Level Seat Assignment Report")
        if latest_ver:
            st.markdown(f"**Dataset Source:** Current Production Allocation `v{latest_ver.version_number}` (*{latest_ver.name}*)")
            table_data = ReportingService.get_assignment_table_data(latest_ver.id)

            if table_data:
                df_asgn = pd.DataFrame(table_data)
                st.dataframe(df_asgn, use_container_width=True, hide_index=True)

                st.download_button(
                    label="📥 Download Complete Assignment Report (CSV)",
                    data=lambda: export_allocation_to_csv(
                        latest_ver,
                        {a.id: a for a in ApplicantService.get_all_applicants(include_withdrawn=True)},
                        {p.id: p for p in ProgramService.get_all_programs(include_inactive=True)}
                    ),
                    file_name=f"fairshift_assignment_report_v{latest_ver.version_number}.csv",
                    mime="text/csv",
                    key="btn_dl_report_assignments_csv"
                )
            else:
                st.info("No assignments recorded in current version.")
        else:
            st.info("No committed allocation version found.")

    with tab_prog:
        st.subheader("Program Seat Enrollment & Capacity Utilization")
        metrics = ReportingService.get_dashboard_metrics()
        if metrics["program_summary"]:
            df_ps = pd.DataFrame(metrics["program_summary"])
            st.dataframe(df_ps, use_container_width=True, hide_index=True)

            st.download_button(
                label="📥 Download Program Capacity Report (CSV)",
                data=lambda: pd.DataFrame(ReportingService.get_dashboard_metrics()["program_summary"]).to_csv(index=False),
                file_name="fairshift_program_utilization.csv",
                mime="text/csv",
                key="btn_dl_report_programs_csv"
            )
        else:
            st.info("No program utilization records.")

    with tab_perf:
        st.subheader("Solver Performance & Optimization History")
        versions = AllocationService.get_all_versions()
        if versions:
            v_rows = []
            for v in versions:
                v_rows.append({
                    "Version": f"v{v.version_number}",
                    "Name": v.name,
                    "Policy": v.policy,
                    "Solver Status": v.solver_status,
                    "Validation": v.validation_result,
                    "Solve Duration (s)": v.solve_duration_sec,
                    "Assigned Applicants": v.total_assigned,
                    "Unassigned Applicants": v.total_unassigned,
                    "Disruptions / Changes": v.assignments_changed,
                    "Timestamp": v.created_at[:19].replace("T", " ")
                })
            df_v = pd.DataFrame(v_rows)
            st.dataframe(df_v, use_container_width=True, hide_index=True)

            fig_time = px.line(
                df_v,
                x="Version",
                y="Solve Duration (s)",
                markers=True,
                title="Solver Solve Duration Across Allocation Versions",
                line_shape="linear"
            )
            fig_time.update_layout(plot_bgcolor="#ffffff", paper_bgcolor="#ffffff")
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("No allocation versions to report.")

    with tab_appeals:
        st.subheader("Appeals & Counterfactual Impact Analytics")
        appeals = AppealService.get_all_appeals()
        if appeals:
            df_apl = pd.DataFrame(appeals)
            st.dataframe(df_apl[["id", "applicant_id", "applicant_name", "requested_program_name", "status", "decision", "created_at"]], use_container_width=True, hide_index=True)

            st.download_button(
                label="📥 Download Appeals Report (CSV)",
                data=lambda: pd.DataFrame(AppealService.get_all_appeals()).to_csv(index=False),
                file_name="fairshift_appeals_report.csv",
                mime="text/csv",
                key="btn_dl_report_appeals_csv"
            )
        else:
            st.info("No appeals registered in database.")
