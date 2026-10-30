"""
FAIRSHIFT — Fair Allocation, Reassignment, and Impact Analysis System
Main Streamlit Application Entrypoint
Transparent Allocation. Minimal Disruption. Verifiable Decisions.
"""

import streamlit as st
from database.db import init_db, reset_db
from database.repositories import ApplicantRepository, ProgramRepository, AllocationRepository
from utils.demo_data import generate_demo_programs, generate_demo_applicants
from services.allocation_service import AllocationService
from services.audit_service import AuditService

# UI Pages
from ui.dashboard import render_dashboard
from ui.applicants import render_applicants
from ui.programs import render_programs
from ui.allocation import render_allocation
from ui.simulation import render_simulation
from ui.appeals import render_appeals
from ui.validation import render_validation
from ui.audit import render_audit
from ui.reports import render_reports

# Page configuration
st.set_page_config(
    page_title="FAIRSHIFT — Allocation & Impact Analysis System",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise Dashboard Styling
st.markdown("""
<style>
    /* Main container and font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Top title & branding */
    .brand-header {
        background: #0f172a;
        color: #ffffff;
        padding: 1.25rem 1.75rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Metric styling */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
        color: #0f172a;
        font-weight: 700;
    }
    
    /* Tab headers */
    button[data-baseweb="tab"] {
        font-size: 0.95rem;
        font-weight: 600;
        color: #475569;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Badges */
    .badge-sample {
        background-color: #fef3c7;
        color: #92400e;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

def setup_demo_environment():
    """Initializes the database and loads the 200 applicant demo dataset with initial allocation."""
    init_db(force=True)
    progs = generate_demo_programs()
    for p in progs:
        ProgramRepository.create(p)
    
    apps = generate_demo_applicants(count=200, seed=42)
    ApplicantRepository.bulk_create(apps)

    AuditService.log(
        event_type="DEMO_DATA_INITIALIZED",
        outcome="SUCCESS",
        details={"programs_count": len(progs), "applicants_count": len(apps)}
    )

    # Solve initial baseline allocation immediately
    ver, val = AllocationService.generate_allocation(
        name="Baseline Cohort Allocation",
        policy="LEXICOGRAPHIC_PREFERENCE_FIRST",
        use_baseline_as_anchor=False,
        auto_commit=True
    )
    return ver, val

# Ensure DB schema is created on initial start
init_db(force=False)

# Check if database has data
programs = ProgramRepository.get_all()
applicants = ApplicantRepository.get_all()

# First-Run Setup Experience
if not programs and not applicants:
    st.markdown("""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 2.5rem; margin: 2rem auto; max-width: 800px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">⚖️</div>
            <h1 style="color: #0f172a; font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;">Welcome to FAIRSHIFT</h1>
            <p style="color: #2563eb; font-weight: 600; font-size: 1.05rem; margin-bottom: 1rem;">
                Fair Allocation, Reassignment, and Impact Analysis System
            </p>
            <p style="color: #475569; font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.5rem;">
                FAIRSHIFT is an auditable decision-support system that allocates limited training seats using mathematical constraint optimization (Google OR-Tools CP-SAT). It respects applicant eligibility, program capacities, and ranked preferences, while minimizing unnecessary reassignment disruptions.
            </p>
            <div style="background: #f1f5f9; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; text-align: left; font-size: 0.85rem; color: #334155;">
                <b>Included Sample Dataset:</b>
                <ul style="margin: 0.5rem 0 0 1.25rem;">
                    <li><b>200 Synthetic Applicants</b> with realistic STEM/clearance eligibility and ranked preferences</li>
                    <li><b>10 Training Programs</b> with individual prerequisites and seat capacities</li>
                    <li>Realistic first-choice competition, over-subscription, and withdrawal cases</li>
                </ul>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col_l, col_btn, col_r = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Load Sample Dataset & Initialize Engine", type="primary", use_container_width=True):
            with st.spinner("Populating database with 200 applicants, 10 programs, and solving baseline allocation..."):
                setup_demo_environment()
                st.success("Database initialized with sample data!")
                st.rerun()
    st.stop()

# Sidebar Navigation
with st.sidebar:
    st.markdown("""
        <div style="padding: 0.5rem 0 1rem 0;">
            <div style="font-size: 1.35rem; font-weight: 800; color: #0f172a; display: flex; align-items: center; gap: 0.5rem;">
                <span>⚖️</span> FAIRSHIFT
            </div>
            <div style="font-size: 0.75rem; color: #64748b; font-weight: 500; margin-top: 0.2rem;">
                Transparent Allocation Engine
            </div>
        </div>
    """, unsafe_allow_html=True)

    page_choice = st.radio(
        "Navigation",
        [
            "📊 Executive Dashboard",
            "👥 Applicant Management",
            "🏢 Program Management",
            "⚙️ Allocation Engine",
            "🧪 Reassignment Simulation",
            "⚖️ Counterfactual Appeals",
            "🛡️ Independent Validation",
            "📜 Audit Logs & History",
            "📈 Reports & Analytics"
        ],
        label_visibility="collapsed"
    )

    st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid #e2e8f0;'/>", unsafe_allow_html=True)
    
    # Environment Control
    st.markdown("<span class='badge-sample'>SAMPLE DATASET LOADED</span>", unsafe_allow_html=True)
    st.caption("200 applicants | 10 training cohorts")
    
    with st.expander("🛠️ Demo Database Management"):
        st.write("Reset database to clean baseline sample dataset.")
        if st.button("Reset to Clean Demo Data", type="secondary", use_container_width=True):
            with st.spinner("Resetting demo database..."):
                setup_demo_environment()
                st.success("Reset completed!")
                st.rerun()

    st.markdown("""
        <div style="margin-top: 2rem; font-size: 0.72rem; color: #94a3b8; line-height: 1.4;">
            FAIRSHIFT v1.0.0<br/>
            Google OR-Tools CP-SAT Solver<br/>
            Independent Rule Validator
        </div>
    """, unsafe_allow_html=True)

# Main Page Routing
if page_choice == "📊 Executive Dashboard":
    render_dashboard()
elif page_choice == "👥 Applicant Management":
    render_applicants()
elif page_choice == "🏢 Program Management":
    render_programs()
elif page_choice == "⚙️ Allocation Engine":
    render_allocation()
elif page_choice == "🧪 Reassignment Simulation":
    render_simulation()
elif page_choice == "⚖️ Counterfactual Appeals":
    render_appeals()
elif page_choice == "🛡️ Independent Validation":
    render_validation()
elif page_choice == "📜 Audit Logs & History":
    render_audit()
elif page_choice == "📈 Reports & Analytics":
    render_reports()
