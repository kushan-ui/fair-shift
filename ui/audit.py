"""
PAGE 8: AUDIT LOGS AND HISTORY
Immutable append-only operational log recording every allocation, appeal,
capacity shift, applicant status change, and administrative decision.
"""

import streamlit as st
import pandas as pd
import json
from services.audit_service import AuditService
from utils.csv_export import export_audit_logs_to_csv

def render_audit():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Audit Logs & Operational History
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Cryptographically trace every administrative action, solver execution, appeal decision, and system modification.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Filtering Controls
    f_c1, f_c2, f_c3, f_c4 = st.columns([1.5, 1, 1, 1])

    with f_c1:
        event_types = [
            "All Events",
            "ALLOCATION_RUN",
            "ALLOCATION_COMMITTED",
            "APPLICANT_CREATED",
            "APPLICANT_UPDATED",
            "APPLICANT_WITHDRAWN",
            "APPLICANT_REACTIVATED",
            "PROGRAM_CREATED",
            "PROGRAM_UPDATED",
            "CAPACITY_CHANGED",
            "APPEAL_SUBMITTED",
            "APPEAL_ANALYZED",
            "APPEAL_DECISION"
        ]
        sel_event = st.selectbox("Filter Event Type", event_types)
        event_filter = None if sel_event == "All Events" else sel_event

    with f_c2:
        app_filter = st.text_input("Applicant ID", placeholder="e.g. APP-014").strip() or None
    with f_c3:
        prog_filter = st.text_input("Program ID", placeholder="e.g. PROG-AI").strip() or None
    with f_c4:
        limit_val = st.selectbox("Log Limit", [50, 100, 200, 500], index=2)

    logs = AuditService.get_logs(
        limit=limit_val,
        event_type=event_filter,
        applicant_id=app_filter,
        program_id=prog_filter
    )

    st.caption(f"Displaying {len(logs)} audit entries")

    if logs:
        # Table view
        log_rows = []
        for l in logs:
            log_rows.append({
                "Log ID": l["id"],
                "Timestamp (UTC)": l["timestamp"][:19].replace("T", " "),
                "Event Type": l["event_type"],
                "Outcome": l["outcome"],
                "Applicant ID": l["applicant_id"] or "—",
                "Program ID": l["program_id"] or "—",
                "Version": l["allocation_version_id"] or "—",
                "Details": json.dumps(l["details"])
            })

        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)

        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("Event Detail Inspector")

        sel_log_id = st.selectbox("Select Log ID to Inspect Details", [l["id"] for l in logs])
        target_log = next((l for l in logs if l["id"] == sel_log_id), None)
        if target_log:
            st.json(target_log["details"])

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Export Audit History to CSV",
            data=lambda: export_audit_logs_to_csv(AuditService.get_logs(
                limit=limit_val,
                event_type=event_filter,
                applicant_id=app_filter,
                program_id=prog_filter
            )),
            file_name="fairshift_audit_log.csv",
            mime="text/csv",
            key="btn_dl_audit_logs_csv"
        )
    else:
        st.info("No audit logs matching criteria.")
