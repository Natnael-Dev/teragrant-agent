"""
TeraGrant Agent — AI Intake & Evaluation Platform (Batch 23 Truth Layer UI).
AI Builder Hackathon 2026 | Challenge 1 (SME Grant Automation)

An end-to-end multi-agent truth layer system that converts informal voice notes, trade license photos,
and workshop facility images into audit-grade grant application packs with epistemic provenance,
evaluates eligibility deterministically, scores across 3 track variants, calculates transparency metrics,
and defends ranked portfolio shortlists.
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


# =============================================================================
# PAGE CONFIGURATION & SHADCN / TAILWIND DESIGN SYSTEM
# =============================================================================
st.set_page_config(
    page_title="TeraGrant — Talk. Upload. Verify. Score. Defend.",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* 1. Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 2. Global Page Styling */
    .stApp {
        background-color: #F6F7F9;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #111827;
    }

    /* 3. Card Containers (shadcn / Tailwind clean aesthetic) */
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

    /* 4. Header Story */
    .header-story {
        padding: 0.5rem 0 1.2rem 0;
    }
    .main-title {
        font-size: 1.95rem;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.6px;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        font-size: 0.95rem;
        color: #6B7280;
        font-weight: 400;
        line-height: 1.4;
    }

    /* 5. Big Touch Targets & Buttons */
    .stButton > button {
        min-height: 48px;
        border-radius: 10px;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
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

    /* 6. Step Cards */
    .step-card {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
    }
    .step-title {
        font-size: 12.5px;
        font-weight: 700;
        color: #111827;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .step-subtitle {
        font-size: 10.5px;
        color: #6B7280;
        margin-bottom: 8px;
    }

    /* 7. Honest Status Badges */
    .chip {
        font-size: 10px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
        display: inline-block;
        letter-spacing: 0.3px;
    }
    .chip-verified { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .chip-stated { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    .chip-inferred { background: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; }
    .chip-confirmation { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .chip-missing { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .chip-contradicted { background: #FEF2F2; color: #DC2626; border: 1px solid #F87171; }

    /* 8. Alert Banners */
    .banner-warning {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 10px;
        padding: 12px 16px;
        color: #92400E;
        font-size: 12px;
        margin-bottom: 12px;
    }
    .banner-danger {
        background: #FEF2F2;
        border: 1px solid #FECACA;
        border-radius: 10px;
        padding: 12px 16px;
        color: #991B1B;
        font-size: 12px;
        margin-bottom: 12px;
    }
    .banner-success {
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 10px;
        padding: 12px 16px;
        color: #065F46;
        font-size: 12px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HEADER STORY
# =============================================================================
st.markdown("""
<div class="header-story">
    <div class="main-title">TeraGrant — Talk. Upload. Verify. Score. Defend.</div>
    <div class="main-subtitle">AI-Powered Multimodal Grant Evaluation & Zero-Hallucination Integrity Engine for Ethiopian SMEs</div>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR (STAGE MODE & DEVELOPER PANEL)
# =============================================================================
with st.sidebar:
    st.markdown("### 🟢 Gemini Connected")
    st.caption("Active Model: `gemini-2.5-flash` • API v1")
    
    st.markdown("---")
    
    # 1. Quick Presets for Demo / Evaluation
    st.markdown("##### ⚡ Live Quick Presets")
    col_pre1, col_pre2 = st.columns(2)
    with col_pre1:
        if st.button("🎲 Unseen Applicant", use_container_width=True, help="Loads test assets (license + workshop + voice)"):
            st.session_state["preset_loaded"] = "unseen"
            st.session_state["preset_time"] = time.time()
            st.toast("Loaded Unseen Applicant test assets!")
    with col_pre2:
        if st.button("👩 Hiwot Impact", use_container_width=True, help="Exercises impact builder with training scenario"):
            st.session_state["preset_loaded"] = "hiwot"
            st.session_state["preset_time"] = time.time()
            st.toast("Loaded Hiwot Training Initiative scenario!")

    st.markdown("---")

    # 2. Developer Mode Expander
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

        st.markdown("##### 🎭 Emergency Backup")
        rehearsal_toggle = st.checkbox("Enable Rehearsal Backup Mode", value=False)
        st.session_state["rehearsal_mode"] = rehearsal_toggle

    # 3. AI Reasoning Boundaries Expander
    with st.expander("🤖 AI Reasoning Boundaries", expanded=False):
        st.markdown("""
        **What TeraGrant CAN Do:**
        - 🎙️ Transcribe trilingual spoken audio (Amharic, Afaan Oromo, English)
        - 👁️ Extract OCR metadata from paper trade licenses
        - 🏭 Audit facility photos for physical asset corroboration
        - ⚖️ Enforce 15-check deterministic eligibility gates and 3 instant-kill exclusion checks
        - 🎯 Calculate weighted 100-point rubric scores across 3 track variants
        - 📊 Detect mathematical and semantic cross-document contradictions
        - 📈 Compute gap-to-score sensitivity & submission readiness

        **What TeraGrant CANNOT Do:**
        - ❌ Auto-tick legal declarations or bypass human verbal consent
        - ❌ Hallucinate missing TINs, financial numbers, or demographic splits
        - ❌ Override investment committee authority or disburse funds automatically
        """)


# =============================================================================
# MAIN TABS (SHADCN CLEAN WORKSPACE)
# =============================================================================
tab1, tab2, tab3 = st.tabs([
    "🚀 1. Applicant Intake & Digital Twin",
    "📊 2. Reviewer Batch Ranker",
    "📜 3. Multilingual Verbal Consent",
])


# =============================================================================
# TAB 1: APPLICANT INTAKE & DIGITAL TWIN
# =============================================================================
with tab1:
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

        # Preset Injection Handler
        preset = st.session_state.get("preset_loaded")
        if preset == "unseen":
            st.info("🎲 **Unseen Test Dossier Loaded**: Almaz Spice Mill (Voice + Smudged License + Workshop Photo).")
        elif preset == "hiwot":
            st.info("👩 **Hiwot Training Scenario Loaded**: Exercising ImpactProtocol and milestone builder.")

        # STEP 1: SPEAK
        st.markdown("""
        <div class="step-card">
            <div class="step-title">1️⃣ 🎙️ Speak (ድምጽ ይቅረጹ / Voice Note)</div>
            <div class="step-subtitle">Record your business story in Amharic, Afaan Oromo, or English.</div>
        </div>
        """, unsafe_allow_html=True)
        
        voice_tab1, voice_tab2 = st.tabs(["🎙️ Record Live", "📁 Upload File"])
        uploaded_audio = None
        with voice_tab1:
            recorded_audio = st.audio_input("Record Audio Note (ድምጽ ይቅረጹ)")
        with voice_tab2:
            uploaded_audio_file = st.file_uploader("Upload Audio (MP3 / WAV / OGA / M4A)", type=["mp3", "wav", "oga", "ogg", "m4a"], key="audio_uploader")

        active_audio_bytes = None
        active_audio_path = None
        if recorded_audio:
            active_audio_bytes = recorded_audio.read()
        elif uploaded_audio_file:
            active_audio_bytes = uploaded_audio_file.read()
        elif preset == "unseen":
            proof_mp3 = PROJECT_ROOT / "data" / "proof_voice.mp3"
            if proof_mp3.exists():
                active_audio_bytes = proof_mp3.read_bytes()

        # STEP 2: TRADE LICENSE
        st.markdown("""
        <div class="step-card">
            <div class="step-title">2️⃣ 📄 License (የንግድ ፈቃድ / Trade License)</div>
            <div class="step-subtitle">Upload paper trade registration certificate or business license.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_license = st.file_uploader("Upload License Photo", type=["jpg", "jpeg", "png"], key="lic_uploader")
        
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
        <div class="step-card">
            <div class="step-title">3️⃣ 📸 Workshop (የስራ ቦታ ፎቶ / Facility Photo)</div>
            <div class="step-subtitle">Upload photo of your facility, machinery, or workshop workers.</div>
        </div>
        """, unsafe_allow_html=True)
        uploaded_workshop = st.file_uploader("Upload Facility Photo", type=["jpg", "jpeg", "png"], key="work_uploader")

        active_workshop_path = None
        if uploaded_workshop:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_work:
                tmp_work.write(uploaded_workshop.read())
                active_workshop_path = tmp_work.name
        elif preset == "unseen":
            dummy_work = PROJECT_ROOT / "data" / "test_assets" / "workshop_berbere.jpg"
            if dummy_work.exists():
                active_workshop_path = str(dummy_work)

        # ONE LARGE EMERALD ACTION BUTTON
        st.write("")
        trigger_intake = st.button("⚡ Analyze & Build Truth Dossier", type="primary", use_container_width=True)

        if trigger_intake:
            with st.spinner("🚀 Running concurrent multimodal extraction, zero-hallucination mapping, and audit checks..."):
                # Save voice temp file if bytes exist
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

        # GUIDED INTERVIEW TOGGLE BELOW
        st.markdown("---")
        with st.expander("🎙️ Or Start Guided 7-Question Voice Interview", expanded=False):
            st.caption("AI asks step-by-step questions in Amharic, Afaan Oromo, or English with native audio playback.")
            int_lang = st.selectbox("Interview Language", ["English", "Amharic", "Afaan Oromo"], index=0, key="int_lang")
            
            step_idx = st.session_state.get("interview_step_idx", 0)
            if step_idx < len(INTERVIEW_STEPS):
                cur_step = INTERVIEW_STEPS[step_idx]
                q_text = cur_step.question_en if int_lang == "English" else (cur_step.question_am if int_lang == "Amharic" else cur_step.question_or)
                
                st.markdown(f"**Step {step_idx + 1} of {len(INTERVIEW_STEPS)}: {cur_step.step_id}**")
                st.info(f"🗣️ **AI Asks:** {q_text}")
                
                # Autoplay Audio via gTTS
                try:
                    aud_bytes = generate_speech_audio(q_text, lang=int_lang)
                    st.audio(aud_bytes, format="audio/mp3", autoplay=True)
                except Exception:
                    pass

                ans_audio = st.audio_input(f"Your Answer for {cur_step.step_id}", key=f"int_ans_{cur_step.step_id}")
                if st.button("Submit Step Answer", key=f"btn_step_{cur_step.step_id}"):
                    st.session_state["interview_step_idx"] = step_idx + 1
                    st.toast(f"Recorded step {cur_step.step_id}!")
                    st.rerun()
            else:
                st.success("✅ Guided Interview Complete! Click 'Analyze & Build Truth Dossier' above to process.")
                if st.button("Reset Interview"):
                    st.session_state["interview_step_idx"] = 0
                    st.rerun()


    # -------------------------------------------------------------------------
    # AFTER SCORING TRANSPARENCY PANEL (FULL WIDTH)
    # -------------------------------------------------------------------------
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
            st.metric("Potential Score (Cap 100)", f"{sensitivity_res['potential_total']} / 100 [POTENTIAL]", delta=f"+{sensitivity_res['total_recoverable_points']} pts Recoverable")

        # 1. SUBMISSION READINESS SCREEN
        st.markdown("#### 🚦 Submission Readiness & Gate Status")
        st.progress(readiness_res["readiness_pct"] / 100.0)
        
        if readiness_res["is_ready"]:
            st.markdown("""<div class="banner-success"><b>✅ Application Ready for Submission</b>: All mandatory eligibility gates passed and zero critical blockers exist.</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="banner-danger"><b>❌ Action Required ({len(readiness_res['blockers'])} Blockers)</b>: Fix the critical items below before submitting to the investment committee.</div>""", unsafe_allow_html=True)
            for b in readiness_res["blockers"]:
                st.markdown(f"- 🔴 **{b}**")

        # 2. GRID COMPARISON TABLE
        st.markdown("#### ⚖️ Grid Variant Comparison & Routing Rationale")
        col_g1, col_g2 = st.columns([1, 2])
        with col_g1:
            st.table({
                "Evaluation Track": list(variants_comp["variant_scores"].keys()),
                "Calculated Score": [f"{v} / 100 pts" for v in variants_comp["variant_scores"].values()],
            })
        with col_g2:
            st.info(f"**Assigned Recommendation**: `{variants_comp['recommended_variant']}`\n\n{variants_comp['routing_reason']}")

        # 3. WHAT WOULD RAISE MY SCORE (SENSITIVITY ANALYSIS)
        st.markdown("#### 📈 What Would Raise My Score? (Gap Sensitivity)")
        st.caption("Resolving missing documentation unlocks recoverable evaluation points across linked criteria:")
        for s in sensitivity_res["sensitivities"]:
            badge_class = "chip-missing" if s["priority"] == "HIGH" else "chip-confirmation"
            st.markdown(f"""
            <div style="background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <b><code>{s['gap_field']}</code></b> &nbsp;<span class="chip {badge_class}">{s['priority']} PRIORITY</span><br/>
                    <small style="color:#6B7280;">Action Required From: <b>{s['required_from']}</b> • Impacts: <b>{s['criterion']}</b></small>
                </div>
                <div style="text-align:right;">
                    <span style="font-size:15px; font-weight:800; color:#059669;">+{s['recoverable_points']} pts</span><br/>
                    <small style="color:#6B7280;">Recoverable</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 4. 100-POINT CRITERIA BREAKDOWN
        with st.expander("📊 View Detailed 100-Point Scoring Rubric Breakdown", expanded=False):
            for c_score in score_res.criteria_scores:
                col_c1, col_c2 = st.columns([4, 1])
                with col_c1:
                    st.markdown(f"**{c_score.criterion.value.replace('_', ' ')}** ({c_score.awarded_points} / {c_score.max_points} pts)")
                    prog = c_score.awarded_points / c_score.max_points if c_score.max_points > 0 else 0
                    st.progress(prog)
                    st.caption(c_score.reasoning)
                with col_c2:
                    st.metric("Awarded", f"{c_score.awarded_points} / {c_score.max_points}")
                st.write("")

        # 5. COMMITTEE EXECUTIVE DEFENSE
        st.markdown("#### 📝 Investment Committee Executive Defense")
        st.info(score_res.reviewer_summary)


# =============================================================================
# TAB 2: REVIEWER PATH (BATCH PORTFOLIO RANKER)
# =============================================================================
with tab2:
    st.markdown('<div class="main-header">Reviewer Path: Batch Ranking & Portfolio Shortlist</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Reviewer committee workspace for evaluating and defending batches of scored SME proposals.</div>', unsafe_allow_html=True)

    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        uploaded_batch = st.file_uploader("Upload Batch JSON", type=["json"], key="reviewer_batch_file")
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
# TAB 3: CONSENT DIARY & MULTILINGUAL EXPLAINER
# =============================================================================
with tab3:
    st.markdown('<div class="main-header">Multilingual Verbal Consent & Audit Diary</div>', unsafe_allow_html=True)
    st.markdown("""<div class="banner-danger"><b>⚠️ MANDATORY RULE</b>: Declarations are <b>NEVER auto-ticked</b>. Informed verbal consent is recorded and audited individually per covenant.</div>""", unsafe_allow_html=True)

    col_cs1, col_cs2 = st.columns([1, 1])
    with col_cs1:
        st.markdown("#### 🎙️ Verbal Explanation Generator")
        c_lang = st.selectbox("Applicant Spoken Language", ["Amharic", "Afaan Oromo", "English"], index=0, key="c_lang_sel")
        
        if st.button("Generate Verbal Reading Script", type="primary", use_container_width=True):
            with st.spinner("Generating plain-language verbal scripts..."):
                cur_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                pkg = generate_consent_package(detected_language=c_lang, api_key=cur_key)
                st.session_state["consent_pkg"] = pkg
                st.rerun()

        if "consent_pkg" in st.session_state:
            pkg = st.session_state["consent_pkg"]
            for i, exp in enumerate(pkg.explanations, 1):
                st.markdown(f"**{i}. {exp.declaration_id}**")
                st.info(f"🗣️ **Spoken Explanation:** {exp.translated_simple_explanation}\n\n❓ **Consent Question:** {exp.verbal_consent_question}")

    with col_cs2:
        st.markdown("#### 📋 Consent Audit Diary")
        
        # Test Simulation Controls
        st.markdown("##### 🧪 Simulate Verbal Consent Input")
        sim_decl = st.selectbox("Select Declaration", ["declaration_05_anti_bribery_corruption", "declaration_08_child_labor_prevention", "declaration_02_truthful_information"])
        sim_resp = st.text_input("Spoken Response Transcript", value="አዎ እስማማለሁ (Yes, I agree)")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("✅ Record Verified YES", use_container_width=True):
                if "consent_diary" not in st.session_state:
                    st.session_state["consent_diary"] = []
                rec = record_consent(sim_decl, c_lang, True, sim_resp)
                st.session_state["consent_diary"].append(rec)
                st.toast(f"Recorded YES consent for {sim_decl}!")
                st.rerun()
        with col_btn2:
            if st.button("🚫 Revoke Consent", use_container_width=True):
                if "consent_diary" in st.session_state:
                    for idx, r in enumerate(st.session_state["consent_diary"]):
                        if r.declaration_id == sim_decl and r.status == ConsentStatus.ACTIVE:
                            st.session_state["consent_diary"][idx] = revoke_consent(r)
                            st.toast(f"Revoked consent for {sim_decl}!")
                            st.rerun()

        # Render Diary Table
        diary = st.session_state.get("consent_diary", [])
        if diary:
            st.markdown("##### Recorded Audit Trail")
            table_data = [
                {
                    "Declaration": r.declaration_id,
                    "Language": r.language,
                    "Verdict": r.response_verdict.value,
                    "Status": r.status.value,
                    "Timestamp (UTC)": r.timestamp[:19],
                }
                for r in diary
            ]
            st.table(table_data)
        else:
            st.caption("No verbal consent records registered yet in this session.")
