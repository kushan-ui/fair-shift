"""
PAGE 2: APPLICANT MANAGEMENT
Comprehensive applicant lifecycle: roster, filtering, registration, ranked preferences,
withdrawal management, CSV import/export, and assignment history.
"""

import streamlit as st
import pandas as pd
from typing import List
from models.applicant import Applicant, Preference
from services.applicant_service import ApplicantService
from services.program_service import ProgramService
from services.allocation_service import AllocationService
from utils.csv_import import parse_applicants_csv
from utils.csv_export import export_applicants_to_csv
from database.repositories import ApplicantRepository

def render_applicants():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Applicant Management
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Manage candidates, declared eligibility attributes, ranked preferences, and active/withdrawn status.
            </p>
        </div>
    """, unsafe_allow_html=True)

    applicants = ApplicantService.get_all_applicants(include_withdrawn=True)
    programs = ProgramService.get_all_programs(include_inactive=True)
    prog_map = {p.id: p.name for p in programs}
    latest_ver = AllocationService.get_latest_committed()
    asgn_map = {a.applicant_id: a for a in (latest_ver.assignments if latest_ver else [])}

    tab_roster, tab_add, tab_import_export = st.tabs([
        "📋 Applicant Directory",
        "➕ Register Applicant",
        "📥 CSV Import / Export"
    ])

    with tab_roster:
        # Search & Filter Controls
        f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
        with f_col1:
            search_query = st.text_input("🔍 Search by ID or Name", placeholder="e.g. APP-005 or Jordan").strip().lower()
        with f_col2:
            status_filter = st.selectbox("Status Filter", ["All", "Active Only", "Withdrawn Only"])
        with f_col3:
            asgn_filter = st.selectbox("Seat Status", ["All", "Assigned Only", "Unassigned Only"])

        # Filter applicants
        filtered = []
        for app in applicants:
            if search_query and (search_query not in app.id.lower() and search_query not in app.full_name.lower()):
                continue
            if status_filter == "Active Only" and (app.is_withdrawn or app.status == "WITHDRAWN"):
                continue
            if status_filter == "Withdrawn Only" and not (app.is_withdrawn or app.status == "WITHDRAWN"):
                continue

            has_asgn = app.id in asgn_map
            if asgn_filter == "Assigned Only" and not has_asgn:
                continue
            if asgn_filter == "Unassigned Only" and has_asgn:
                continue

            filtered.append(app)

        st.caption(f"Showing {len(filtered)} of {len(applicants)} applicants")

        # Table representation
        table_rows = []
        for a in filtered:
            asgn = asgn_map.get(a.id)
            asgn_str = f"{asgn.program_id} ({prog_map.get(asgn.program_id, '')}) [Rank {asgn.preference_rank}]" if asgn else "Unassigned"
            table_rows.append({
                "Applicant ID": a.id,
                "Full Name": a.full_name,
                "Status": "WITHDRAWN" if (a.is_withdrawn or a.status == "WITHDRAWN") else "ACTIVE",
                "Eligibility Tags": ", ".join(a.eligibility_attributes) if a.eligibility_attributes else "—",
                "Preferences": " > ".join([p.program_id for p in sorted(a.preferences, key=lambda x: x.preference_rank)]) if a.preferences else "None",
                "Current Seat": asgn_str
            })

        if table_rows:
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No applicants found matching filter criteria.")

        # Individual Applicant Inspector / Actions
        st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
        st.subheader("Manage Individual Applicant")

        sel_col1, sel_col2 = st.columns([1.5, 2.5])
        with sel_col1:
            app_options = [f"{a.id} — {a.full_name}" for a in applicants]
            if app_options:
                selected_opt = st.selectbox("Select Applicant to Inspect / Modify", app_options)
                selected_id = selected_opt.split(" — ")[0]
                sel_app = next((a for a in applicants if a.id == selected_id), None)
            else:
                sel_app = None

        with sel_col2:
            if sel_app:
                st.markdown(f"**ID:** `{sel_app.id}` | **Name:** `{sel_app.full_name}` | **Email:** `{sel_app.email or 'N/A'}`")
                st.markdown(f"**Eligibility Attributes:** `{', '.join(sel_app.eligibility_attributes) or 'None'}`")

                asgn = asgn_map.get(sel_app.id)
                if asgn:
                    st.success(f"Confirmed Placement: **{asgn.program_id}** — {prog_map.get(asgn.program_id, '')} (Preference Rank #{asgn.preference_rank})")
                else:
                    st.warning("Currently Unassigned")

                act_col1, act_col2 = st.columns(2)
                with act_col1:
                    if sel_app.is_withdrawn or sel_app.status == "WITHDRAWN":
                        if st.button("🟢 Reactivate Applicant", key=f"reactivate_{sel_app.id}"):
                            ApplicantService.set_withdrawal_status(sel_app.id, False)
                            st.success(f"Applicant {sel_app.id} reactivated successfully.")
                            st.rerun()
                    else:
                        if st.button("🚫 Withdraw Applicant", key=f"withdraw_{sel_app.id}"):
                            ApplicantService.set_withdrawal_status(sel_app.id, True)
                            st.warning(f"Applicant {sel_app.id} marked as withdrawn.")
                            st.rerun()

    with tab_add:
        st.subheader("Register a New Applicant")
        with st.form("add_applicant_form"):
            c_id, c_name, c_email = st.columns([1, 2, 2])
            with c_id:
                new_id = st.text_input("Applicant ID *", placeholder="APP-201").strip()
            with c_name:
                new_name = st.text_input("Full Name *", placeholder="Jane Doe").strip()
            with c_email:
                new_email = st.text_input("Email (Optional)", placeholder="jane.doe@example.org").strip()

            available_attrs = ["STEM", "SECURITY_CLEARANCE", "LIFE_SCIENCES", "FINANCE_MATH", "ENVIRONMENTAL_SCI", "VETERAN"]
            sel_attrs = st.multiselect("Eligibility Attributes", available_attrs, default=["STEM"])

            st.markdown("**Ranked Program Preferences** (Ordered 1st choice to 5th choice)")
            p_cols = st.columns(5)
            pref_selections = []
            prog_choices = ["None"] + [p.id for p in programs]

            for idx, col in enumerate(p_cols):
                with col:
                    choice = st.selectbox(f"Preference #{idx+1}", prog_choices, key=f"new_pref_{idx}")
                    if choice != "None" and choice not in pref_selections:
                        pref_selections.append(choice)

            submitted = st.form_submit_button("Register Candidate", use_container_width=True)
            if submitted:
                if not new_id or not new_name:
                    st.error("Applicant ID and Full Name are strictly required.")
                elif not pref_selections:
                    st.error("Please specify at least one ranked program preference.")
                else:
                    try:
                        prefs = [Preference(program_id=pid, preference_rank=i+1) for i, pid in enumerate(pref_selections)]
                        ApplicantService.create_applicant(
                            applicant_id=new_id,
                            full_name=new_name,
                            email=new_email,
                            eligibility_attributes=sel_attrs,
                            preferences=prefs
                        )
                        st.success(f"Applicant {new_id} ({new_name}) registered successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error registering applicant: {e}")

    with tab_import_export:
        st.subheader("Data Portability")
        imp_col, exp_col = st.columns(2)

        with imp_col:
            st.markdown("### Import Applicants (CSV)")
            st.caption("Expected columns: `id`, `full_name`, `email`, `eligibility_attributes` (semicolon-separated), `preferences` (semicolon-separated program IDs).")
            uploaded_file = st.file_uploader("Upload Applicant CSV", type=["csv"], key="applicant_csv_uploader")
            if uploaded_file is not None:
                content = uploaded_file.getvalue().decode("utf-8")
                valid_apps, errs = parse_applicants_csv(content)
                if errs:
                    for err in errs[:5]:
                        st.error(err)
                    if len(errs) > 5:
                        st.error(f"...and {len(errs) - 5} more errors.")
                if valid_apps:
                    st.info(f"Parsed {len(valid_apps)} valid applicant records ready for import.")
                    if st.button("Confirm and Import Roster"):
                        ApplicantRepository.bulk_create(valid_apps)
                        st.success(f"Successfully imported {len(valid_apps)} applicants.")
                        st.rerun()

        with exp_col:
            st.markdown("### Export Applicants (CSV)")
            st.caption("Download complete applicant database including declared preferences and attributes.")
            st.download_button(
                label="📥 Download Applicants CSV",
                data=lambda: export_applicants_to_csv(ApplicantService.get_all_applicants(include_withdrawn=True)),
                file_name="fairshift_applicants.csv",
                mime="text/csv",
                key="btn_dl_applicants_csv",
                use_container_width=True
            )
