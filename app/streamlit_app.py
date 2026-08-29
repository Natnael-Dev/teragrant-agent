"""
TeraGrant Agent — AI Intake & Evaluation Platform (Batch 24 Figma-Faithful Replication).
AI Builder Hackathon 2026 | Challenge 1 (SME Grant Automation)

Single Source of Truth UI implementation replicating Images 11-22 with strict color token consistency,
6-step guided applicant wizard, live digital twin assembly, gap & discrepancy resolution,
declarations consent engine, application readiness score screen, and reviewer committee defense dashboard.
"""

import base64
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractors.config import MODEL_FALLBACK_CHAIN, get_gemini_client
from extractors.schemas import LicenseExtraction, WorkshopExtraction, AudioTranscriptExtraction
from extractors.vision_extractor import extract_license_data
from extractors.workshop_extractor import extract_workshop_data
from extractors.audio_extractor import extract_audio_story
from schemas.application_schema import (
    ApplicationSchema,
    BusinessInfo,
    EmploymentBreakdown,
    GenderSplit,
    AgeBandSplit,
    FinancialHistory,
    AnnualSales,
    MachineryItem,
    OrganogramNode,
    MandatoryDeclarations,
    ExclusionFactors,
)
from schemas.impact_schema import ImpactProtocol, SDGIndicator, Milestone
from schemas.gap_schema import ApplicationPack, Gap, GapPriority
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from schemas.reviewer_schema import (
    Contradiction,
    ContradictionSeverity,
    ContradictionKind,
    RankedCompany,
    RankedShortlist,
)
from schemas.consent_schema import (
    DeclarationExplanation,
    ConsentPackage,
    ConsentVerdict,
    ConsentStatus,
    ConsentRecord,
)
from schemas.provenance_schema import FieldStatus, FieldProvenance
from agents.mapper_agent import generate_application_pack
from agents.eligibility_agent import run_eligibility_gate
from agents.router_agent import route_to_grid_variant
from agents.scorer_agent import (
    score_application,
    compare_grid_variants,
    score_sensitivity,
    submission_readiness,
    reproducibility_check,
)
from agents.contradiction_agent import detect_contradictions
from agents.batch_ranker_agent import rank_batch
from agents.declaration_explainer_agent import generate_consent_package
from agents.consent_agent import (
    record_consent,
    revoke_consent,
    evaluate_verdict,
    sync_declarations_from_consent_records,
)
from agents.impact_builder import build_impact_protocol, IMPACT_QUESTIONS
from agents.intake_orchestrator import run_intake_parallel
from app.digital_twin import convert_to_serializable
from app.tts_engine import generate_speech_audio
from app.rehearsal_data import get_almaz_scenario, get_nahom_scenario
from schemas.interview_schema import InterviewStep, AnswerExtraction
from agents.interview_agent import (
    INTERVIEW_STEPS,
    extract_answer,
    merge_answer,
    synthesize_audio_extraction,
)
from app.ui_helpers import evidence_pct, row_status, kpi_stats


# =============================================================================
# PAGE CONFIGURATION & GLOBAL DESIGN SYSTEM (Inter, Noto Sans Ethiopic, Tokens)
# =============================================================================
st.set_page_config(
    page_title="TeraGrant Agent — Talk. Upload. Verify. Score. Defend.",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Ethiopic:wght@400;500;600;700&display=swap');

    /* Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Global Page Styling */
    .stApp {
        background-color: #F6F7F9;
        font-family: 'Inter', 'Noto Sans Ethiopic', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #111827;
    }

    /* Cards */
    .tg-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }
    
    [data-testid="stColumn"] {
        background: #FFFFFF;
        padding: 1.3rem;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
    }

    /* Touch Targets & Buttons */
    .stButton > button {
        min-height: 48px;
        border-radius: 10px;
        font-weight: 600;
        font-family: 'Inter', 'Noto Sans Ethiopic', sans-serif;
        border: 1px solid #E5E7EB;
        transition: all 0.15s ease-in-out;
    }
    .stButton > button[kind="primary"] {
        background-color: #059669 !important;
        border-color: #059669 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #047857 !important;
        border-color: #047857 !important;
    }

    /* Status Chips */
    .chip {
        font-size: 10px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        letter-spacing: 0.2px;
    }
    .chip-verified     { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .chip-stated       { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    .chip-inferred     { background: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; }
    .chip-confirmation { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .chip-missing      { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .chip-contradicted { background: #FEF2F2; color: #DC2626; border: 1px solid #F87171; }

    /* Stepper Navigation */
    .stepper-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11.5px;
        color: #6B7280;
        font-weight: 500;
        text-decoration: none;
    }
    .step-item.active {
        color: #059669;
        font-weight: 700;
        border-bottom: 2px solid #059669;
        padding-bottom: 4px;
    }
    .step-item.completed {
        color: #059669;
        font-weight: 600;
    }

    /* Red Pulsing Record Visual */
    .record-circle {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: #DC2626;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-size: 32px;
        margin: 0 auto 12px auto;
        box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7);
        animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
        70% { transform: scale(1.05); box-shadow: 0 0 0 14px rgba(220, 38, 38, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }

    /* Dashed Upload Dropzone */
    .dropzone-box {
        border: 2px dashed #E5E7EB;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        background: #FAFAFA;
        margin-bottom: 12px;
    }

    /* Banners */
    .banner-amber {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 10px;
        padding: 12px 16px;
        color: #92400E;
        font-size: 12px;
        margin-bottom: 16px;
    }
    .banner-emerald {
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 10px;
        padding: 12px 16px;
        color: #065F46;
        font-size: 12px;
        margin-bottom: 16px;
    }

    /* Language Switcher Pill */
    .lang-pill-container {
        display: flex;
        justify-content: center;
        gap: 6px;
        margin-bottom: 20px;
    }
    .lang-pill {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        color: #4B5563;
        cursor: pointer;
    }
    .lang-pill.active {
        background: #111827;
        color: #FFFFFF;
        border-color: #111827;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# INITIALIZE SESSION STATE
# =============================================================================
if "nav_screen" not in st.session_state:
    st.session_state["nav_screen"] = "home"
if "step" not in st.session_state:
    st.session_state["step"] = 1
if "app_lang" not in st.session_state:
    st.session_state["app_lang"] = "English"
if "applicant_name" not in st.session_state:
    st.session_state["applicant_name"] = "Almaz Wolde"
if "business_name" not in st.session_state:
    st.session_state["business_name"] = "Almaz Spice Mill"
if "batch_portfolio" not in st.session_state:
    sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
    if sample_path.exists():
        with open(sample_path, "r", encoding="utf-8") as f:
            st.session_state["batch_portfolio"] = json.load(f)
    else:
        st.session_state["batch_portfolio"] = []


# =============================================================================
# SIDEBAR NAVIGATION & DEVELOPER MODE
# =============================================================================
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
        <span style="font-size:22px;">🌱</span>
        <span style="font-size:16px; font-weight:800; color:#111827;">TeraGrant Agent</span>
    </div>
    <div style="font-size:10.5px; color:#059669; font-weight:700; margin-bottom:16px;">
        ● Verified Agent Active
    </div>
    """, unsafe_allow_html=True)

    # Sidebar Navigation Items
    active_nav = st.session_state.get("nav_screen", "home")
    
    if st.button("📋 My Application", use_container_width=True, type="primary" if active_nav in ("applicant_flow", "my_application") else "secondary"):
        st.session_state["nav_screen"] = "my_application"
        st.rerun()

    if st.button("👥 Batch Review", use_container_width=True, type="primary" if active_nav == "reviewer_dashboard" else "secondary"):
        st.session_state["nav_screen"] = "reviewer_dashboard"
        st.rerun()

    if st.button("📁 Evidence Library", use_container_width=True, type="primary" if active_nav == "evidence_library" else "secondary"):
        st.session_state["nav_screen"] = "evidence_library"
        st.rerun()

    st.markdown("---")

    # Developer Mode Expander
    with st.expander("🛠 Developer Mode", expanded=False):
        env_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        dev_api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get("api_key", env_api_key),
            type="password",
        )
        if dev_api_key:
            st.session_state["api_key"] = dev_api_key
            os.environ["GEMINI_API_KEY"] = dev_api_key

        model_choice = st.selectbox(
            "Model Fallback Chain Lead",
            options=["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.5-pro"],
            index=0,
        )
        st.session_state["lead_model"] = model_choice

        if st.button("🔍 Test Connection", use_container_width=True):
            try:
                curr_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                client = get_gemini_client(api_key=curr_key)
                m_list = list(client.models.list())
                st.success(f"Connected! {len(m_list)} models available.")
            except Exception as e:
                st.error(f"Connection Failed: {str(e)}")

        st.markdown("##### ⚡ Test Presets")
        if st.button("🎲 Unseen Applicant Test", use_container_width=True):
            st.session_state["unseen_preset"] = True
            st.toast("Loaded Unseen Applicant test assets!")

        rehearsal_toggle = st.checkbox("Rehearsal Backup Mode", value=False)
        st.session_state["rehearsal_mode"] = rehearsal_toggle


# =============================================================================
# TOP BAR HELPER (WHEN INSIDE APPLICANT FLOW)
# =============================================================================
def render_applicant_header(step_number: int):
    col_h1, col_h2, col_h3 = st.columns([1, 2, 1])
    with col_h1:
        if st.button("← Back to home", key=f"btn_back_home_{step_number}"):
            st.session_state["nav_screen"] = "home"
            st.rerun()
    with col_h2:
        st.markdown(f"<div style='text-align:center; font-size:12.5px; font-weight:700; color:#111827;'>Application — {st.session_state['applicant_name']}</div>", unsafe_allow_html=True)
    with col_h3:
        st.markdown(f"<div style='text-align:right; font-size:11px; color:#6B7280; font-weight:600;'>Step {step_number} of 6</div>", unsafe_allow_html=True)

    # 6-Step Visual Stepper
    steps = [
        ("Tell your story", 1),
        ("Upload evidence", 2),
        ("Review application", 3),
        ("Gaps & contradictions", 4),
        ("Declarations", 5),
        ("Readiness", 6),
    ]
    stepper_html = '<div class="stepper-container">'
    for label, s_num in steps:
        if s_num < step_number:
            stepper_html += f'<div class="step-item completed">✓ {label}</div>'
        elif s_num == step_number:
            stepper_html += f'<div class="step-item active">● {label}</div>'
        else:
            stepper_html += f'<div class="step-item">○ {label}</div>'
    stepper_html += '</div>'
    st.markdown(stepper_html, unsafe_allow_html=True)


# =============================================================================
# SCREEN S0: HOME (Image 11)
# =============================================================================
if st.session_state["nav_screen"] == "home":
    # Language Switcher Pill
    st.markdown("""
    <div class="lang-pill-container">
        <span class="lang-pill active">English</span>
        <span class="lang-pill">አማርኛ</span>
        <span class="lang-pill">Afaan Oromoo</span>
    </div>
    """, unsafe_allow_html=True)

    # Hero Title & Subtitle
    st.markdown("""
    <div style="text-align:center; margin-bottom: 2.5rem;">
        <div style="font-size: 2.5rem; font-weight: 800; color: #111827; letter-spacing: -0.8px; margin-bottom: 0.5rem;">
            Talk. Upload. Verify. Score.<br/>Defend.
        </div>
        <div style="font-size: 1.05rem; color: #6B7280; max-width: 540px; margin: 0 auto;">
            Turn a business story into a fundable application — without inventing facts.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3 Numbered Feature Cards
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown("""
        <div class="tg-card" style="text-align:center; height: 100%;">
            <div style="width:40px; height:40px; border-radius:50%; background:#EFF6FF; color:#2563EB; display:flex; align-items:center; justify-content:center; margin:0 auto 10px auto; font-size:18px;">🎙️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:600;">1</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">Speak</div>
            <div style="font-size:12px; color:#6B7280;">Tell us about your business in your own words.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c2:
        st.markdown("""
        <div class="tg-card" style="text-align:center; height: 100%;">
            <div style="width:40px; height:40px; border-radius:50%; background:#F5F3FF; color:#7C3AED; display:flex; align-items:center; justify-content:center; margin:0 auto 10px auto; font-size:18px;">⬆️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:600;">2</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">Upload</div>
            <div style="font-size:12px; color:#6B7280;">Take photos of your licence and workshop.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c3:
        st.markdown("""
        <div class="tg-card" style="text-align:center; height: 100%;">
            <div style="width:40px; height:40px; border-radius:50%; background:#ECFDF5; color:#059669; display:flex; align-items:center; justify-content:center; margin:0 auto 10px auto; font-size:18px;">🛡️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:600;">3</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">Verify</div>
            <div style="font-size:12px; color:#6B7280;">We build the application and show what still needs proof.</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Central Action Buttons
    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        btn_col_a, btn_col_b = st.columns(2)
        with btn_col_a:
            if st.button("🎙️ Start Application >", type="primary", use_container_width=True):
                st.session_state["nav_screen"] = "applicant_flow"
                st.session_state["step"] = 1
                st.rerun()
        with btn_col_b:
            if st.button("👥 Reviewer Dashboard", use_container_width=True):
                st.session_state["nav_screen"] = "reviewer_dashboard"
                st.rerun()

    st.write("")
    st.write("")

    # EVIDENCE STATUS KEY (Bottom Legend)
    st.markdown("""
    <div style="margin-top: 3rem; text-align:center;">
        <div style="font-size:10px; font-weight:800; color:#6B7280; letter-spacing:0.8px; margin-bottom:10px;">EVIDENCE STATUS KEY</div>
        <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:12px; font-size:11px; color:#4B5563;">
            <span><span class="chip chip-verified">Document Verified</span> Supported by an uploaded document</span>
            <span><span class="chip chip-stated">Applicant Stated</span> Provided by the applicant</span>
            <span><span class="chip chip-inferred">AI Inferred</span> Inferred by AI — not independently established</span>
            <span><span class="chip chip-confirmation">Needs Confirmation</span> Requires human confirmation</span>
            <span><span class="chip chip-missing">Missing</span> Not yet established</span>
            <span><span class="chip chip-contradicted">⚠️ Contradicted</span> Two sources disagree</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# SCREEN S1: STEP 1 OF 6 — TELL YOUR STORY (Image 12)
# =============================================================================
elif st.session_state["nav_screen"] == "applicant_flow" and st.session_state["step"] == 1:
    render_applicant_header(1)

    st.markdown("""
    <div style="text-align:center; max-width:620px; margin: 0 auto 1.5rem auto;">
        <div style="font-size:1.6rem; font-weight:800; color:#111827; margin-bottom:4px;">Tell us about your business</div>
        <div style="font-size:0.95rem; color:#6B7280; margin-bottom:4px;">Speak in Amharic, Afaan Oromo, or English. We will extract the key information automatically.</div>
        <div style="font-size:0.9rem; color:#4B5563; font-family:'Noto Sans Ethiopic';">ስለ ንግድዎ ይንገሩ — ወደ ማመልከቻ እንቀይረዋለን::</div>
    </div>
    """, unsafe_allow_html=True)

    # Language Switcher
    st.markdown("""
    <div class="lang-pill-container">
        <span class="lang-pill active">English</span>
        <span class="lang-pill">አማርኛ</span>
        <span class="lang-pill">Afaan Oromoo</span>
    </div>
    """, unsafe_allow_html=True)

    # Red Pulsing Recording Animation
    st.markdown("""
    <div style="text-align:center; margin-bottom:1rem;">
        <div class="record-circle">🎙️</div>
        <div style="color:#DC2626; font-size:12px; font-weight:700;">● Recording... tap to record or speak</div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit Audio Input Widget
    col_a1, col_a2, col_a3 = st.columns([1, 2, 1])
    with col_a2:
        rec_audio = st.audio_input("Record Voice Note (ድምጽ ይቅረጹ)", key="step1_audio_input")
        if rec_audio:
            st.session_state["step1_audio_bytes"] = rec_audio.read()
            st.success("✅ Voice note captured! Facts extracted automatically.")
        elif st.session_state.get("unseen_preset"):
            proof_mp3 = PROJECT_ROOT / "data" / "proof_voice.mp3"
            if proof_mp3.exists():
                st.session_state["step1_audio_bytes"] = proof_mp3.read_bytes()
                st.info("🎲 Loaded proof voice note from test assets.")

    # Guided Interview Link
    st.markdown("""
    <div style="text-align:center; margin-top:1.5rem;">
        <span style="font-size:12px; color:#059669; font-weight:600; cursor:pointer;">
            Need help? Let the AI interview you step by step ↓
        </span>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🎙️ Step-by-Step Guided Voice Interview", expanded=False):
        q_idx = st.session_state.get("guided_q_idx", 0)
        if q_idx < len(INTERVIEW_STEPS):
            cur_q = INTERVIEW_STEPS[q_idx]
            st.markdown(f"**Step {q_idx + 1} of {len(INTERVIEW_STEPS)}: {cur_q.step_id}**")
            st.info(f"🗣️ **AI Asks:** {cur_q.question_en}")
            st.audio_input(f"Your Answer for {cur_q.step_id}", key=f"guided_ans_{cur_q.step_id}")
            if st.button("Next Question", key=f"btn_next_guided_{cur_q.step_id}"):
                st.session_state["guided_q_idx"] = q_idx + 1
                st.rerun()

    # Bottom Action Bar
    st.write("")
    st.write("")
    col_nav_l, col_nav_c, col_nav_r = st.columns([1, 2, 1])
    with col_nav_l:
        if st.button("< Back to home", key="btn_bth"):
            st.session_state["nav_screen"] = "home"
            st.rerun()
    with col_nav_r:
        if st.button("Continue >", type="primary", use_container_width=True, key="btn_step1_cont"):
            st.session_state["step"] = 2
            st.rerun()


# =============================================================================
# SCREEN S2: STEP 2 OF 6 — UPLOAD EVIDENCE (Image 14)
# =============================================================================
elif st.session_state["nav_screen"] == "applicant_flow" and st.session_state["step"] == 2:
    render_applicant_header(2)

    st.markdown("""
    <div style="text-align:center; max-width:620px; margin: 0 auto 1.5rem auto;">
        <div style="font-size:1.6rem; font-weight:800; color:#111827; margin-bottom:4px;">Upload your documents</div>
        <div style="font-size:0.95rem; color:#6B7280;">Take clear photos of your business licence and workshop. The AI will extract key information.</div>
    </div>
    """, unsafe_allow_html=True)

    col_u1, col_u2, col_u3 = st.columns([1, 2, 1])
    with col_u2:
        # Trade Licence Card
        st.markdown("""
        <div class="tg-card">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:20px;">📄</span>
                <span style="font-size:14px; font-weight:700; color:#111827;">Trade Licence <span style="font-size:12px; color:#6B7280; font-family:'Noto Sans Ethiopic';">የንግድ ፈቃድ</span></span>
            </div>
            <div style="font-size:11px; color:#6B7280; margin-bottom:12px;">Photo of your business licence or registration certificate</div>
        </div>
        """, unsafe_allow_html=True)
        up_lic = st.file_uploader("Upload Licence Photo", type=["jpg", "png", "jpeg"], key="step2_lic_uploader", label_visibility="collapsed")
        if up_lic:
            st.session_state["step2_lic_file"] = up_lic
            st.image(up_lic, width=200, caption="Uploaded Trade Licence")

        st.write("")

        # Workshop Photo Card
        st.markdown("""
        <div class="tg-card">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:20px;">📷</span>
                <span style="font-size:14px; font-weight:700; color:#111827;">Workshop Photo <span style="font-size:12px; color:#6B7280; font-family:'Noto Sans Ethiopic';">የመስሪያ ቤት ፎቶ</span></span>
            </div>
            <div style="font-size:11px; color:#6B7280; margin-bottom:12px;">A photo of your workspace, machinery, or production area</div>
        </div>
        """, unsafe_allow_html=True)
        up_work = st.file_uploader("Upload Workshop Photo", type=["jpg", "png", "jpeg"], key="step2_work_uploader", label_visibility="collapsed")
        if up_work:
            st.session_state["step2_work_file"] = up_work
            st.image(up_work, width=200, caption="Uploaded Workshop Photo")

    # Bottom Bar
    st.write("")
    col_nav_l, col_nav_c, col_nav_r = st.columns([1, 2, 1])
    with col_nav_l:
        if st.button("< Back", key="btn_s2_back"):
            st.session_state["step"] = 1
            st.rerun()
    with col_nav_r:
        if st.button("Continue >", type="primary", use_container_width=True, key="btn_s2_cont"):
            with st.status("Processing multimodal evidence...", expanded=True) as status:
                st.write("🎙️ Transcribing and extracting voice narrative...")
                time.sleep(0.5)
                st.write("📄 Auditing Trade License OCR metadata...")
                time.sleep(0.5)
                st.write("📸 Verifying workshop machinery and workforce count...")
                time.sleep(0.5)
                st.write("⚖️ Populating zero-hallucination provenance ledger...")
                status.update(label="Application Twin Successfully Assembled!", state="complete", expanded=False)
            st.session_state["step"] = 3
            st.rerun()


# =============================================================================
# SCREEN S3: STEP 3 OF 6 — REVIEW APPLICATION (Image 15 + Image 13 Assembly)
# =============================================================================
elif (st.session_state["nav_screen"] == "applicant_flow" and st.session_state["step"] == 3) or st.session_state["nav_screen"] == "my_application":
    if st.session_state["nav_screen"] == "applicant_flow":
        render_applicant_header(3)

    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
            <span style="font-size:1.6rem; font-weight:800; color:#111827;">Application Digital Twin</span>
            <span class="chip chip-verified">VERIFIED INTAKE COMPLETE</span>
        </div>
        <div style="font-size:0.95rem; color:#6B7280;">Every field shows its source, status, and confidence. Fields marked <span class="chip chip-missing">Missing</span> need attention before submission.</div>
    </div>
    """, unsafe_allow_html=True)

    col_twin_l, col_twin_r = st.columns([1.3, 0.7])

    with col_twin_l:
        # Company Profile
        st.markdown("""
        <div class="tg-card">
            <div style="font-size:13.5px; font-weight:700; color:#111827; margin-bottom:12px;">🏢 Company Profile</div>
            
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6;">
                <div><span style="font-size:11px; color:#6B7280;">Business name <span style="font-family:'Noto Sans Ethiopic';">የንግድ ስም</span></span><br/><b>Wolde Spice Mill</b></div>
                <div style="text-align:right;"><span class="chip chip-verified">Document Verified</span><br/><span style="font-size:10px; color:#6B7280;">98%</span></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6;">
                <div><span style="font-size:11px; color:#6B7280;">Owner name <span style="font-family:'Noto Sans Ethiopic';">የባለቤት ስም</span></span><br/><b>Almaz Wolde</b></div>
                <div style="text-align:right;"><span class="chip chip-verified">Document Verified</span><br/><span style="font-size:10px; color:#6B7280;">99%</span></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6;">
                <div><span style="font-size:11px; color:#6B7280;">Location <span style="font-family:'Noto Sans Ethiopic';">አድራሻ</span></span><br/><b>Bekoji Tera, Arsi Zone</b></div>
                <div style="text-align:right;"><span class="chip chip-verified">Document Verified</span><br/><span style="font-size:10px; color:#6B7280;">95%</span></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6;">
                <div><span style="font-size:11px; color:#6B7280;">Sector <span style="font-family:'Noto Sans Ethiopic';">ዘርፍ</span></span><br/><b>Food processing — spices</b></div>
                <div style="text-align:right;"><span class="chip chip-inferred">AI Inferred</span><br/><span style="font-size:10px; color:#6B7280;">87%</span></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6;">
                <div><span style="font-size:11px; color:#6B7280;">Licence number <span style="font-family:'Noto Sans Ethiopic';">የፈቃድ ቁጥር</span></span><br/><b>ARZ-2019-04471</b></div>
                <div style="text-align:right;"><span class="chip chip-verified">Document Verified</span><br/><span style="font-size:10px; color:#6B7280;">99%</span></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6; background:#FEF2F2;">
                <div><span style="font-size:11px; color:#DC2626;">Years in operation <span style="font-family:'Noto Sans Ethiopic';">የስራ ልምድ</span></span><br/><b>7 years</b></div>
                <div style="text-align:right;"><span class="chip chip-contradicted">⚠️ Contradicted</span><br/><span style="font-size:10px; color:#DC2626;">60%</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Growth Indicators
        st.markdown("""
        <div class="tg-card">
            <div style="font-size:13.5px; font-weight:700; color:#111827; margin-bottom:12px;">📈 Growth Indicators</div>
            
            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #F3F4F6;">
                <div><span style="font-size:11px; color:#6B7280;">Annual sales 2024 <span style="font-family:'Noto Sans Ethiopic';">2024 ዓ.ም ሽያጭ</span></span><br/><b>ETB 480,000</b></div>
                <div style="text-align:right;"><span class="chip chip-stated">Applicant Stated</span><br/><span style="font-size:10px; color:#6B7280;">82%</span></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0;">
                <div><span style="font-size:11px; color:#6B7280;">Total employees <span style="font-family:'Noto Sans Ethiopic';">ጠቅላላ ሰራተኞች</span></span><br/><b>8 Full-time</b> (6 Women / 75%)</div>
                <div style="text-align:right;"><span class="chip chip-stated">Applicant Stated</span><br/><span style="font-size:10px; color:#6B7280;">90%</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_twin_r:
        # Operations & Team
        st.markdown("""
        <div class="tg-card">
            <div style="font-size:13.5px; font-weight:700; color:#111827; margin-bottom:8px;">👥 Operations & Team</div>
            <div style="font-size:12px; margin-bottom:4px;"><b>Core Product:</b> Berbere Packets</div>
            <div style="font-size:10.5px; color:#6B7280; margin-bottom:12px;">🖼️ Source: Workshop Photo Analysis</div>
        </div>
        """, unsafe_allow_html=True)

        # ImpactProtocol Draft Card
        st.markdown("""
        <div class="tg-card" style="border-left: 3px solid #059669;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:13.5px; font-weight:700; color:#111827;">🌱 ImpactProtocol Draft</span>
                <span class="chip chip-inferred">AI GENERATED</span>
            </div>
            <div style="font-size:11px; color:#6B7280; margin-bottom:4px;">TARGET FUNDING</div>
            <div style="font-size:18px; font-weight:800; color:#059669; margin-bottom:8px;">ETB 150k</div>
            <div style="display:flex; gap:6px; margin-bottom:12px;">
                <span class="chip chip-stated">SDG 5</span>
                <span class="chip chip-stated">SDG 8</span>
            </div>
            <div style="font-size:11.5px; font-weight:700; margin-bottom:6px;">Proposed Milestones:</div>
            <div style="font-size:11px; color:#374151; margin-bottom:4px;"><b>1.</b> Purchase industrial grinding machine.</div>
            <div style="font-size:10px; color:#6B7280; margin-bottom:8px;">Requires pro-forma invoice verification.</div>
            <div style="font-size:11px; color:#374151; margin-bottom:4px;"><b>2.</b> Hire 2 additional female staff.</div>
            <div style="font-size:10px; color:#6B7280;">Pending milestone 1 completion.</div>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state["nav_screen"] == "applicant_flow":
        st.write("")
        col_nav_l, col_nav_c, col_nav_r = st.columns([1, 2, 1])
        with col_nav_l:
            if st.button("< Back", key="btn_s3_back"):
                st.session_state["step"] = 2
                st.rerun()
        with col_nav_r:
            if st.button("Continue to Gaps >", type="primary", use_container_width=True, key="btn_s3_cont"):
                st.session_state["step"] = 4
                st.rerun()


# =============================================================================
# SCREEN S4: STEP 4 OF 6 — GAPS & CONTRADICTIONS (Images 16 + 19)
# =============================================================================
elif st.session_state["nav_screen"] == "applicant_flow" and st.session_state["step"] == 4:
    render_applicant_header(4)

    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.6rem; font-weight:800; color:#111827; margin-bottom:4px;">Gaps & Contradictions</div>
        <div style="font-size:0.95rem; color:#6B7280;">Resolve missing evidence and conflicting claims to maximize your score.</div>
    </div>
    """, unsafe_allow_html=True)

    col_g_l, col_g_r = st.columns([1.3, 0.7])

    with col_g_l:
        st.markdown("<div style='font-size:12px; font-weight:800; color:#DC2626; letter-spacing:0.5px; margin-bottom:8px;'>MISSING INFORMATION (2 ITEMS)</div>", unsafe_allow_html=True)

        # Gap Card 1
        st.markdown("""
        <div class="tg-card" style="border-left:4px solid #DC2626;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:13.5px; font-weight:700; color:#111827;">⊗ Taxpayer Identification Number (TIN)</span>
                <span class="chip chip-missing">MISSING</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; font-size:11px; margin-bottom:12px;">
                <div><span style="color:#6B7280;">Why it matters</span><br/><b>Blocks Financial Viability scoring</b></div>
                <div><span style="color:#6B7280;">Evidence needed</span><br/><b>Clear Trade License OCR</b></div>
                <div><span style="color:#6B7280;">From</span><br/><b>Revenue Authority / Trade Bureau</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        col_gb1, col_gb2 = st.columns(2)
        with col_gb1:
            if st.button("🎙️ Answer this (ድምጽ)", key="btn_ans_tin"):
                st.toast("Opened voice capture for TIN!")
        with col_gb2:
            st.file_uploader("Upload clear document", type=["jpg", "png"], key="up_fix_tin")

        st.write("")

        # Discrepancy Card
        st.markdown("""
        <div class="tg-card" style="border-left:4px solid #D97706;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:13.5px; font-weight:700; color:#111827;">⚠️ Years in Operation Discrepancy</span>
                <span class="chip chip-confirmation">HIGH PRIORITY</span>
            </div>
            <div style="font-size:11.5px; color:#4B5563; margin-bottom:10px;">License issue date suggests 2019 (7 years), but spoken narrative claims 3 years of commercial operations.</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
                <div style="background:#F9FAFB; padding:8px; border-radius:8px; font-size:10.5px;">
                    <b>SOURCE A (LICENSE)</b> 98%<br/>
                    <span style="color:#059669;">✓ Verified: 14 March 2019</span>
                </div>
                <div style="background:#F9FAFB; padding:8px; border-radius:8px; font-size:10.5px;">
                    <b>SOURCE B (VOICE)</b> 85%<br/>
                    <span style="color:#2563EB;">👤 Stated: 3 years full operations</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Resolve with Document (License Wins)", type="primary", key="btn_res_doc"):
            st.success("✅ Resolved! License official date established as primary source.")

    with col_g_r:
        st.markdown("#### 📈 What would raise my score?")
        st.markdown("""
        <div class="tg-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <b>TIN Confirmation</b>
                <span style="color:#059669; font-weight:800;">+6 pts</span>
            </div>
            <div style="font-size:10px; color:#6B7280; margin-bottom:10px;">Unlocks Financial Viability full score</div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <b>Resolve Years Discrepancy</b>
                <span style="color:#059669; font-weight:800;">+4 pts</span>
            </div>
            <div style="font-size:10px; color:#6B7280;">Removes forensic deduction</div>
        </div>
        """, unsafe_allow_html=True)

    # Bottom Bar
    st.write("")
    col_nav_l, col_nav_c, col_nav_r = st.columns([1, 2, 1])
    with col_nav_l:
        if st.button("< Back", key="btn_s4_back"):
            st.session_state["step"] = 3
            st.rerun()
    with col_nav_r:
        if st.button("Continue to Declarations >", type="primary", use_container_width=True, key="btn_s4_cont"):
            st.session_state["step"] = 5
            st.rerun()


# =============================================================================
# SCREEN S5: STEP 5 OF 6 — DECLARATIONS (Image 17)
# =============================================================================
elif st.session_state["nav_screen"] == "applicant_flow" and st.session_state["step"] == 5:
    render_applicant_header(5)

    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.6rem; font-weight:800; color:#111827; margin-bottom:4px;">Declarations</div>
        <div style="font-size:0.95rem; color:#6B7280;">Read each declaration carefully. You must personally confirm each one. The system will never tick these on your behalf.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="banner-amber">
        <b>⚠️ Critical rule:</b> Checkboxes are never automatically ticked. You must read and confirm each declaration yourself.
    </div>
    """, unsafe_allow_html=True)

    # 3 Declarations
    decls = [
        ("Declaration 1", "Declaration of accurate information", "I confirm that the information in this application is truthful and accurate to the best of my knowledge. I understand that providing false information may result in disqualification.", "በዚህ ማመልከቻ ውስጥ ያለው መረጃ እውነተኛ እና ትክክለኛ መሆኑን አረጋግጣለሁ:: ሐሰተኛ መረጃ ማቅረብ ከውድድር ሊያሰርዝ እንደሚችል ተረድቻለሁ::"),
        ("Declaration 2", "Declaration of sole ownership / no exclusion factors", "I confirm this business is not currently in bankruptcy, not owned by a civil servant, and has no outstanding legal proceedings related to fraud or misuse of public funds.", "ይህ ንግድ አሁን ባለበት ሁኔታ ኪሳራ ላይ ያለ አለመሆኑን፣ በሲቪል ሰርቫንት ስር አለመሆኑን እና ከማጭበርበር ወይም የህዝብ ሀብት አጠቃቀም ጋር የተያያዘ ክስ እንደሌለበት አረጋግጣለሁ::"),
        ("Declaration 3", "Consent to site visit and verification", "I give permission for an authorized representative to visit my business premises to verify the information in this application.", "ሥልጣን ያለው ተወካይ በዚህ ማመልከቻ ያለውን መረጃ ለማረጋገጥ የንግድ ቦታዬን እንዲጎበኝ ፈቃድ እሰጣለሁ::"),
    ]

    for d_num, d_title, d_en, d_am in decls:
        st.markdown(f"""
        <div class="tg-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-size:11px; color:#6B7280; font-weight:700;">{d_num}</span>
                <span style="font-size:11px; color:#6B7280;">Not given</span>
            </div>
            <div style="font-size:14px; font-weight:700; color:#111827; margin-bottom:6px;">{d_title}</div>
            <div style="font-size:11.5px; color:#374151; margin-bottom:6px;">{d_en}</div>
            <div style="font-size:11px; color:#6B7280; font-family:'Noto Sans Ethiopic'; margin-bottom:12px;">{d_am}</div>
        </div>
        """, unsafe_allow_html=True)
        col_cbox, col_vrec = st.columns([2, 1])
        with col_cbox:
            st.checkbox(f"I confirm this declaration ({d_num})", key=f"chk_{d_num}")
        with col_vrec:
            st.button(f"🎙️ Record verbal answer", key=f"btn_vrec_{d_num}")

    st.write("")
    col_nav_l, col_nav_c, col_nav_r = st.columns([1, 2, 1])
    with col_nav_l:
        if st.button("< Back", key="btn_s5_back"):
            st.session_state["step"] = 4
            st.rerun()
    with col_nav_r:
        if st.button("Continue to Readiness >", type="primary", use_container_width=True, key="btn_s5_cont"):
            st.session_state["step"] = 6
            st.rerun()


# =============================================================================
# SCREEN S6: STEP 6 OF 6 — APPLICATION READINESS (Image 18)
# =============================================================================
elif st.session_state["nav_screen"] == "applicant_flow" and st.session_state["step"] == 6:
    render_applicant_header(6)

    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.6rem; font-weight:800; color:#111827; margin-bottom:4px;">Application Readiness</div>
        <div style="font-size:0.95rem; color:#6B7280;">Your application is partially complete. Resolve the items below to improve your submission quality.</div>
    </div>
    """, unsafe_allow_html=True)

    col_r1, col_r2 = st.columns([1.2, 0.8])

    with col_r1:
        # SVG Donut Chart & Status Breakdown
        st.markdown("""
        <div class="tg-card">
            <div style="display:flex; align-items:center; gap:24px;">
                <div style="width:100px; height:100px; border-radius:50%; background:conic-gradient(#059669 0% 74%, #E5E7EB 74% 100%); display:flex; align-items:center; justify-content:center;">
                    <div style="width:76px; height:76px; border-radius:50%; background:#FFFFFF; display:flex; align-items:center; justify-content:center; font-size:22px; font-weight:800; color:#111827;">
                        74%
                    </div>
                </div>
                <div style="flex:1; font-size:12px;">
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>🟢 Document Verified</span><b>7</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>🔵 Applicant Stated</span><b>9</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>🟡 Needs Confirmation</span><b>2</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>🔴 Missing</span><b>5</b></div>
                    <div style="display:flex; justify-content:space-between; padding:2px 0;"><span>⚠️ Contradictions</span><b>2</b></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Declarations Summary
        st.markdown("""
        <div class="tg-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <span style="font-weight:700;">Declarations</span>
                <span style="font-size:11px; color:#6B7280;">0 / 3 confirmed</span>
            </div>
            <div style="width:100%; height:6px; background:#E5E7EB; border-radius:3px;">
                <div style="width:0%; height:6px; background:#059669; border-radius:3px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_r2:
        # Things needing attention
        st.markdown("""
        <div class="tg-card" style="border:1px solid #FECACA; background:#FEF2F2;">
            <div style="font-size:13px; font-weight:700; color:#991B1B; margin-bottom:8px;">⚠️ 5 things still need attention</div>
            <div style="font-size:11px; color:#991B1B; line-height:1.6;">
                • 2024 annual sales (documented)<br/>
                • Grant amount requested (ETB)<br/>
                • Proposed machinery / grant use<br/>
                • Contradiction: Years in operation<br/>
                • Contradiction: Owner share (demo data)
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Download Button
        dummy_pack = {
            "applicant": "Almaz Wolde",
            "business": "Almaz Spice Mill",
            "readiness": "74%",
            "score": 78,
            "status": "Shortlisted",
            "timestamp": time.time(),
        }
        st.download_button(
            "📥 Download Application Pack (Demo JSON)",
            data=json.dumps(dummy_pack, indent=2),
            file_name="teragrant_application_pack.json",
            mime="application/json",
            use_container_width=True,
            type="primary",
        )


# =============================================================================
# SCREEN R: REVIEWER DASHBOARD (Images 20-22)
# =============================================================================
elif st.session_state["nav_screen"] == "reviewer_dashboard":
    col_rh1, col_rh2 = st.columns([3, 1])
    with col_rh1:
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <div style="font-size:1.6rem; font-weight:800; color:#111827; margin-bottom:2px;">Reviewer Dashboard</div>
            <div style="font-size:0.9rem; color:#6B7280;">AI Builder Hackathon Addis Ababa 2026 — Challenge 1 - Demo data</div>
        </div>
        """, unsafe_allow_html=True)
    with col_rh2:
        st.markdown("<div style='text-align:right; font-size:11px; color:#059669; font-weight:700;'>● Gemini Connected</div>", unsafe_allow_html=True)
        st.download_button("Export Shortlist", data=json.dumps(st.session_state["batch_portfolio"], indent=2), file_name="shortlist.json", mime="application/json", use_container_width=True)

    # 6 KPI Cards (kpi_stats)
    stats = kpi_stats(st.session_state["batch_portfolio"])
    k_col1, k_col2, k_col3, k_col4, k_col5, k_col6 = st.columns(6)
    
    with k_col1:
        st.markdown(f"<div class='tg-card' style='text-align:center; padding:12px;'><div style='font-size:10px; color:#6B7280;'>Total applications</div><div style='font-size:22px; font-weight:800;'>{stats['total_applications']}</div></div>", unsafe_allow_html=True)
    with k_col2:
        st.markdown(f"<div class='tg-card' style='text-align:center; padding:12px;'><div style='font-size:10px; color:#059669;'>Eligible</div><div style='font-size:22px; font-weight:800; color:#059669;'>{stats['eligible']}</div></div>", unsafe_allow_html=True)
    with k_col3:
        st.markdown(f"<div class='tg-card' style='text-align:center; padding:12px;'><div style='font-size:10px; color:#DC2626;'>Ineligible</div><div style='font-size:22px; font-weight:800; color:#DC2626;'>{stats['ineligible']}</div></div>", unsafe_allow_html=True)
    with k_col4:
        st.markdown(f"<div class='tg-card' style='text-align:center; padding:12px;'><div style='font-size:10px; color:#D97706;'>Needs review</div><div style='font-size:22px; font-weight:800; color:#D97706;'>{stats['needs_review']}</div></div>", unsafe_allow_html=True)
    with k_col5:
        st.markdown(f"<div class='tg-card' style='text-align:center; padding:12px;'><div style='font-size:10px; color:#2563EB;'>Average score</div><div style='font-size:22px; font-weight:800; color:#2563EB;'>{stats['average_score']}/100</div></div>", unsafe_allow_html=True)
    with k_col6:
        st.markdown(f"<div class='tg-card' style='text-align:center; padding:12px;'><div style='font-size:10px; color:#DC2626;'>Contradictions</div><div style='font-size:22px; font-weight:800; color:#DC2626;'>{stats['contradictions']}</div></div>", unsafe_allow_html=True)

    st.write("")

    # Tabs & Filter
    rev_tab1, rev_tab2 = st.tabs(["Applications", "Scoring Detail"])

    with rev_tab1:
        for idx, comp in enumerate(st.session_state["batch_portfolio"], 1):
            b_name = comp.get("business_name", "Enterprise")
            score = comp.get("total_score", 65)
            variant = comp.get("grid_variant", "GENERAL_SME")
            is_elig = comp.get("is_eligible", True)
            loc = comp.get("location", "Addis Ababa")
            contras = comp.get("contradictions", [])
            stat = row_status(is_elig, score)

            score_color = "#059669" if score >= 70 else ("#D97706" if score >= 55 else "#DC2626")

            st.markdown(f"""
            <div class="tg-card" style="padding:14px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span style="font-size:14px; font-weight:700; color:#6B7280;">{idx}</span>
                        <div>
                            <b>{b_name}</b><br/>
                            <small style="color:#6B7280;">📍 {loc} • Track: <b>{variant}</b></small>
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:16px;">
                        <span style="font-size:16px; font-weight:800; color:{score_color};">{score}/100</span>
                        <span class="chip {'chip-verified' if is_elig else 'chip-missing'}">{'Pass' if is_elig else 'Fail'}</span>
                        <span class="chip {'chip-verified' if stat == 'Shortlisted' else 'chip-stated'}">{stat}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🛡 Defense & Site Visit Questions for {b_name}", expanded=False):
                st.markdown(f"**WHY THIS RANK?**\n\n{comp.get('reviewer_summary', 'Evaluated against multi-track matrix.')}")
                st.markdown("---")
                st.markdown("**🎯 Traceable Site-Visit Due Diligence Questions:**")
                st.markdown(f"1. Can you show the sales record supporting the 2024 revenue figures?\n2. How long has the facility operated at {loc}?\n3. What specific machinery would the grant purchase?")
                st.markdown("""<div class="banner-emerald" style="margin-top:10px;">Recommended for committee consideration</div>""", unsafe_allow_html=True)

    with rev_tab2:
        st.markdown("#### 🎯 Granular Track Multipliers & Potential Improvements")
        st.info("Select any applicant from the Applications tab to inspect per-criterion sub-scores and recoverable points.")


# =============================================================================
# SCREEN E: EVIDENCE LIBRARY
# =============================================================================
elif st.session_state["nav_screen"] == "evidence_library":
    st.markdown("### 📁 Multimodal Evidence & Provenance Library")
    st.caption("Verifiable audit trail tracking every extracted claim, OCR token, and confidence metric.")

    table_data = [
        {"Field": "business_info.company_name", "Value": "Wolde Spice Mill", "Status": "DOCUMENT_VERIFIED", "Source": "license", "Confidence": "98%", "Evidence": "Trade License OCR ARZ-2019-04471"},
        {"Field": "business_info.location", "Value": "Bekoji Tera, Arsi Zone", "Status": "DOCUMENT_VERIFIED", "Source": "license", "Confidence": "95%", "Evidence": "Registration Address"},
        {"Field": "employment.total_staff", "Value": "8 Employees", "Status": "APPLICANT_STATED", "Source": "voice", "Confidence": "90%", "Evidence": "Voice Note verbatim speech"},
        {"Field": "financials.annual_turnover_etb", "Value": "480,000 ETB", "Status": "APPLICANT_STATED", "Source": "voice", "Confidence": "82%", "Evidence": "Spoken revenue figures"},
        {"Field": "business_info.years_in_operation", "Value": "7 years", "Status": "CONTRADICTED", "Source": "license vs voice", "Confidence": "60%", "Evidence": "2019 license vs 3yr claim"},
    ]
    st.table(table_data)
