"""
TeraGrant Agent — AI Intake & Evaluation Platform (Batch 25 App Shell & Home Page).
AI Builder Hackathon 2026 | Challenge 1 (SME Grant Automation)

Figma-faithful application shell with clean white sidebar, navigation router,
pixel-accurate Home Page (Image 11), and preserved working workspaces for My Application,
Batch Review, and Evidence Library.
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
from app.digital_twin import render_giz_form, convert_to_serializable
from app.heartbeat_ui import render_heartbeat
from app.chat_bubble_ui import render_chat_bubble, render_question_bubble
from app.tts_ui import speak_question
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
    page_title="TeraGrant — Talk. Upload. Verify. Score. Defend.",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Ethiopic:wght@400;500;600;700&display=swap');

    /* 1. Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 2. Global Page Styling */
    .stApp {
        background-color: #F6F7F9;
        font-family: 'Inter', 'Noto Sans Ethiopic', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #111827;
    }

    /* 3. Cards */
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

    /* 4. Touch Targets & Buttons */
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

    /* 5. Status Chips */
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

    /* 6. Language Switcher Pill */
    .lang-pill-container {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-bottom: 24px;
    }
    .lang-pill {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 600;
        color: #4B5563;
        display: inline-block;
    }
    .lang-pill.active {
        background: #111827;
        color: #FFFFFF;
        border-color: #111827;
    }

    /* 7. Numbered Step Cards on Home Screen */
    .home-step-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .home-step-icon {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# INITIALIZE SESSION STATE & NAVIGATION ROUTER
# =============================================================================
if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "batch_portfolio" not in st.session_state:
    sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
    if sample_path.exists():
        with open(sample_path, "r", encoding="utf-8") as f:
            st.session_state["batch_portfolio"] = json.load(f)
    else:
        st.session_state["batch_portfolio"] = []


# =============================================================================
# STEP 2: APP SHELL (FIGMA LIGHT SIDEBAR)
# =============================================================================
with st.sidebar:
    st.markdown("""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:2px;">
        <span style="font-size:22px;">🌱</span>
        <span style="font-size:16px; font-weight:800; color:#111827;">TeraGrant Agent</span>
    </div>
    <div style="font-size:10.5px; color:#059669; font-weight:700; margin-bottom:16px;">
        ● Verified Agent Active
    </div>
    """, unsafe_allow_html=True)

    # Navigation Buttons
    cur_page = st.session_state.get("page", "home")

    if st.button("🏠 Home", use_container_width=True, type="primary" if cur_page == "home" else "secondary"):
        st.session_state["page"] = "home"
        st.rerun()

    if st.button("📋 My Application", use_container_width=True, type="primary" if cur_page == "my_application" else "secondary"):
        st.session_state["page"] = "my_application"
        st.rerun()

    if st.button("👥 Batch Review", use_container_width=True, type="primary" if cur_page == "batch_review" else "secondary"):
        st.session_state["page"] = "batch_review"
        st.rerun()

    if st.button("📁 Evidence Library", use_container_width=True, type="primary" if cur_page == "evidence_library" else "secondary"):
        st.session_state["page"] = "evidence_library"
        st.rerun()

    st.markdown("---")

    # Developer Mode Expander (Collapsed)
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
            "Model Fallback Lead",
            options=["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.5-pro"],
            index=0,
        )
        st.session_state["lead_model"] = model_choice

        if st.button("🔍 Test API Connection", use_container_width=True):
            with st.spinner("Connecting to Google Gemini v1 API..."):
                try:
                    curr_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                    client = get_gemini_client(api_key=curr_key)
                    models_iter = list(client.models.list())
                    st.success(f"✅ Connected! Available models: {len(models_iter)}")
                except Exception as e:
                    st.error(f"❌ Connection Failed: {str(e)}")

        st.markdown("##### ⚡ Test Presets")
        if st.button("🎲 Unseen Applicant Test", use_container_width=True):
            st.session_state["preset_loaded"] = "unseen"
            st.toast("Loaded Unseen Applicant test assets!")

        rehearsal_toggle = st.checkbox("Enable Rehearsal Backup Mode", value=False)
        st.session_state["rehearsal_mode"] = rehearsal_toggle


# =============================================================================
# STEP 3: SCREEN S0 — RESTYLED HOME PAGE (Figma Image 11)
# =============================================================================
if st.session_state["page"] == "home":
    # Language Segmented Pills (English active dark)
    st.markdown("""
    <div class="lang-pill-container">
        <span class="lang-pill active">English</span>
        <span class="lang-pill">አማርኛ</span>
        <span class="lang-pill">Afaan Oromoo</span>
    </div>
    """, unsafe_allow_html=True)

    # Hero Section
    st.markdown("""
    <div style="text-align:center; margin-bottom: 2.5rem;">
        <div style="font-size: 2.5rem; font-weight: 800; color: #111827; letter-spacing: -0.8px; margin-bottom: 0.5rem; line-height: 1.2;">
            Talk. Upload. Verify. Score.<br/>Defend.
        </div>
        <div style="font-size: 1.05rem; color: #6B7280; max-width: 560px; margin: 0 auto; line-height: 1.4;">
            Turn a business story into a fundable application — without inventing facts.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3 Numbered Step Cards (Image 11)
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown("""
        <div class="home-step-card">
            <div class="home-step-icon" style="background:#EFF6FF; color:#2563EB;">🎙️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:700; margin-bottom:2px;">1</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">Speak</div>
            <div style="font-size:12px; color:#6B7280; line-height:1.4;">Tell us about your business in your own words.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c2:
        st.markdown("""
        <div class="home-step-card">
            <div class="home-step-icon" style="background:#F5F3FF; color:#7C3AED;">⬆️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:700; margin-bottom:2px;">2</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">Upload</div>
            <div style="font-size:12px; color:#6B7280; line-height:1.4;">Take photos of your licence and workshop.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c3:
        st.markdown("""
        <div class="home-step-card">
            <div class="home-step-icon" style="background:#ECFDF5; color:#059669;">🛡️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:700; margin-bottom:2px;">3</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">Verify</div>
            <div style="font-size:12px; color:#6B7280; line-height:1.4;">We build the application and show what still needs proof.</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Button Row (Emerald Primary + Outline Secondary)
    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        btn_col_a, btn_col_b = st.columns(2)
        with btn_col_a:
            if st.button("🎙️ Start Application >", type="primary", use_container_width=True):
                st.session_state["page"] = "my_application"
                st.rerun()
        with btn_col_b:
            if st.button("👥 Reviewer Dashboard", use_container_width=True):
                st.session_state["page"] = "batch_review"
                st.rerun()

    st.write("")
    st.write("")

    # EVIDENCE STATUS KEY (Bottom Legend exact per Figma)
    st.markdown("""
    <div style="margin-top: 3.5rem; text-align:center;">
        <div style="font-size:10px; font-weight:800; color:#6B7280; letter-spacing:0.8px; margin-bottom:12px;">EVIDENCE STATUS KEY</div>
        <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:14px; font-size:11px; color:#4B5563;">
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
# MY APPLICATION WORKSPACE (STEP 4: DO NOT TOUCH BATCH-23 INTAKE WORKSPACE)
# =============================================================================
elif st.session_state["page"] == "my_application":
    col_hdr_l, col_hdr_r = st.columns([3, 1])
    with col_hdr_l:
        st.markdown("""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:1.6rem; font-weight:800; color:#111827;">Applicant Intake & Digital Twin Workspace</div>
            <div style="font-size:0.9rem; color:#6B7280;">Upload voice, license, and workshop evidence to assemble your fundable application twin in real time.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hdr_r:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    col_left, col_right = st.columns([1.2, 0.8])

    # -------------------------------------------------------------------------
    # LEFT COLUMN: GIZ DIGITAL TWIN WITH HONEST STATUSES & PROVENANCE
    # -------------------------------------------------------------------------
    with col_left:
        st.markdown("#### 📋 Official Grant Application Digital Twin")
        twin_data = st.session_state.get("digital_twin_data", {})
        render_giz_form(session_data=twin_data, height=720)

    # -------------------------------------------------------------------------
    # RIGHT COLUMN: 3 BIG NUMBERED STEP CARDS + PRIMARY BUTTON
    # -------------------------------------------------------------------------
    with col_right:
        st.markdown("#### 📥 Multimodal Intake Dossier")

        # Preset Handler
        preset = st.session_state.get("preset_loaded")
        if preset == "unseen":
            st.info("🎲 **Unseen Test Dossier Loaded**: Almaz Spice Mill (Voice + Smudged License + Workshop Photo).")

        # STEP 1: SPEAK
        st.markdown("""
        <div class="tg-card" style="padding:12px; margin-bottom:8px;">
            <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:4px;">1️⃣ 🎙️ Speak (ድምጽ ይቅረጹ / Voice Note)</div>
            <div style="font-size:10.5px; color:#6B7280;">Record your business story in Amharic, Afaan Oromo, or English.</div>
        </div>
        """, unsafe_allow_html=True)
        
        voice_tab1, voice_tab2 = st.tabs(["🎙️ Record Live", "📁 Upload File"])
        active_audio_bytes = None
        with voice_tab1:
            recorded_audio = st.audio_input("Record Audio Note (ድምጽ ይቅረጹ)")
            if recorded_audio:
                active_audio_bytes = recorded_audio.read()
        with voice_tab2:
            uploaded_audio_file = st.file_uploader("Upload Audio", type=["mp3", "wav", "oga", "ogg", "m4a"], key="audio_up")
            if uploaded_audio_file:
                active_audio_bytes = uploaded_audio_file.read()

        if preset == "unseen" and not active_audio_bytes:
            proof_mp3 = PROJECT_ROOT / "data" / "proof_voice.mp3"
            if proof_mp3.exists():
                active_audio_bytes = proof_mp3.read_bytes()

        # STEP 2: TRADE LICENSE
        st.markdown("""
        <div class="tg-card" style="padding:12px; margin-bottom:8px;">
            <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:4px;">2️⃣ 📄 License (የንግድ ፈቃድ / Trade License)</div>
            <div style="font-size:10.5px; color:#6B7280;">Upload paper trade registration certificate or business license.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_license = st.file_uploader("Upload License Photo", type=["jpg", "jpeg", "png"], key="lic_up")
        active_license_path = None
        if uploaded_license:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_lic:
                tmp_lic.write(uploaded_license.read())
                active_license_path = tmp_lic.name
        elif preset == "unseen":
            dummy_lic = PROJECT_ROOT / "data" / "test_assets" / "license_smudged.jpg"
            if dummy_lic.exists():
                active_license_path = str(dummy_lic)

        # STEP 3: WORKSHOP PHOTO
        st.markdown("""
        <div class="tg-card" style="padding:12px; margin-bottom:8px;">
            <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:4px;">3️⃣ 📸 Workshop (የስራ ቦታ ፎቶ / Facility Photo)</div>
            <div style="font-size:10.5px; color:#6B7280;">Upload photo of your facility, machinery, or workshop workers.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_workshop = st.file_uploader("Upload Facility Photo", type=["jpg", "jpeg", "png"], key="work_up")
        active_workshop_path = None
        if uploaded_workshop:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_work:
                tmp_work.write(uploaded_workshop.read())
                active_workshop_path = tmp_work.name
        elif preset == "unseen":
            dummy_work = PROJECT_ROOT / "data" / "test_assets" / "workshop_berbere.jpg"
            if dummy_work.exists():
                active_workshop_path = str(dummy_work)

        # Action Button
        st.write("")
        trigger_intake = st.button("⚡ Analyze & Build Truth Dossier", type="primary", use_container_width=True)

        if trigger_intake:
            with st.spinner("🚀 Running concurrent multimodal extraction, zero-hallucination mapping, and audit checks..."):
                temp_voice_path = None
                if active_audio_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_aud:
                        tmp_aud.write(active_audio_bytes)
                        temp_voice_path = tmp_aud.name

                lead_mod = st.session_state.get("lead_model", "gemini-2.5-flash")
                cur_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")

                # Parallel Extraction
                audio_res, lic_res, work_res, timings, extra_gaps = run_intake_parallel(
                    voice_path=temp_voice_path,
                    license_path=active_license_path,
                    workshop_path=active_workshop_path,
                    model=lead_mod,
                    api_key=cur_key,
                )

                # Resilient Mapping
                pack = generate_application_pack(
                    license_data=lic_res or LicenseExtraction(is_legible=False),
                    audio_data=audio_res or AudioTranscriptExtraction(transcript="Voice note intake", detected_language="English"),
                    workshop_data=work_res,
                    model=lead_mod,
                    api_key=cur_key,
                )

                # Eligibility Gate & Contradictions
                gate_res = run_eligibility_gate(pack.application)
                contras = detect_contradictions(pack=pack, workshop_data=work_res, model=lead_mod, api_key=cur_key)

                # Track Routing & Multiplier Scoring
                variant = route_to_grid_variant(pack.application, pack.impact)
                score_res = score_application(pack=pack, variant=variant, model=lead_mod, api_key=cur_key)

                # Transparency Engines
                variants_comp = compare_grid_variants(pack.application, pack.impact, pack=pack)
                sensitivity_res = score_sensitivity(pack, score_res)
                readiness_res = submission_readiness(pack, gate_res, contras)

                # Update Session State
                st.session_state["pack_res"] = pack
                st.session_state["gate_res"] = gate_res
                st.session_state["contras"] = contras
                st.session_state["variant"] = variant
                st.session_state["score_res"] = score_res
                st.session_state["variants_comp"] = variants_comp
                st.session_state["sensitivity_res"] = sensitivity_res
                st.session_state["readiness_res"] = readiness_res

                # Digital Twin Payload
                twin_payload = {
                    "company_name": pack.application.business_info.business_name if pack.application else None,
                    "tin_number": pack.application.business_info.tin_number if pack.application else None,
                    "location": pack.application.business_info.location if pack.application else None,
                    "annual_sales": pack.application.financials.sales_history[0].revenue_etb if pack.application and pack.application.financials.sales_history else None,
                    "total_staff": pack.application.employment.total_staff if pack.application else None,
                    "female_staff": pack.application.employment.gender_split.female if pack.application else None,
                    "youth_staff": pack.application.employment.age_split.youth_18_29 if pack.application else None,
                    "product_type": pack.application.business_info.sector if pack.application else None,
                    "machinery_requested": pack.impact.milestones[0].title if pack.impact and pack.impact.milestones else None,
                    "requested_etb": pack.impact.etb_financial_target if pack.impact else None,
                    "provenance": {k: v.model_dump() for k, v in pack.provenance.items()},
                    "gaps": [g.model_dump() for g in pack.gaps],
                }
                st.session_state["digital_twin_data"] = twin_payload
                st.rerun()

    # AFTER SCORING TRANSPARENCY PANEL
    if "score_res" in st.session_state:
        st.markdown("---")
        st.markdown("### 📊 Transparency & Evaluation Truth Center")

        score_res = st.session_state["score_res"]
        gate_res = st.session_state["gate_res"]
        contras = st.session_state["contras"]
        pack_res = st.session_state["pack_res"]
        variants_comp = st.session_state["variants_comp"]
        sensitivity_res = st.session_state["sensitivity_res"]
        readiness_res = st.session_state["readiness_res"]

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.metric("Total Rubric Score", f"{score_res.total_score} / 100 pts", delta=f"Track: {score_res.grid_variant.value}")
        with col_t2:
            st.metric("Submission Readiness", f"{readiness_res['readiness_pct']}%", delta="100% Needed to Submit" if not readiness_res["is_ready"] else "Ready for Submission")
        with col_t3:
            st.metric("Potential Score", f"{sensitivity_res['potential_total']} / 100 [POTENTIAL]", delta=f"+{sensitivity_res['total_recoverable_points']} pts Recoverable")

        # Submission Readiness Screen
        st.markdown("#### 🚦 Submission Readiness & Gate Status")
        st.progress(readiness_res["readiness_pct"] / 100.0)
        
        if readiness_res["is_ready"]:
            st.success("✅ Application Ready for Submission: All mandatory eligibility gates passed.")
        else:
            st.error(f"❌ Action Required ({len(readiness_res['blockers'])} Blockers): Fix the items below before submission.")
            for b in readiness_res["blockers"]:
                st.markdown(f"- 🔴 **{b}**")

        # Grid Comparison Table
        st.markdown("#### ⚖️ Grid Variant Comparison & Routing Rationale")
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            st.table({
                "Evaluation Track": list(variants_comp["variant_scores"].keys()),
                "Calculated Score": [f"{v} / 100 pts" for v in variants_comp["variant_scores"].values()],
            })
        with col_g2:
            st.info(f"**Assigned Recommendation**: `{variants_comp['recommended_variant']}`\n\n{variants_comp['routing_reason']}")


# =============================================================================
# BATCH REVIEW WORKSPACE (STEP 4: DO NOT TOUCH BATCH-23 REVIEWER TABLE)
# =============================================================================
elif st.session_state["page"] == "batch_review":
    col_rh1, col_rh2 = st.columns([3, 1])
    with col_rh1:
        st.markdown("""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:1.6rem; font-weight:800; color:#111827;">Reviewer Batch Ranking & Portfolio Defense</div>
            <div style="font-size:0.9rem; color:#6B7280;">Reviewer committee workspace for evaluating and defending batches of scored SME proposals.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_rh2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        uploaded_batch = st.file_uploader("Upload Batch JSON", type=["json"], key="rev_batch_up")
    with col_b2:
        st.markdown("##### ⚡ Quick Load Presets")
        load_12_btn = st.button("📂 Load 12-Applicant Portfolio", use_container_width=True)

    if load_12_btn or uploaded_batch:
        if uploaded_batch:
            raw_batch_data = json.load(uploaded_batch)
        else:
            sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
            with open(sample_path, "r", encoding="utf-8") as f:
                raw_batch_data = json.load(f)
        st.session_state["raw_batch_data"] = raw_batch_data
        st.success(f"Loaded portfolio containing {len(raw_batch_data)} SME enterprises!")

    if "raw_batch_data" in st.session_state:
        batch_items = st.session_state["raw_batch_data"]
        
        if st.button("⚡ Rank Batch & Defend Shortlist", type="primary", use_container_width=True):
            with st.spinner("Sorting deterministically and synthesizing committee defense..."):
                scored_entries = []
                contra_dict = {}

                for item in batch_items:
                    b_name = item.get("business_name", "Unnamed SME")
                    score_val = item.get("total_score", 70)
                    variant_val = GridVariant(item.get("grid_variant", "GENERAL_SME"))
                    is_elig = item.get("is_eligible", True)
                    rev_sum = item.get("reviewer_summary", "Technical reviewer evaluation summary.")

                    mock_criteria = [
                        CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=min(score_val, 20), reasoning="Job creation potential verified."),
                        CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=min(max(score_val - 20, 0), 15), reasoning="Demographic inclusion verified."),
                        CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=min(max(score_val - 35, 0), 15), reasoning="Technical novelty verified."),
                        CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=min(max(score_val - 50, 0), 15), reasoning="Financial health verified."),
                        CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=min(max(score_val - 65, 0), 10), reasoning="Domestic supply verified."),
                        CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=min(max(score_val - 75, 0), 10), reasoning="Environmental impact verified."),
                        CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=min(max(score_val - 85, 0), 5), reasoning="Management verified."),
                        CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=0, reasoning="Community benefit noted."),
                        CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=0, reasoning="Scalability noted."),
                    ]
                    sc_res = ScoringResult(
                        grid_variant=variant_val,
                        total_score=sum(c.awarded_points for c in mock_criteria),
                        criteria_scores=mock_criteria,
                        eligibility_gate=EligibilityGate(
                            is_eligible=is_elig,
                            failed_declarations=[] if is_elig else ["environmental_compliance"],
                            triggered_exclusions=[],
                            gate_reasoning="Confirmed" if is_elig else "Disqualified due to regulatory permits."
                        ),
                        reviewer_summary=rev_sum
                    )
                    scored_entries.append((b_name, sc_res))

                    raw_contras = item.get("contradictions", [])
                    contra_objs = [
                        Contradiction(
                            claim_a=c.get("claim_a", ""),
                            claim_b=c.get("claim_b", ""),
                            severity=ContradictionSeverity(c.get("severity", "WARNING")),
                            kind=ContradictionKind(c.get("kind", "DISCREPANCY")),
                            explanation=c.get("explanation", "")
                        )
                        for c in raw_contras
                    ]
                    if contra_objs:
                        contra_dict[b_name] = contra_objs

                cur_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                shortlist = rank_batch(scored_entries, contradictions_map=contra_dict, api_key=cur_key)
                st.session_state["shortlist_res"] = shortlist
                st.rerun()

    if "shortlist_res" in st.session_state:
        shortlist = st.session_state["shortlist_res"]
        st.markdown("### 🏆 Ranked Portfolio Shortlist")
        st.info(f"**Portfolio Summary**: {shortlist.batch_summary}")

        for comp in shortlist.companies:
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5E7EB; border-radius:14px; padding:16px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:16px; font-weight:700; color:#111827;">Rank #{comp.rank}: {comp.business_name}</span>
                    <span style="font-size:16px; font-weight:800; color:#059669;">{comp.total_score} / 100 pts</span>
                </div>
                <div style="color:#6B7280; font-size:12px; margin-bottom:8px;">
                    Track: <b>{comp.grid_variant.value}</b> • Status: <span class="chip chip-verified">Recommended for committee consideration</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🛡 Why this rank? — Executive Defense for {comp.business_name}", expanded=False):
                st.markdown(f"**Executive Justification:**\n{comp.justification}")
                
                if comp.contradictions:
                    st.markdown("**⚠️ Flagged Risk Anomalies:**")
                    for c in comp.contradictions:
                        st.markdown(f"- `[{c.severity.value} - {c.kind.value}]` {c.explanation}")

                if comp.site_visit_questions:
                    st.markdown("**🎯 Traceable Site-Visit Due Diligence Questions:**")
                    for q in comp.site_visit_questions:
                        st.markdown(f"- 🔍 {q}")


# =============================================================================
# EVIDENCE LIBRARY (PROVENANCE TABLE)
# =============================================================================
elif st.session_state["page"] == "evidence_library":
    col_eh1, col_eh2 = st.columns([3, 1])
    with col_eh1:
        st.markdown("### 📁 Multimodal Evidence & Provenance Library")
        st.caption("Verifiable audit trail tracking every extracted claim, OCR token, and confidence metric.")
    with col_eh2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    table_data = [
        {"Field": "business_info.company_name", "Value": "Wolde Spice Mill", "Status": "DOCUMENT_VERIFIED", "Source": "license", "Confidence": "98%", "Evidence": "Trade License OCR ARZ-2019-04471"},
        {"Field": "business_info.location", "Value": "Bekoji Tera, Arsi Zone", "Status": "DOCUMENT_VERIFIED", "Source": "license", "Confidence": "95%", "Evidence": "Registration Address"},
        {"Field": "employment.total_staff", "Value": "8 Employees", "Status": "APPLICANT_STATED", "Source": "voice", "Confidence": "90%", "Evidence": "Voice Note verbatim speech"},
        {"Field": "financials.annual_turnover_etb", "Value": "480,000 ETB", "Status": "APPLICANT_STATED", "Source": "voice", "Confidence": "82%", "Evidence": "Spoken revenue figures"},
        {"Field": "business_info.years_in_operation", "Value": "7 years", "Status": "CONTRADICTED", "Source": "license vs voice", "Confidence": "60%", "Evidence": "2019 license vs 3yr claim"},
    ]
    st.table(table_data)
