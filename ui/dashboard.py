"""
PAGE 1: EXECUTIVE DASHBOARD
Live metrics, enterprise charts, solver status, and real-time operational posture.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.reporting_service import ReportingService

def render_dashboard():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Executive Dashboard
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Live operational metrics, solver status, and system-wide allocation health.
            </p>
        </div>
    """, unsafe_allow_html=True)

    metrics = ReportingService.get_dashboard_metrics()

    # System Status Bar
    solver_status = metrics["solver_status"]
    val_status = metrics["validation_result"]

    solver_bg = "#dcfce7" if solver_status == "OPTIMAL" else ("#fef9c3" if solver_status == "FEASIBLE" else "#fee2e2" if solver_status in ("INFEASIBLE", "MODEL_INVALID") else "#f1f5f9")
    solver_color = "#166534" if solver_status == "OPTIMAL" else ("#854d0e" if solver_status == "FEASIBLE" else "#991b1b" if solver_status in ("INFEASIBLE", "MODEL_INVALID") else "#475569")

    val_bg = "#dcfce7" if val_status == "PASS" else ("#fee2e2" if val_status == "FAIL" else "#f1f5f9")
    val_color = "#166534" if val_status == "PASS" else ("#991b1b" if val_status == "FAIL" else "#475569")

    st.markdown(f"""
        <div style="display: flex; gap: 1rem; align-items: center; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.75rem 1.25rem; margin-bottom: 1.5rem;">
            <div style="font-weight: 600; color: #1e293b; font-size: 0.9rem;">System State:</div>
            <div style="background: {solver_bg}; color: {solver_color}; font-weight: 600; font-size: 0.8rem; padding: 0.25rem 0.65rem; border-radius: 9999px;">
                SOLVER: {solver_status}
            </div>
            <div style="background: {val_bg}; color: {val_color}; font-weight: 600; font-size: 0.8rem; padding: 0.25rem 0.65rem; border-radius: 9999px;">
                VALIDATOR: {val_status}
            </div>
            <div style="margin-left: auto; color: #64748b; font-size: 0.85rem;">
                Last Allocation: <b>{metrics['last_allocation_time'] or 'No Run Recorded'}</b>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Key Stat Cards Row 1: Applicants & Programs
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="Total Applicants",
            value=metrics["total_applicants"],
            delta=f"{metrics['withdrawn_applicants']} Withdrawn" if metrics['withdrawn_applicants'] else "All Active",
            delta_color="off"
        )
    with col2:
        st.metric(
            label="Total Seat Capacity",
            value=metrics["total_capacity"],
            delta=f"{metrics['active_programs']} Programs",
            delta_color="off"
        )
    with col3:
        st.metric(
            label="Assigned Applicants",
            value=metrics["assigned_applicants"],
            delta=f"{metrics['available_seats']} Seats Remaining",
            delta_color="normal"
        )
    with col4:
        st.metric(
            label="Unassigned Applicants",
            value=metrics["unassigned_applicants"],
            delta="Pending Placement" if metrics["unassigned_applicants"] > 0 else "Fully Placed",
            delta_color="inverse" if metrics["unassigned_applicants"] > 0 else "off"
        )
    with col5:
        st.metric(
            label="Pending Appeals",
            value=metrics["pending_appeals"],
            delta="Awaiting Review" if metrics["pending_appeals"] > 0 else "Clear",
            delta_color="inverse" if metrics["pending_appeals"] > 0 else "off"
        )

    # Key Stat Cards Row 2: Satisfaction & Stability
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="1st-Choice Satisfaction",
            value=f"{metrics['first_pref_rate']}%",
            delta=f"{metrics['first_pref_satisfied']} Applicants",
            delta_color="normal"
        )
    with c2:
        st.metric(
            label="Top-3 Satisfaction",
            value=f"{metrics['top_three_rate']}%",
            delta=f"{metrics['top_three_satisfied']} Applicants",
            delta_color="normal"
        )
    with c3:
        st.metric(
            label="Assignments Disrupted",
            value=metrics["assignments_changed"],
            delta="Reassigned / Changed",
            delta_color="off"
        )
    with c4:
        st.metric(
            label="Seat Utilization",
            value=f"{round((metrics['assigned_applicants']/metrics['total_capacity']*100), 1)}%" if metrics['total_capacity'] > 0 else "0%",
            delta="Active Enrollment",
            delta_color="normal"
        )

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

    # Visual Analytics Row
    chart_col1, chart_col2 = st.columns([1.6, 1.0])

    with chart_col1:
        st.subheader("Program Capacity vs. Enrolled Seats")
        if metrics["program_summary"]:
            df_progs = pd.DataFrame(metrics["program_summary"])
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                name="Enrolled",
                x=df_progs["name"],
                y=df_progs["enrolled"],
                marker_color="#2563eb"
            ))
            fig_bar.add_trace(go.Bar(
                name="Remaining Available",
                x=df_progs["name"],
                y=df_progs["remaining_seats"],
                marker_color="#93c5fd"
            ))
            fig_bar.update_layout(
                barmode="stack",
                height=340,
                margin=dict(l=20, r=20, t=20, b=80),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(tickangle=-30),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No training program data recorded.")

    with chart_col2:
        st.subheader("Preference Satisfaction")
        dist = metrics["preference_distribution"]
        if any(dist.values()):
            labels = list(dist.keys())
            values = list(dist.values())
            colors = ["#16a34a", "#3b82f6", "#60a5fa", "#93c5fd", "#cbd5e1"]
            fig_donut = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors),
                textinfo="label+value"
            )])
            fig_donut.update_layout(
                height=340,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=False,
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff"
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No allocation results to chart.")

    # Recent Activity Row
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    hist_col1, hist_col2 = st.columns(2)

    with hist_col1:
        st.subheader("Recent Audit Activity")
        if metrics["recent_audit_logs"]:
            audit_display = []
            for log in metrics["recent_audit_logs"][:6]:
                audit_display.append({
                    "Timestamp": log["timestamp"][:19].replace("T", " "),
                    "Event": log["event_type"],
                    "Outcome": log["outcome"],
                    "Target ID": log.get("applicant_id") or log.get("program_id") or log.get("allocation_version_id") or "—"
                })
            st.dataframe(pd.DataFrame(audit_display), use_container_width=True, hide_index=True)
        else:
            st.caption("No audit activity logged yet.")

    with hist_col2:
        st.subheader("Recent Capacity Changes")
        if metrics["recent_capacity_changes"]:
            cap_display = []
            for ch in metrics["recent_capacity_changes"]:
                cap_display.append({
                    "Date": ch["changed_at"][:19].replace("T", " "),
                    "Program": ch["program_name"],
                    "Old": ch["old_capacity"],
                    "New": ch["new_capacity"],
                    "Reason": ch["reason"] or "Adjustment"
                })
            st.dataframe(pd.DataFrame(cap_display), use_container_width=True, hide_index=True)
        else:
            st.caption("No program capacity changes recorded.")
