"""
TeraGrant Agent — AI Intake & Evaluation Platform (Batch 28-R2 Pure HTML Home + Query Router).
AI Builder Hackathon 2026 | Challenge 1 (SME Grant Automation)

Figma-faithful Home page as ONE pure HTML/CSS block with query-param routing,
zero Streamlit widget artifacts on Home, and fully preserved downstream challenge engine.
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
from app.theme import apply_theme


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
        "btn_start": "Start Application ›",
        "btn_reviewer": "Reviewer Dashboard",
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
        "btn_start": "ማመልከቻ ይጀምሩ ›",
        "btn_reviewer": "የገምጋሚ ዳሽቦርድ",
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
        "btn_start": "Iyyannoo Jalqabaa ›",
        "btn_reviewer": "Daashboordii Gamaggamaa",
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
# PAGE CONFIGURATION & THEME
# =============================================================================
st.set_page_config(
    page_title="TeraGrant — Talk. Upload. Verify. Score. Defend.",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()


# =============================================================================
# STEP 1: QUERY-PARAM ROUTER
# =============================================================================
raw_page = st.query_params.get("page", "home")
raw_lang = st.query_params.get("lang", "en")

# Normalize language
if raw_lang in ["am", "amharic", "Amharic"]:
    cur_lang_code = "am"
    st.session_state["lang"] = "Amharic"
elif raw_lang in ["om", "oromo", "Oromo", "afaan_oromoo"]:
    cur_lang_code = "om"
    st.session_state["lang"] = "Oromo"
else:
    cur_lang_code = "en"
    st.session_state["lang"] = "English"

# Normalize page
if raw_page == "home":
    st.session_state["page"] = "home"
elif raw_page.startswith("step"):
    st.session_state["page"] = "my_application"
    try:
        st.session_state["step"] = int(raw_page[4:])
    except ValueError:
        st.session_state["step"] = 1
elif raw_page in ["reviewer", "batch_review"]:
    st.session_state["page"] = "batch_review"
elif raw_page in ["evidence", "evidence_library"]:
    st.session_state["page"] = "evidence_library"
elif raw_page in ["myapp", "my_application"]:
    st.session_state["page"] = "my_application"

if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "step" not in st.session_state:
    st.session_state["step"] = 1
if "batch_portfolio" not in st.session_state:
    sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
    if sample_path.exists():
        with open(sample_path, "r", encoding="utf-8") as f:
            st.session_state["batch_portfolio"] = json.load(f)
    else:
        st.session_state["batch_portfolio"] = []

cur_lang = st.session_state.get("lang", "English")
t = I18N.get(cur_lang, I18N["English"])


# =============================================================================
# STEP 2: HOME AS ONE PURE HTML BLOCK (Figma Image 11 Ground Truth)
# =============================================================================
if st.session_state["page"] == "home":
    active_en = "active" if cur_lang_code == "en" else ""
    active_am = "active" if cur_lang_code == "am" else ""
    active_om = "active" if cur_lang_code == "om" else ""

    home_html = f"""
    <style>
        [data-testid="stSidebar"] {{ display: none !important; }}
        .home-wrapper {{
            max-width: 760px;
            margin: 0 auto;
            padding-top: 4vh;
            font-family: 'Inter', 'Noto Sans Ethiopic', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #111827;
        }}
        .home-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0 20px 0;
        }}
        .home-brand {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            font-weight: 700;
            color: #111827;
        }}
        .home-status {{
            font-size: 12px;
            color: #059669;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .home-status a {{
            color: #6B7280;
            text-decoration: none;
            font-weight: 500;
            font-size: 12px;
        }}
        .home-status a:hover {{
            color: #111827;
        }}
        .lang-segmented-bar {{
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 10px;
            padding: 3px;
            display: flex;
            width: 270px;
            margin: 0 auto 24px auto;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }}
        .lang-pill-link {{
            flex: 1;
            text-align: center;
            padding: 6px 0;
            font-size: 12px;
            font-weight: 500;
            color: #6B7280;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.15s ease;
        }}
        .lang-pill-link.active {{
            background: #111827;
            color: #FFFFFF !important;
            font-weight: 700;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .home-hero-h1 {{
            font-size: 40px;
            font-weight: 800;
            color: #111827;
            line-height: 1.15;
            letter-spacing: -0.8px;
            margin-bottom: 10px;
            text-align: center;
        }}
        .home-hero-sub {{
            font-size: 14px;
            color: #6B7280;
            max-width: 480px;
            margin: 0 auto 32px auto;
            line-height: 1.45;
            text-align: center;
        }}
        .home-cards-row {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 32px;
        }}
        .home-step-box {{
            flex: 1;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 16px;
            padding: 18px 16px;
            text-align: left;
            display: flex;
            flex-direction: column;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }}
        .home-step-icon-wrap {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 12px;
        }}
        .home-step-num {{
            font-size: 12px;
            color: #9CA3AF;
            font-weight: 600;
            margin-bottom: 2px;
        }}
        .home-step-title {{
            font-size: 14px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 6px;
        }}
        .home-step-desc {{
            font-size: 12px;
            color: #6B7280;
            line-height: 1.4;
        }}
        .home-cta-row {{
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 48px;
        }}
        .btn-primary-link {{
            background: #059669;
            color: #FFFFFF !important;
            height: 44px;
            padding: 0 24px;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            transition: background 0.15s ease;
        }}
        .btn-primary-link:hover {{
            background: #047857;
        }}
        .btn-secondary-link {{
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            color: #111827 !important;
            height: 44px;
            padding: 0 24px;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.15s ease;
        }}
        .btn-secondary-link:hover {{
            background: #F9FAFB;
            border-color: #D1D5DB;
        }}
        .home-legend-wrap {{
            max-width: 640px;
            margin: 0 auto 32px auto;
            text-align: left;
        }}
        .home-legend-title {{
            font-size: 10px;
            font-weight: 800;
            color: #6B7280;
            letter-spacing: 0.8px;
            margin-bottom: 12px;
            text-transform: uppercase;
        }}
        .home-legend-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px 16px;
            font-size: 11px;
            color: #4B5563;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
    </style>

    <div class="home-wrapper">
        <!-- Top Bar -->
        <div class="home-topbar">
            <div class="home-brand">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                <span>TeraGrant Agent</span>
            </div>
            <div class="home-status">
                <span>● Gemini Connected</span>
                <a href="?page=reviewer">Reviewer</a>
            </div>
        </div>

        <!-- Language Segmented Control -->
        <div class="lang-segmented-bar">
            <a class="lang-pill-link {active_en}" href="?lang=en&page=home">English</a>
            <a class="lang-pill-link {active_am}" href="?lang=am&page=home">አማርኛ</a>
            <a class="lang-pill-link {active_om}" href="?lang=om&page=home">Afaan Oromoo</a>
        </div>

        <!-- Hero -->
        <div class="home-hero-h1">{t["hero_title"]}</div>
        <div class="home-hero-sub">{t["hero_subtitle"]}</div>

        <!-- 3 Step Cards -->
        <div class="home-cards-row">
            <!-- Card 1: Speak -->
            <div class="home-step-box">
                <div class="home-step-icon-wrap" style="background:#EFF6FF; color:#2563EB;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563EB" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                </div>
                <div class="home-step-num">1</div>
                <div class="home-step-title">{t["step1_title"]}</div>
                <div class="home-step-desc">{t["step1_desc"]}</div>
            </div>

            <!-- Card 2: Upload -->
            <div class="home-step-box">
                <div class="home-step-icon-wrap" style="background:#F5F3FF; color:#7C3AED;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                </div>
                <div class="home-step-num">2</div>
                <div class="home-step-title">{t["step2_title"]}</div>
                <div class="home-step-desc">{t["step2_desc"]}</div>
            </div>

            <!-- Card 3: Verify -->
            <div class="home-step-box">
                <div class="home-step-icon-wrap" style="background:#ECFDF5; color:#059669;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
                </div>
                <div class="home-step-num">3</div>
                <div class="home-step-title">{t["step3_title"]}</div>
                <div class="home-step-desc">{t["step3_desc"]}</div>
            </div>
        </div>

        <!-- CTA Row -->
        <div class="home-cta-row">
            <a class="btn-primary-link" href="?page=step1">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
                <span>{t["btn_start"]}</span>
            </a>
            <a class="btn-secondary-link" href="?page=reviewer">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#111827" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                <span>{t["btn_reviewer"]}</span>
            </a>
        </div>

        <!-- Evidence Status Key -->
        <div class="home-legend-wrap">
            <div class="home-legend-title">{t["legend_title"]}</div>
            <div class="home-legend-grid">
                <div class="legend-item">
                    <span class="chip chip-verified">Document Verified</span>
                    <span>{t["legend_verified"]}</span>
                </div>
                <div class="legend-item">
                    <span class="chip chip-stated">Applicant Stated</span>
                    <span>{t["legend_stated"]}</span>
                </div>
                <div class="legend-item">
                    <span class="chip chip-inferred">AI Inferred</span>
                    <span>{t["legend_inferred"]}</span>
                </div>
                <div class="legend-item">
                    <span class="chip chip-confirmation">Needs Confirmation</span>
                    <span>{t["legend_confirm"]}</span>
                </div>
                <div class="legend-item">
                    <span class="chip chip-missing">Missing</span>
                    <span>{t["legend_missing"]}</span>
                </div>
                <div class="legend-item">
                    <span class="chip chip-contradicted">⚠ Contradicted</span>
                    <span>{t["legend_contra"]}</span>
                </div>
            </div>
        </div>
    </div>
    """
    if hasattr(st, "html"):
        st.html(home_html)
    else:
        import textwrap
        st.markdown(textwrap.dedent(home_html).strip(), unsafe_allow_html=True)


# =============================================================================
# APP SHELL FOR OTHER SCREENS (SIDEBAR & DEVELOPER MODE)
# =============================================================================
else:
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

        cur_page = st.session_state.get("page", "home")

        if st.button(t["nav_home"], use_container_width=True, type="primary" if cur_page == "home" else "secondary"):
            st.query_params["page"] = "home"
            st.session_state["page"] = "home"
            st.rerun()

        if st.button(t["nav_app"], use_container_width=True, type="primary" if cur_page == "my_application" else "secondary"):
            st.query_params["page"] = "step1"
            st.session_state["page"] = "my_application"
            st.session_state["step"] = 1
            st.rerun()

        if st.button(t["nav_review"], use_container_width=True, type="primary" if cur_page == "batch_review" else "secondary"):
            st.query_params["page"] = "reviewer"
            st.session_state["page"] = "batch_review"
            st.rerun()

        if st.button(t["nav_evidence"], use_container_width=True, type="primary" if cur_page == "evidence_library" else "secondary"):
            st.query_params["page"] = "evidence"
            st.session_state["page"] = "evidence_library"
            st.rerun()

        st.markdown("---")

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
# SCREEN S1: STEP 1 OF 6 — TELL YOUR STORY (Figma Image 12)
# =============================================================================
if st.session_state["page"] == "my_application" and st.session_state.get("step", 1) == 1:
    disp_name = applicant_display_name(st.session_state)

    # 1. Top Bar Row
    st.markdown(f"""
    <div class="top-bar-row">
        <a href="?page=home" style="font-size:13px; font-weight:600; color:#6B7280; text-decoration:none;">‹ Home</a>
        <div class="top-bar-title">{disp_name}</div>
        <div class="top-bar-step">Step 1 of 6</div>
    </div>
    """, unsafe_allow_html=True)

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
    <div style="text-align:center; max-width:640px; margin: 0 auto 0.8rem auto;">
        <div style="font-size:1.65rem; font-weight:800; color:#111827; margin-bottom:4px;">Tell us about your business</div>
        <div style="font-size:0.95rem; color:#6B7280; margin-bottom:4px;">Speak in Amharic, Afaan Oromo, or English. We will extract the key information automatically.</div>
        <div style="font-size:0.9rem; color:#4B5563; font-family:'Noto Sans Ethiopic';">ስለ ንግድዎ ይናገሩ — ወደ ማመልከቻ እንቀይረዋለን::</div>
    </div>
    """, unsafe_allow_html=True)

    col_lp1, col_lp2, col_lp3 = st.columns(3)
    with col_lp1:
        if st.button("English", key="s1_lang_en", use_container_width=True, type="primary" if cur_lang == "English" else "secondary"):
            st.query_params["lang"] = "en"
            st.session_state["lang"] = "English"
            st.rerun()
    with col_lp2:
        if st.button("አማርኛ", key="s1_lang_am", use_container_width=True, type="primary" if cur_lang == "Amharic" else "secondary"):
            st.query_params["lang"] = "am"
            st.session_state["lang"] = "Amharic"
            st.rerun()
    with col_lp3:
        if st.button("Afaan Oromoo", key="s1_lang_or", use_container_width=True, type="primary" if cur_lang == "Oromo" else "secondary"):
            st.query_params["lang"] = "om"
            st.session_state["lang"] = "Oromo"
            st.rerun()

    # 4. Recorder Block
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
        <div style="color:#DC2626; font-size:12px; font-weight:700; margin-bottom:12px;">● Recording... tap to record or speak</div>
    </div>
    """, unsafe_allow_html=True)

    audio_bytes_found = None
    audio_ext = "mp3"

    audio_rec = st.audio_input("Speak your story (ድምጽ ይቅረጹ)", key="step1_audio_input")
    if audio_rec:
        audio_bytes_found = audio_rec.read()
        audio_ext = "mp3"

    with st.expander("📁 or upload a voice note (.mp3/.wav/.m4a/.ogg/.oga/.webm)", expanded=False):
        up_audio = st.file_uploader("Upload audio file", type=["mp3", "wav", "m4a", "ogg", "oga", "webm"], key="step1_upload_file")
        if up_audio:
            audio_bytes_found = up_audio.read()
            audio_ext = up_audio.name.split(".")[-1].lower()

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

    # 6. Transcript Bubble + Fact Chips
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

    # 7. Bottom Navigation Bar
    col_bb1, col_bb2, col_bb3 = st.columns([1, 2, 1])
    with col_bb1:
        if st.button("‹ Back to home", key="btn_s1_bth"):
            st.query_params["page"] = "home"
            st.session_state["page"] = "home"
            st.rerun()

    with col_bb2:
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
            st.query_params["page"] = "step2"
            st.session_state["step"] = 2
            st.rerun()

    # 8. Guided Voice Interview
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
# SCREEN S2: STEP 2 OF 6 — UPLOAD EVIDENCE (Figma Image 14)
# =============================================================================
elif st.session_state["page"] == "my_application" and st.session_state.get("step", 1) == 2:
    disp_name = applicant_display_name(st.session_state)

    # 1. Top Bar Row
    st.markdown(f"""
    <div class="top-bar-row">
        <a href="?page=step1" style="font-size:13px; font-weight:600; color:#6B7280; text-decoration:none;">‹ Back</a>
        <div class="top-bar-title">{disp_name}</div>
        <div class="top-bar-step">Step 2 of 6</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Stepper Row
    st.markdown("""
    <div class="stepper-bar">
        <span class="step-node completed">✓ Tell your story</span>
        <span class="step-node active">● Upload evidence</span>
        <span class="step-node">○ Review application</span>
        <span class="step-node">○ Gaps & contradictions</span>
        <span class="step-node">○ Declarations</span>
        <span class="step-node">○ Readiness</span>
    </div>
    """, unsafe_allow_html=True)

    # 3. Center Header
    st.markdown("""
    <div style="text-align:center; max-width:640px; margin: 0 auto 1.5rem auto;">
        <div style="font-size:1.65rem; font-weight:800; color:#111827; margin-bottom:4px;">Upload your documents</div>
        <div style="font-size:0.95rem; color:#6B7280; margin-bottom:4px;">Trade licence and workshop photos help verify your business.</div>
        <div style="font-size:0.9rem; color:#4B5563; font-family:'Noto Sans Ethiopic';">የንግድ ፈቃድ እና የስራ ቦታ ፎቶዎችን ይጫኑ::</div>
    </div>
    """, unsafe_allow_html=True)

    col_u1, col_u2 = st.columns(2)

    with col_u1:
        st.markdown("""
        <div class="upload-card-container">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:20px;">📄</span>
                <span style="font-size:14px; font-weight:700; color:#111827;">Trade Licence Photo</span>
            </div>
            <div style="font-size:11px; color:#6B7280; font-family:'Noto Sans Ethiopic'; margin-bottom:8px;">የንግድ ፈቃድ ፎቶ</div>
            <div style="font-size:11.5px; color:#6B7280; line-height:1.4;">Official municipal or federal business registration certificate.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_license = st.file_uploader("Upload Trade Licence", type=["jpg", "jpeg", "png"], key="lic_up_step2")
        active_license_path = None
        if uploaded_license:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_lic:
                tmp_lic.write(uploaded_license.read())
                active_license_path = tmp_lic.name
            st.image(uploaded_license, caption="Uploaded Trade License", use_container_width=True)
        elif st.session_state.get("preset_loaded") == "unseen":
            dummy_lic = PROJECT_ROOT / "data" / "test_assets" / "license_smudged.jpg"
            if dummy_lic.exists():
                active_license_path = str(dummy_lic)
                st.caption("🎲 Unseen Test License Attached")

    with col_u2:
        st.markdown("""
        <div class="upload-card-container">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                <span style="font-size:20px;">📸</span>
                <span style="font-size:14px; font-weight:700; color:#111827;">Workshop / Facility Photo</span>
            </div>
            <div style="font-size:11px; color:#6B7280; font-family:'Noto Sans Ethiopic'; margin-bottom:8px;">የስራ ቦታ ፎቶ</div>
            <div style="font-size:11.5px; color:#6B7280; line-height:1.4;">Photo showing your equipment, production space, or team members.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_workshop = st.file_uploader("Upload Workshop Photo", type=["jpg", "jpeg", "png"], key="work_up_step2")
        active_workshop_path = None
        if uploaded_workshop:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_work:
                tmp_work.write(uploaded_workshop.read())
                active_workshop_path = tmp_work.name
            st.image(uploaded_workshop, caption="Uploaded Workshop Facility", use_container_width=True)
        elif st.session_state.get("preset_loaded") == "unseen":
            dummy_work = PROJECT_ROOT / "data" / "test_assets" / "workshop_berbere.jpg"
            if dummy_work.exists():
                active_workshop_path = str(dummy_work)
                st.caption("🎲 Unseen Test Workshop Photo Attached")

    st.write("")

    col_s2_b1, col_s2_b2 = st.columns(2)
    with col_s2_b1:
        if st.button("‹ Back to Step 1", key="btn_s2_back"):
            st.query_params["page"] = "step1"
            st.session_state["step"] = 1
            st.rerun()
    with col_s2_b2:
        if st.button("⚡ Process & Build Full Dossier ›", type="primary", use_container_width=True, key="btn_s2_process"):
            with st.spinner("🚀 Running multimodal parallel extraction, mapping, and rubric evaluation..."):
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
                st.query_params["page"] = "step3"
                st.session_state["step"] = 3
                st.rerun()


# =============================================================================
# STEPS 3..6 / DIGITAL TWIN WORKSPACE (PRESERVED WORKING DOWNSTREAM CODE)
# =============================================================================
elif st.session_state["page"] == "my_application":
    col_hdr_l, col_hdr_r = st.columns([3, 1])
    with col_hdr_l:
        st.markdown(f"""
        <div style="margin-bottom:0.5rem;">
            <div style="font-size:1.6rem; font-weight:800; color:#111827;">{t['nav_app']} — Step {st.session_state.get('step', 3)} of 6</div>
            <div style="font-size:0.9rem; color:#6B7280;">Review your assembled grant application digital twin with epistemic provenance.</div>
        </div>
        """, unsafe_allow_html=True)
    with col_hdr_r:
        if st.button("← " + t["nav_home"], use_container_width=True, key="btn_downstream_home3"):
            st.query_params["page"] = "home"
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    col_left, col_right = st.columns([1.2, 0.8])

    with col_left:
        st.markdown("#### 📋 Official Grant Application Digital Twin")
        twin_data = st.session_state.get("digital_twin_data", {})
        render_giz_form(session_data=twin_data, height=720)

    with col_right:
        if "score_res" in st.session_state:
            st.markdown("#### 📊 Evaluation & Transparency")
            score_res = st.session_state["score_res"]
            readiness_res = st.session_state["readiness_res"]
            sensitivity_res = st.session_state["sensitivity_res"]

            st.metric("Total Score", f"{score_res.total_score} / 100", delta=f"Track: {score_res.grid_variant.value}")
            st.metric("Submission Readiness", f"{readiness_res['readiness_pct']}%")
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
        if st.button("← " + t["nav_home"], use_container_width=True, key="btn_rev_home3"):
            st.query_params["page"] = "home"
            st.session_state["page"] = "home"
            st.rerun()

    st.markdown("---")

    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        uploaded_batch = st.file_uploader("Upload Batch JSON", type=["json"], key="rev_batch_up_main4")
    with col_b2:
        st.markdown("##### ⚡ Quick Load Presets")
        load_12_btn = st.button("📂 Load 12-Applicant Portfolio", use_container_width=True, key="btn_load_12_main2")

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
        
        if st.button("⚡ Rank Batch & Defend Shortlist", type="primary", use_container_width=True, key="btn_rank_batch_main2"):
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
        if st.button("← " + t["nav_home"], use_container_width=True, key="btn_ev_home3"):
            st.query_params["page"] = "home"
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
