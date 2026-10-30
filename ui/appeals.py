"""
PAGE 6: COUNTERFACTUAL APPEAL MANAGEMENT
Auditable appeal workflow with counterfactual mathematical re-optimization,
ripple effect analysis, and authorized administrative decisions.
"""

import streamlit as st
import pandas as pd
from services.appeal_service import AppealService
from services.applicant_service import ApplicantService
from services.program_service import ProgramService
from services.allocation_service import AllocationService

def render_appeals():
    st.markdown("""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="color: #0f172a; font-size: 1.85rem; font-weight: 700; margin-bottom: 0.25rem;">
                Counterfactual Appeal Management
            </h1>
            <p style="color: #475569; font-size: 0.95rem; margin: 0;">
                Evaluate seat assignment appeals using mathematical counterfactual optimization.
                Measure displacement ripples and provide verifiable evidence before administrative decisions.
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab_list, tab_submit, tab_decision = st.tabs([
        "📑 Appeals Roster & Analysis",
        "➕ Submit Seat Appeal",
        "⚖️ Administrative Decision"
    ])

    appeals = AppealService.get_all_appeals()
    applicants = ApplicantService.get_all_applicants(include_withdrawn=True)
    programs = ProgramService.get_all_programs(include_inactive=True)
    latest_ver = AllocationService.get_latest_committed()

    with tab_list:
        st.subheader("Submitted Appeals")
        if appeals:
            table_data = []
            for a in appeals:
                table_data.append({
                    "Appeal ID": a["id"],
                    "Applicant": f"{a['applicant_name']} ({a['applicant_id']})",
                    "Requested Cohort": a["requested_program_name"],
                    "Reason": a["reason"],
                    "Baseline": f"v{a['baseline_version_number']}",
                    "Status": a["status"],
                    "Decision": a["decision"] or "Pending",
                    "Submitted": a["created_at"][:19].replace("T", " ")
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

            st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
            st.subheader("Counterfactual Analysis Inspector")

            sel_apl_id = st.selectbox(
                "Select Appeal to Analyze",
                [a["id"] for a in appeals],
                format_func=lambda x: f"{x} — {next((a['applicant_name'] for a in appeals if a['id'] == x), '')}"
            )

            col_btn, col_res = st.columns([1, 2.5])
            with col_btn:
                time_lim = st.slider("Analysis Solver Time (s)", 5, 30, 10, key="apl_time_lim")
                if st.button("🔬 Run Counterfactual Optimization", type="primary", use_container_width=True):
                    with st.spinner("Solving counterfactual constrained model..."):
                        res = AppealService.run_counterfactual_analysis(sel_apl_id, time_limit_seconds=time_lim)
                        st.session_state[f"apl_res_{sel_apl_id}"] = res
                        st.success("Analysis complete!")
                        st.rerun()

            with col_res:
                analysis = st.session_state.get(f"apl_res_{sel_apl_id}")
                if not analysis:
                    _, analysis = AppealService.get_appeal_details(sel_apl_id)

                if analysis:
                    st.markdown(f"**Solver Status:** `{analysis.solver_status}` | **Accommodatable:** `{'YES' if analysis.is_accommodatable else 'NO'}`")
                    st.markdown(f"**Solve Duration:** `{analysis.solve_duration_sec}s`")
                    st.info(analysis.impact_summary)

                    if analysis.affected_applicant_ids:
                        st.markdown(f"**Applicants Displaced/Affected ({analysis.affected_applicants_count}):**")
                        st.write(", ".join([f"`{aid}`" for aid in analysis.affected_applicant_ids]))
                    else:
                        st.caption("No other applicant assignments would need to change.")
                else:
                    st.caption("Click 'Run Counterfactual Optimization' to calculate displacement metrics.")
        else:
            st.info("No appeals have been registered yet. Use the 'Submit Seat Appeal' tab to create one.")

    with tab_submit:
        st.subheader("Submit a New Allocation Appeal")
        if not latest_ver:
            st.warning("A committed baseline allocation is required before submitting an appeal.")
        else:
            asgn_map = {a.applicant_id: a for a in latest_ver.assignments}

            with st.form("submit_appeal_form"):
                app_options = [f"{a.id} — {a.full_name}" for a in applicants if not a.is_withdrawn]
                sel_app_opt = st.selectbox("Select Appellant", app_options)
                sel_app_id = sel_app_opt.split(" — ")[0]

                current_asgn = asgn_map.get(sel_app_id)
                current_asgn_str = f"Currently assigned to {current_asgn.program_id}" if current_asgn else "Currently unassigned"
                st.caption(f"Current Status: **{current_asgn_str}**")

                prog_options = [f"{p.id} — {p.name} (Cap: {p.capacity})" for p in programs if p.is_active]
                sel_prog_opt = st.selectbox("Requested Training Program", prog_options)
                sel_prog_id = sel_prog_opt.split(" — ")[0]

                appeal_reason = st.text_area(
                    "Appeal Justification & Hardship Reason *",
                    placeholder="Describe specific grounds for reconsideration, schedule conflict, or medical accommodation."
                )

                submit_btn = st.form_submit_button("Submit Appeal for Review", use_container_width=True)
                if submit_btn:
                    if not appeal_reason.strip():
                        st.error("Please provide an explicit appeal reason.")
                    else:
                        try:
                            apl = AppealService.submit_appeal(
                                applicant_id=sel_app_id,
                                requested_program_id=sel_prog_id,
                                reason=appeal_reason,
                                baseline_version_id=latest_ver.id
                            )
                            st.success(f"Appeal {apl.id} submitted successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error submitting appeal: {e}")

    with tab_decision:
        st.subheader("Administrative Decision & Justification")
        pending_or_analyzed = [a for a in appeals if a["status"] in ("PENDING", "ANALYZED")]

        if pending_or_analyzed:
            sel_dec_id = st.selectbox(
                "Select Appeal to Decide",
                [a["id"] for a in pending_or_analyzed],
                format_func=lambda x: f"{x} — {next((a['applicant_name'] for a in pending_or_analyzed if a['id'] == x), '')}"
            )
            appeal_obj, analysis_obj = AppealService.get_appeal_details(sel_dec_id)

            if appeal_obj:
                st.markdown(f"**Appellant:** `{appeal_obj.applicant_id}` | **Requested Program:** `{appeal_obj.requested_program_id}`")
                st.markdown(f"**Appellant Grounds:** *{appeal_obj.reason}*")

                if analysis_obj:
                    st.info(f"Counterfactual Impact: {analysis_obj.impact_summary}")
                else:
                    st.warning("Note: Counterfactual analysis has not been executed for this appeal yet.")

                col_dec, col_exp = st.columns([1, 2.5])
                with col_dec:
                    decision_choice = st.radio("Decision", ["APPROVED", "REJECTED"])
                with col_exp:
                    explanation = st.text_area("Administrative Decision Justification *", placeholder="Formal justification recorded for audit transparency.")

                if st.button("Record Binding Decision", type="primary"):
                    if not explanation.strip():
                        st.error("An administrative explanation is mandatory for audit compliance.")
                    else:
                        try:
                            AppealService.record_decision(appeal_obj.id, decision_choice, explanation)
                            st.success(f"Decision for appeal {appeal_obj.id} recorded as {decision_choice}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error recording decision: {e}")
        else:
            st.info("No appeals currently awaiting administrative decision.")
