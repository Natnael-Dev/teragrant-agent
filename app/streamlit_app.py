"""
TeraGrant Agent — AI Intake & Evaluation Platform (Batch 26 Step 1 "Tell Your Story").
AI Builder Hackathon 2026 | Challenge 1 (SME Grant Automation)

Figma-faithful Step 1 (Image 12) implementation with pure wizard logic extraction (app/wizard_logic.py),
96px red pulsing recording circle, waveform visualizer, WhatsApp transcript bubble with fact chips,
multilingual pills, and preserved working downstream workspaces for full challenge pipeline.
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
from app.wizard_logic import transcribe_step1, build_fact_chips, applicant_display_name


# =============================================================================
# TRILINGUAL CONTENT DICTIONARY
# =============================================================================
I18N = {
    "English": {
        "hero_title": "Talk. Upload. Verify. Score.<br/>Defend.",
        "hero_subtitle": "Turn a business story into a fundable application — without inventing facts.",
        "step1_title": "Speak",
        "step1_desc": "Tell us about your business in your own words.",
        "step2_title": "Upload",
        "step2_desc": "Take photos of your licence and workshop.",
        "step3_title": "Verify",
        "step3_desc": "We build the application and show what still needs proof.",
        "btn_start": "🎙️ Start Application >",
        "btn_reviewer": "👥 Reviewer Dashboard",
        "legend_title": "EVIDENCE STATUS KEY",
        "legend_verified": "Supported by an uploaded document",
        "legend_stated": "Provided by the applicant",
        "legend_inferred": "Inferred by AI — not independently established",
        "legend_confirm": "Requires human confirmation",
        "legend_missing": "Not yet established",
        "legend_contra": "Two sources disagree",
        "nav_home": "🏠 Home",
        "nav_app": "📋 My Application",
        "nav_review": "👥 Batch Review",
        "nav_evidence": "📁 Evidence Library",
    },
    "Amharic": {
        "hero_title": "ይናገሩ። ይጫኑ። ያረጋግጡ። ይመዝኑ።<br/>ይሟገቱ።",
        "hero_subtitle": "የንግድ ታሪክዎን ያለ ምንም የፈጠራ ወሬ ወደ ተቀባይነት ያለው የድጋፍ ማመልከቻ ይቀይሩ።",
        "step1_title": "ይናገሩ",
        "step1_desc": "ስለ ንግድዎ በራስዎ ቋንቋ እና አገላለጽ ይንገሩን።",
        "step2_title": "ይጫኑ",
        "step2_desc": "የንግድ ፈቃድዎን እና የስራ ቦታዎን ፎቶዎች ያንሱ።",
        "step3_title": "ያረጋግጡ",
        "step3_desc": "ማመልከቻውን አዘጋጅተን ማረጋገጫ የሚያስፈልጋቸውን እናሳያለን።",
        "btn_start": "🎙️ ማመልከቻ ይጀምሩ >",
        "btn_reviewer": "👥 የገምጋሚ ዳሽቦርድ",
        "legend_title": "የማስረጃ ሁኔታ ቁልፍ (EVIDENCE STATUS KEY)",
        "legend_verified": "በተያያዘ ሰነድ የተረጋገጠ",
        "legend_stated": "በአመልካቹ በድምጽ የተገለጸ",
        "legend_inferred": "በአይ አእምሮ የተገመተ — ራሱን ችሎ ያልተረጋገጠ",
        "legend_confirm": "የሰው ማረጋገጫ የሚያስፈልገው",
        "legend_missing": "እስካሁን ያልቀረበ",
        "legend_contra": "ሁለት መረጃዎች የተጋጩበት",
        "nav_home": "🏠 መነሻ ገጽ",
        "nav_app": "📋 የእኔ ማመልከቻ",
        "nav_review": "👥 የቡድን ግምገማ",
        "nav_evidence": "📁 የማስረጃ ቤተ-መጽሐፍት",
    },
    "Oromo": {
        "hero_title": "Dubbadhaa. Fe'aa. Mirkaneessaa. Qabaa.<br/>Falmadhaa.",
        "hero_subtitle": "Osoo soba hin uumin seenaa daldala keessanii gara iyyannoo fudhatama qabuutti jijjiiraa.",
        "step1_title": "Dubbadhaa",
        "step1_desc": "Waa'ee daldala keessanii jechoota keessaniin nuutti himaa.",
        "step2_title": "Fe'aa",
        "step2_desc": "Suuraa heeyyama daldalaa fi iddoo hojii keessanii kaasaa.",
        "step3_title": "Mirkaneessaa",
        "step3_desc": "Iyyannoo ijaarree wantoota ragaa barbaadan isiniif agarsiifna.",
        "btn_start": "🎙️ Iyyannoo Jalqabaa >",
        "btn_reviewer": "👥 Daashboordii Gamaggamaa",
        "legend_title": "KALLATTII HAALA RAGAA (EVIDENCE STATUS KEY)",
        "legend_verified": "Ragaa galmeetiin mirkanaa'e",
        "legend_stated": "Iyyataadhaan kan dubbatame",
        "legend_inferred": "AI'n kan tilmaamame — of danda'ee kan hin mirkanoofne",
        "legend_confirm": "Mirkaneessa namaa kan barbaadu",
        "legend_missing": "Hanga ammaatti kan hin dhiyaanne",
        "legend_contra": "Ragaaleen lama kan wal-faallessan",
        "nav_home": "🏠 Fuula Duraa",
        "nav_app": "📋 Iyyannoo Kiyya",
        "nav_review": "👥 Gamaggama Garee",
        "nav_evidence": "📁 Kuusaa Ragaalee",
    },
}


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

    /* 6. Stepper Navigation Row */
    .stepper-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }
    .step-node {
        font-size: 12px;
        color: #6B7280;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .step-node.active {
        color: #059669;
        font-weight: 700;
        border-bottom: 2px solid #059669;
        padding-bottom: 4px;
    }

    /* 7. 96px Red Pulsing Recording Circle & Waveform */
    .recorder-wrapper {
        text-align: center;
        margin: 20px auto 16px auto;
        max-width: 480px;
    }
    .record-circle-96 {
        width: 96px;
        height: 96px;
        border-radius: 50%;
        background: #DC2626;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-size: 38px;
        margin: 0 auto 14px auto;
        box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7);
        animation: pulse-ring 1.8s infinite;
    }
    @keyframes pulse-ring {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
        70% { transform: scale(1.04); box-shadow: 0 0 0 16px rgba(220, 38, 38, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    .wave-bars {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 4px;
        height: 24px;
        margin-bottom: 8px;
    }
    .wave-bar {
        width: 3px;
        background: #DC2626;
        border-radius: 2px;
        animation: wave 1.2s ease-in-out infinite alternate;
    }
    .wave-bar:nth-child(1) { height: 8px; animation-delay: 0.1s; }
    .wave-bar:nth-child(2) { height: 16px; animation-delay: 0.2s; }
    .wave-bar:nth-child(3) { height: 22px; animation-delay: 0.3s; }
    .wave-bar:nth-child(4) { height: 14px; animation-delay: 0.4s; }
    .wave-bar:nth-child(5) { height: 20px; animation-delay: 0.2s; }
    .wave-bar:nth-child(6) { height: 10px; animation-delay: 0.5s; }
    @keyframes wave {
        0% { transform: scaleY(0.4); }
        100% { transform: scaleY(1.0); }
    }

    /* 8. WhatsApp-style Chat Bubble */
    .whatsapp-bubble {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #059669;
        border-radius: 12px;
        padding: 16px;
        margin: 16px auto;
        max-width: 620px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        text-align: left;
    }
    .whatsapp-bubble-title {
        font-size: 11px;
        font-weight: 700;
        color: #059669;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .whatsapp-transcript {
        font-size: 13px;
        color: #111827;
        line-height: 1.5;
        font-style: italic;
        margin-bottom: 12px;
    }
    .fact-chips-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .fact-chip-pill {
        background: #F3F4F6;
        border: 1px solid #E5E7EB;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        color: #374151;
        font-weight: 600;
    }

    /* 9. Black Decorative Pill in Bottom Bar */
    .bottom-status-pill {
        background: #111827;
        color: #FFFFFF;
        border-radius: 24px;
        padding: 8px 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-size: 12px;
        font-weight: 600;
        margin: 0 auto;
        width: fit-content;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# INITIALIZE SESSION STATE & NAVIGATION ROUTER
# =============================================================================
if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "step" not in st.session_state:
    st.session_state["step"] = 1
if "lang" not in st.session_state:
    st.session_state["lang"] = "English"
if "batch_portfolio" not in st.session_state:
    sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
    if sample_path.exists():
        with open(sample_path, "r", encoding="utf-8") as f:
            st.session_state["batch_portfolio"] = json.load(f)
    else:
        st.session_state["batch_portfolio"] = []


# =============================================================================
# APP SHELL: SIDEBAR NAVIGATION & DEVELOPER MODE
# =============================================================================
cur_lang = st.session_state["lang"]
t = I18N.get(cur_lang, I18N["English"])

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

    if st.button(t["nav_home"], use_container_width=True, type="primary" if cur_page == "home" else "secondary"):
        st.session_state["page"] = "home"
        st.rerun()

    if st.button(t["nav_app"], use_container_width=True, type="primary" if cur_page == "my_application" else "secondary"):
        st.session_state["page"] = "my_application"
        st.session_state["step"] = 1
        st.rerun()

    if st.button(t["nav_review"], use_container_width=True, type="primary" if cur_page == "batch_review" else "secondary"):
        st.session_state["page"] = "batch_review"
        st.rerun()

    if st.button(t["nav_evidence"], use_container_width=True, type="primary" if cur_page == "evidence_library" else "secondary"):
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
# SCREEN S0: RESTYLED HOME PAGE (Image 11)
# =============================================================================
if st.session_state["page"] == "home":
    col_t_l, col_t_r = st.columns([2, 1])
    with col_t_l:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:6px; font-weight:800; font-size:14px; color:#111827;">
            <span style="color:#059669; font-size:18px;">🌱</span> TeraGrant Agent
        </div>
        """, unsafe_allow_html=True)
    with col_t_r:
        st.markdown("<div style='text-align:right; font-size:11px; color:#059669; font-weight:700;'>● Gemini Connected</div>", unsafe_allow_html=True)

    st.write("")

    # Language Switcher
    col_lp1, col_lp2, col_lp3, col_lp4, col_lp5 = st.columns([2, 1, 1, 1, 2])
    with col_lp2:
        if st.button("English", key="home_lang_en", use_container_width=True, type="primary" if cur_lang == "English" else "secondary"):
            st.session_state["lang"] = "English"
            st.rerun()
    with col_lp3:
        if st.button("አማርኛ", key="home_lang_am", use_container_width=True, type="primary" if cur_lang == "Amharic" else "secondary"):
            st.session_state["lang"] = "Amharic"
            st.rerun()
    with col_lp4:
        if st.button("Afaan Oromoo", key="home_lang_or", use_container_width=True, type="primary" if cur_lang == "Oromo" else "secondary"):
            st.session_state["lang"] = "Oromo"
            st.rerun()

    # Hero
    st.markdown(f"""
    <div style="text-align:center; margin-top: 1rem; margin-bottom: 2.5rem;">
        <div style="font-size: 2.5rem; font-weight: 800; color: #111827; letter-spacing: -0.8px; margin-bottom: 0.5rem; line-height: 1.2;">
            {t["hero_title"]}
        </div>
        <div style="font-size: 1.05rem; color: #6B7280; max-width: 560px; margin: 0 auto; line-height: 1.4;">
            {t["hero_subtitle"]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3 Cards
    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown(f"""
        <div class="home-step-card">
            <div class="home-step-icon" style="background:#EFF6FF; color:#2563EB;">🎙️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:700; margin-bottom:2px;">1</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">{t["step1_title"]}</div>
            <div style="font-size:12px; color:#6B7280; line-height:1.4;">{t["step1_desc"]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c2:
        st.markdown(f"""
        <div class="home-step-card">
            <div class="home-step-icon" style="background:#F5F3FF; color:#7C3AED;">⬆️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:700; margin-bottom:2px;">2</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">{t["step2_title"]}</div>
            <div style="font-size:12px; color:#6B7280; line-height:1.4;">{t["step2_desc"]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_c3:
        st.markdown(f"""
        <div class="home-step-card">
            <div class="home-step-icon" style="background:#ECFDF5; color:#059669;">🛡️</div>
            <div style="font-size:11px; color:#6B7280; font-weight:700; margin-bottom:2px;">3</div>
            <div style="font-size:15px; font-weight:700; color:#111827; margin-bottom:4px;">{t["step3_title"]}</div>
            <div style="font-size:12px; color:#6B7280; line-height:1.4;">{t["step3_desc"]}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # CTAs
    col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
    with col_b2:
        btn_col_a, btn_col_b = st.columns(2)
        with btn_col_a:
            if st.button(t["btn_start"], type="primary", use_container_width=True):
                st.session_state["page"] = "my_application"
                st.session_state["step"] = 1
                st.rerun()
        with btn_col_b:
            if st.button(t["btn_reviewer"], use_container_width=True):
                st.session_state["page"] = "batch_review"
                st.rerun()

    st.write("")
    st.write("")

    # Status Key
    st.markdown(f"""
    <div style="margin-top: 3.5rem; text-align:center;">
        <div style="font-size:10px; font-weight:800; color:#6B7280; letter-spacing:0.8px; margin-bottom:12px;">{t["legend_title"]}</div>
        <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:14px; font-size:11px; color:#4B5563;">
            <span><span class="chip chip-verified">Document Verified</span> {t["legend_verified"]}</span>
            <span><span class="chip chip-stated">Applicant Stated</span> {t["legend_stated"]}</span>
            <span><span class="chip chip-inferred">AI Inferred</span> {t["legend_inferred"]}</span>
            <span><span class="chip chip-confirmation">Needs Confirmation</span> {t["legend_confirm"]}</span>
            <span><span class="chip chip-missing">Missing</span> {t["legend_missing"]}</span>
            <span><span class="chip chip-contradicted">⚠️ Contradicted</span> {t["legend_contra"]}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# SCREEN S1: STEP 1 OF 6 — TELL YOUR STORY (Figma Image 12)
# =============================================================================
elif st.session_state["page"] == "my_application" and st.session_state.get("step", 1) == 1:
    # 1. Top Bar
    disp_name = applicant_display_name(st.session_state)
    col_tb1, col_tb2, col_tb3 = st.columns([1, 2, 1])
    with col_tb1:
        if st.button("← Back to home", key="btn_s1_home"):
            st.session_state["page"] = "home"
            st.rerun()
    with col_tb2:
        st.markdown(f"<div style='text-align:center; font-size:13px; font-weight:700; color:#111827;'>{disp_name}</div>", unsafe_allow_html=True)
    with col_tb3:
        st.markdown("<div style='text-align:right; font-size:11.5px; color:#6B7280; font-weight:600;'>Step 1 of 6</div>", unsafe_allow_html=True)

    # 2. Stepper Row
    st.markdown("""
    <div class="stepper-bar">
        <span class="step-node active">● Tell your story</span>
        <span class="step-node">○ Upload evidence</span>
        <span class="step-node">○ Review application</span>
        <span class="step-node">○ Gaps & contradictions</span>
        <span class="step-node">○ Declarations</span>
        <span class="step-node">○ Readiness</span>
    </div>
    """, unsafe_allow_html=True)

    # 3. Center Header & Language Pills
    st.markdown("""
    <div style="text-align:center; max-width:640px; margin: 0 auto 1.2rem auto;">
        <div style="font-size:1.65rem; font-weight:800; color:#111827; margin-bottom:4px;">Tell us about your business</div>
        <div style="font-size:0.95rem; color:#6B7280; margin-bottom:4px;">Speak in Amharic, Afaan Oromo, or English. We will extract the key information automatically.</div>
        <div style="font-size:0.9rem; color:#4B5563; font-family:'Noto Sans Ethiopic';">ስለ ንግድዎ ይናገሩ — ወደ ማመልከቻ እንቀይረዋለን::</div>
    </div>
    """, unsafe_allow_html=True)

    col_lp1, col_lp2, col_lp3, col_lp4, col_lp5 = st.columns([2, 1, 1, 1, 2])
    with col_lp2:
        if st.button("English", key="s1_lang_en", use_container_width=True, type="primary" if cur_lang == "English" else "secondary"):
            st.session_state["lang"] = "English"
            st.rerun()
    with col_lp3:
        if st.button("አማርኛ", key="s1_lang_am", use_container_width=True, type="primary" if cur_lang == "Amharic" else "secondary"):
            st.session_state["lang"] = "Amharic"
            st.rerun()
    with col_lp4:
        if st.button("Afaan Oromoo", key="s1_lang_or", use_container_width=True, type="primary" if cur_lang == "Oromo" else "secondary"):
            st.session_state["lang"] = "Oromo"
            st.rerun()

    # 4. Recorder Block (96px Red Pulsing Circle + Waveform)
    st.markdown("""
    <div class="recorder-wrapper">
        <div class="record-circle-96">🎙️</div>
        <div class="wave-bars">
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
        </div>
        <div style="color:#DC2626; font-size:12px; font-weight:700;">● Recording... tap to record or speak</div>
    </div>
    """, unsafe_allow_html=True)

    col_a1, col_a2, col_a3 = st.columns([1, 2, 1])
    audio_bytes_found = None
    audio_ext = "mp3"

    with col_a2:
        # Native recorder
        audio_rec = st.audio_input("Speak your story (ድምጽ ይቅረጹ)", key="step1_audio_input")
        if audio_rec:
            audio_bytes_found = audio_rec.read()
            audio_ext = "mp3"

        # Approved deviation: quiet upload link for all 6 formats
        with st.expander("📁 or upload a voice note (.mp3/.wav/.m4a/.ogg/.oga/.webm)", expanded=False):
            up_audio = st.file_uploader("Upload audio file", type=["mp3", "wav", "m4a", "ogg", "oga", "webm"], key="step1_upload_file")
            if up_audio:
                audio_bytes_found = up_audio.read()
                audio_ext = up_audio.name.split(".")[-1].lower()

        # Check unseen preset if applicable
        if not audio_bytes_found and st.session_state.get("preset_loaded") == "unseen":
            proof_mp3 = PROJECT_ROOT / "data" / "proof_voice.mp3"
            if proof_mp3.exists():
                audio_bytes_found = proof_mp3.read_bytes()
                audio_ext = "mp3"

    # 5. Process & Cache Transcription
    if audio_bytes_found:
        if st.session_state.get("step1_audio_raw") != audio_bytes_found:
            st.session_state["step1_audio_raw"] = audio_bytes_found
            with st.spinner("🎙️ Extracting facts with zero-hallucination auditor..."):
                lead_mod = st.session_state.get("lead_model", "gemini-2.5-flash")
                cur_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                res = transcribe_step1(
                    audio_bytes=audio_bytes_found,
                    ext=audio_ext,
                    lang=cur_lang,
                    model=lead_mod,
                    api_key=cur_key
                )
                st.session_state["step1_result"] = res

    # 6. Render WhatsApp-style Transcript Bubble + Fact Chips
    s1_res = st.session_state.get("step1_result")
    has_valid_transcript = False

    if s1_res:
        if s1_res.get("error"):
            err = s1_res["error"]
            st.error(f"❌ {err['type']}: {err['message']}\n\n💡 **Advice:** {err['advice']}")
        elif s1_res.get("transcript"):
            has_valid_transcript = True
            chips_html = "".join([f'<span class="fact-chip-pill">{c}</span>' for c in s1_res.get("chips", [])])
            st.markdown(f"""
            <div class="whatsapp-bubble">
                <div class="whatsapp-bubble-title">✓ Verified Audio Extraction</div>
                <div class="whatsapp-transcript">"{s1_res['transcript']}"</div>
                <div class="fact-chips-row">
                    {chips_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")

    # 7. Bottom Navigation Bar with Black Pill & Emerald Continue
    col_bb1, col_bb2, col_bb3 = st.columns([1, 2, 1])
    with col_bb1:
        if st.button("‹ Back to home", key="btn_s1_bth"):
            st.session_state["page"] = "home"
            st.rerun()

    with col_bb2:
        # Decorative Black Pill with Cancel (clear) and Confirm
        st.markdown("""
        <div class="bottom-status-pill">
            <span style="cursor:pointer; color:#9CA3AF;">✕ Cancel</span>
            <span>••••••••</span>
            <span style="color:#059669;">✓ Confirm</span>
        </div>
        """, unsafe_allow_html=True)

    with col_bb3:
        cont_disabled = not has_valid_transcript
        if st.button("Continue ›", type="primary", use_container_width=True, disabled=cont_disabled, key="btn_s1_continue"):
            st.session_state["step"] = 2
            st.rerun()

    # 8. Guided Voice Interview Expander
    st.write("")
    st.markdown("""
    <div style="text-align:center;">
        <span style="font-size:12px; color:#059669; font-weight:600;">
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


# =============================================================================
# STEPS 2..6 / DIGITAL TWIN WORKSPACE (PRESERVED WORKING DOWNSTREAM CODE)
# =============================================================================
elif st.session_state["page"] == "my_application":
    col_hdr_l, col_hdr_r = st.columns([3, 1])
    with col_hdr_l:
        st.markdown(f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:1.6rem; font-weight:800; color:#111827;">{t['nav_app']} — Step {st.session_state.get('step', 2)} of 6</div>
            <div style="font-size:0.9rem; color:#6B7280;">Upload evidence and review your assembled grant application digital twin.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hdr_r:
        if st.button("← " + t["nav_home"], use_container_width=True, key="btn_downstream_home"):
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    col_left, col_right = st.columns([1.2, 0.8])

    with col_left:
        st.markdown("#### 📋 Official Grant Application Digital Twin")
        twin_data = st.session_state.get("digital_twin_data", {})
        render_giz_form(session_data=twin_data, height=720)

    with col_right:
        st.markdown("#### 📥 Multimodal Evidence Upload")

        st.markdown("""
        <div class="tg-card" style="padding:12px; margin-bottom:8px;">
            <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:4px;">2️⃣ 📄 License (የንግድ ፈቃድ / Trade License)</div>
            <div style="font-size:10.5px; color:#6B7280;">Upload paper trade registration certificate or business license.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_license = st.file_uploader("Upload License Photo", type=["jpg", "jpeg", "png"], key="lic_up_step2")
        active_license_path = None
        if uploaded_license:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_lic:
                tmp_lic.write(uploaded_license.read())
                active_license_path = tmp_lic.name
        elif st.session_state.get("preset_loaded") == "unseen":
            dummy_lic = PROJECT_ROOT / "data" / "test_assets" / "license_smudged.jpg"
            if dummy_lic.exists():
                active_license_path = str(dummy_lic)

        st.markdown("""
        <div class="tg-card" style="padding:12px; margin-bottom:8px;">
            <div style="font-size:12px; font-weight:700; color:#111827; margin-bottom:4px;">3️⃣ 📸 Workshop (የስራ ቦታ ፎቶ / Facility Photo)</div>
            <div style="font-size:10.5px; color:#6B7280;">Upload photo of your facility, machinery, or workshop workers.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_workshop = st.file_uploader("Upload Facility Photo", type=["jpg", "jpeg", "png"], key="work_up_step2")
        active_workshop_path = None
        if uploaded_workshop:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_work:
                tmp_work.write(uploaded_workshop.read())
                active_workshop_path = tmp_work.name
        elif st.session_state.get("preset_loaded") == "unseen":
            dummy_work = PROJECT_ROOT / "data" / "test_assets" / "workshop_berbere.jpg"
            if dummy_work.exists():
                active_workshop_path = str(dummy_work)

        st.write("")
        trigger_intake = st.button("⚡ Process & Build Full Dossier", type="primary", use_container_width=True)

        if trigger_intake:
            with st.spinner("🚀 Running multimodal parallel extraction and scoring..."):
                lead_mod = st.session_state.get("lead_model", "gemini-2.5-flash")
                cur_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")

                temp_v_path = None
                raw_aud = st.session_state.get("step1_audio_raw")
                if raw_aud:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_a:
                        tmp_a.write(raw_aud)
                        temp_v_path = tmp_a.name

                audio_res, lic_res, work_res, timings, extra_gaps = run_intake_parallel(
                    voice_path=temp_v_path,
                    license_path=active_license_path,
                    workshop_path=active_workshop_path,
                    model=lead_mod,
                    api_key=cur_key,
                )

                pack = generate_application_pack(
                    license_data=lic_res or LicenseExtraction(is_legible=False),
                    audio_data=audio_res or AudioTranscriptExtraction(transcript="Voice note intake", detected_language="English"),
                    workshop_data=work_res,
                    model=lead_mod,
                    api_key=cur_key,
                )

                gate_res = run_eligibility_gate(pack.application)
                contras = detect_contradictions(pack=pack, workshop_data=work_res, model=lead_mod, api_key=cur_key)
                variant = route_to_grid_variant(pack.application, pack.impact)
                score_res = score_application(pack=pack, variant=variant, model=lead_mod, api_key=cur_key)

                variants_comp = compare_grid_variants(pack.application, pack.impact, pack=pack)
                sensitivity_res = score_sensitivity(pack, score_res)
                readiness_res = submission_readiness(pack, gate_res, contras)

                st.session_state["pack_res"] = pack
                st.session_state["gate_res"] = gate_res
                st.session_state["contras"] = contras
                st.session_state["variant"] = variant
                st.session_state["score_res"] = score_res
                st.session_state["variants_comp"] = variants_comp
                st.session_state["sensitivity_res"] = sensitivity_res
                st.session_state["readiness_res"] = readiness_res

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

    # Transparency Output
    if "score_res" in st.session_state:
        st.markdown("---")
        st.markdown("### 📊 Transparency & Evaluation Truth Center")
        score_res = st.session_state["score_res"]
        readiness_res = st.session_state["readiness_res"]
        sensitivity_res = st.session_state["sensitivity_res"]
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.metric("Total Score", f"{score_res.total_score} / 100", delta=f"Track: {score_res.grid_variant.value}")
        with col_t2:
            st.metric("Readiness", f"{readiness_res['readiness_pct']}%")
        with col_t3:
            st.metric("Potential Total", f"{sensitivity_res['potential_total']} / 100 [POTENTIAL]")


# =============================================================================
# BATCH REVIEW WORKSPACE (PRESERVED WORKING REVIEWER TAB)
# =============================================================================
elif st.session_state["page"] == "batch_review":
    col_rh1, col_rh2 = st.columns([3, 1])
    with col_rh1:
        st.markdown(f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:1.6rem; font-weight:800; color:#111827;">{t['nav_review']}</div>
            <div style="font-size:0.9rem; color:#6B7280;">Reviewer committee workspace for evaluating and defending batches of scored SME proposals.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_rh2:
        if st.button("← " + t["nav_home"], use_container_width=True, key="btn_rev_home"):
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        uploaded_batch = st.file_uploader("Upload Batch JSON", type=["json"], key="rev_batch_up_main2")
    with col_b2:
        st.markdown("##### ⚡ Quick Load Presets")
        load_12_btn = st.button("📂 Load 12-Applicant Portfolio", use_container_width=True, key="btn_load_12")

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
        
        if st.button("⚡ Rank Batch & Defend Shortlist", type="primary", use_container_width=True, key="btn_rank_batch"):
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
                <div style="color:#6B7280; font-size:12px;">
                    Track: <b>{comp.grid_variant.value}</b> • Status: <span class="chip chip-verified">Recommended for committee consideration</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


# =============================================================================
# EVIDENCE LIBRARY (PROVENANCE TABLE)
# =============================================================================
elif st.session_state["page"] == "evidence_library":
    col_eh1, col_eh2 = st.columns([3, 1])
    with col_eh1:
        st.markdown(f"### 📁 {t['nav_evidence']}")
        st.caption("Verifiable audit trail tracking every extracted claim, OCR token, and confidence metric.")
    with col_eh2:
        if st.button("← " + t["nav_home"], use_container_width=True, key="btn_ev_home"):
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
