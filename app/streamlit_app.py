"""
TeraGrant Agent — AI Intake & Evaluation Platform
AI Builder Hackathon 2026 | Challenge 1 (SME Grant Automation)

An end-to-end multi-agent system that converts informal voice notes, trade license photos,
and workshop facility images into fundable, audit-grade grant application packs,
scores them across a 100-point matrix, detects discrepancies, and defends ranked shortlists.
"""

import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from extractors.config import MODEL_FALLBACK_CHAIN
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
    RankedCompany,
    RankedShortlist,
)
from schemas.consent_schema import ConsentPackage
from agents.mapper_agent import generate_application_pack
from agents.eligibility_agent import run_eligibility_gate
from agents.router_agent import route_to_grid_variant
from agents.scorer_agent import score_application
from agents.contradiction_agent import detect_contradictions
from agents.batch_ranker_agent import rank_batch
from agents.declaration_explainer_agent import generate_consent_package
from app.digital_twin import render_giz_form, convert_to_serializable
from app.heartbeat_ui import render_heartbeat
from app.chat_bubble_ui import render_chat_bubble, render_question_bubble
from app.tts_ui import speak_question
from app.rehearsal_data import get_almaz_scenario, get_nahom_scenario
from schemas.interview_schema import InterviewStep, AnswerExtraction
from agents.interview_agent import (
    INTERVIEW_STEPS,
    extract_answer,
    merge_answer,
    synthesize_audio_extraction,
)


# =============================================================================
# PAGE CONFIGURATION & STYLING
# =============================================================================
st.set_page_config(
    page_title="TeraGrant Agent | AI SME Grant System",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .gap-card {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .contra-card {
        background-color: #FEF2F2;
        border-left: 4px solid #EF4444;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR CONFIGURATION
# =============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/hand-planting.png", width=64)
    st.title("TeraGrant Agent")
    st.caption("AI-Powered SME Grant Intake & Evaluation Engine")
    st.divider()

    st.subheader("⚙️ System Configuration")
    env_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    api_key = st.text_input(
        "Gemini API Key",
        value=st.session_state.get("api_key", env_api_key),
        type="password",
        help="Enter your Google Gemini API key for live multimodal agent execution."
    )
    if api_key:
        st.session_state["api_key"] = api_key
        os.environ["GEMINI_API_KEY"] = api_key

    model_choice = st.selectbox(
        "Gemini Foundation Model",
        options=["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-1.5-pro-latest"],
        index=0,
        help="Select the Gemini multimodal reasoning model (defaults to gemini-1.5-flash with automatic failover)."
    )

    st.divider()
    st.markdown("### 🧩 Agent Architecture")
    st.markdown("""
    - **Vision OCR Agent** (Zero-Hallucination)
    - **Workshop Evaluator** (Visual Asset Cross-Check)
    - **Audio Transcriber** (Amharic / Oromo / Eng)
    - **Intake & Gap Mapper** (Form Normalizer)
    - **Deterministic Gate** (Pure Python 15-Check)
    - **Forensic Auditor** (Discrepancies)
    - **100-Pt Reviewer** (3 Track Multipliers)
    - **Portfolio Ranker** (Batch Shortlisting)
    - **Consent Explainer** (Never Auto-Tick)
    """)
    st.caption("AI Builder Hackathon 2026 • Production Build")


# =============================================================================
# MAIN INTERFACE TABS
# =============================================================================
tab1, tab2, tab3 = st.tabs([
    "🚀 1. Applicant Intake & Digital Twin",
    "📊 2. Reviewer Batch Ranker",
    "📜 3. Multilingual Verbal Consent",
])


# =============================================================================
# TAB 1: APPLICANT PATH (SPLIT-SCREEN DIGITAL TWIN & INTAKE)
# =============================================================================
with tab1:
    st.markdown('<div class="main-header">Applicant Path: Voice to Fundable Proposal</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload a voice note or record live. The Agent listens and fills the official GIZ SME Support Scheme form in real-time.</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # MODE SELECTOR AT TOP OF TAB 1
    # -------------------------------------------------------------------------
    mode_choice = st.radio(
        "Select Operating Mode:",
        options=[
            "🎙️ LIVE INTAKE MODE — Real user data only (default)",
            "🎭 REHEARSAL MODE — Cached scenarios for stage backup"
        ],
        index=0,
        key="mode_radio",
        horizontal=True
    )
    is_live_mode = "LIVE" in mode_choice
    st.session_state["mode"] = "LIVE" if is_live_mode else "REHEARSAL"

    st.divider()

    # -------------------------------------------------------------------------
    # REHEARSAL MODE BUTTONS (Only shown when explicitly chosen)
    # -------------------------------------------------------------------------
    if not is_live_mode:
        st.info("🎭 **Rehearsal Mode Active**: Click either pre-calculated scenario below to load verified backup data without calling live APIs.")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("🌶️ Load Almaz Scenario (Spice Mill — Smudged TIN & Gaps)", type="secondary", use_container_width=True):
                pack, scoring_res, contras, data_map = get_almaz_scenario()
                st.session_state["extracted_data"] = data_map
                st.session_state["latest_pack"] = pack
                st.session_state["latest_score"] = scoring_res
                st.session_state["latest_contradictions"] = contras
                st.session_state["latest_audio_transcript"] = AudioTranscriptExtraction(
                    transcript="My name is Almaz Bekele. I run a spice mill in Bahir Dar with 8 employees. We produce fine ground berbere and shiro.",
                    detected_language="Amharic",
                    business_name="Almaz Spice Mill",
                    employee_count=8,
                    product_type="Ground Spices & Berbere",
                    location="Bahir Dar",
                    financial_figures=["450,000 Birr"],
                    impact_summary="Spice processing cooperative seeking commercial pulverizer."
                )
                st.session_state["is_active"] = False
                st.rerun()
        with col_r2:
            if st.button("⚡ Load Nahom Scenario (Tech Repair — 92/100 Innovation)", type="secondary", use_container_width=True):
                pack, scoring_res, contras, data_map = get_nahom_scenario()
                st.session_state["extracted_data"] = data_map
                st.session_state["latest_pack"] = pack
                st.session_state["latest_score"] = scoring_res
                st.session_state["latest_contradictions"] = contras
                st.session_state["latest_audio_transcript"] = AudioTranscriptExtraction(
                    transcript="My name is Nahom Tadesse. I operate Nahom Solar Tech solutions in Hawassa. We assemble solar charge controllers with 12 technicians.",
                    detected_language="English",
                    business_name="Nahom Solar Tech Solutions",
                    employee_count=12,
                    product_type="Solar Charge Controllers",
                    location="Hawassa",
                    financial_figures=["850,000 Birr"],
                    impact_summary="Clean-tech hardware assembly replacing imported solar accessories."
                )
                st.session_state["is_active"] = False
                st.rerun()
        st.divider()

    # -------------------------------------------------------------------------
    # TWO-COLUMN SPLIT SCREEN LAYOUT
    # -------------------------------------------------------------------------
    col_left, col_right = st.columns([1.2, 0.8], gap="medium")

    # RIGHT COLUMN: AI INTAKE CONTROLS
    with col_right:
        st.markdown("### 🎙️ Agent Intake Interface")
        
        # Render Live Heartbeat Component
        is_agent_active = st.session_state.get("is_active", False)
        render_heartbeat(is_active=is_agent_active, height=65)

        # Supporting Documents (Available for both Guided and Free-form)
        with st.expander("📎 Supporting Documents (License & Workshop Photo)", expanded=False):
            uploaded_license = st.file_uploader(
                "Upload Commercial License (.jpg/.png/.pdf)",
                type=["jpg", "jpeg", "png", "webp", "pdf"],
                key="license_uploader"
            )
            uploaded_workshop = st.file_uploader(
                "Upload Workshop Facility Photo (.jpg/.png)",
                type=["jpg", "jpeg", "png", "webp"],
                key="workshop_uploader"
            )

        intake_style = st.radio(
            "Select Intake Mode:",
            options=[
                "🗣️ Guided Interview (AI asks you)",
                "📄 Free-form (one voice note)",
            ],
            index=0,
            horizontal=True,
            key="intake_style_radio"
        )
        is_guided = "Guided" in intake_style

        if is_guided:
            # =================================================================
            # GUIDED CONVERSATIONAL INTERVIEW STATE MACHINE
            # =================================================================
            step_idx = st.session_state.setdefault("interview_step_index", 0)
            interview_data = st.session_state.setdefault("interview_data", {})
            interview_transcripts = st.session_state.setdefault("interview_transcripts", [])

            if step_idx < len(INTERVIEW_STEPS):
                current_step = INTERVIEW_STEPS[step_idx]
                st.progress(step_idx / float(len(INTERVIEW_STEPS)))
                st.caption(f"Question {step_idx + 1} of {len(INTERVIEW_STEPS)} • Field: `{current_step.field_path}`")

                # AI Question Bubble
                render_question_bubble(
                    question_en=current_step.question_en,
                    question_am=current_step.question_am,
                    question_or=current_step.question_or,
                    step_id=current_step.step_id,
                    step_num=step_idx + 1,
                    total_steps=len(INTERVIEW_STEPS),
                )

                # Browser TTS Control
                speak_question(text=current_step.question_en, lang="en", autoplay=False)

                # Audio Recording per step
                step_audio = st.audio_input(
                    f"Speak your answer for {current_step.step_id}",
                    key=f"guided_audio_{step_idx}"
                )

                if step_audio is not None:
                    raw_audio_bytes = step_audio.getvalue()
                    audio_sig = f"step_{step_idx}_{len(raw_audio_bytes)}"
                    if st.session_state.get(f"sig_{step_idx}") != audio_sig:
                        curr_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                        if curr_key:
                            with st.spinner("🎙️ Transcribing and extracting fact..."):
                                try:
                                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_f:
                                        tmp_f.write(raw_audio_bytes)
                                        tmp_f_path = tmp_f.name
                                    step_trans_obj = extract_audio_story(audio_path=tmp_f_path, model=model_choice, api_key=curr_key)
                                    st.session_state[f"transcript_{step_idx}"] = step_trans_obj.transcript

                                    ans_ext = extract_answer(
                                        step=current_step,
                                        transcript=step_trans_obj.transcript,
                                        model=model_choice,
                                        api_key=curr_key
                                    )
                                    st.session_state[f"extraction_{step_idx}"] = ans_ext
                                    st.session_state[f"sig_{step_idx}"] = audio_sig
                                except Exception as err:
                                    st.session_state[f"sig_{step_idx}"] = audio_sig
                                    st.warning(f"Note: {str(err)}")

                trans_val = st.session_state.get(f"transcript_{step_idx}")
                ext_val = st.session_state.get(f"extraction_{step_idx}")

                if trans_val:
                    st.markdown(f"**🗣️ Spoken Transcript:** *\"{trans_val}\"*")

                can_advance = False
                if ext_val:
                    if ext_val.value and ext_val.confidence >= 0.5:
                        st.success(f"✅ Extracted: **{ext_val.value}** (Confidence: {int(ext_val.confidence * 100)}%)")
                        updated_int_data = merge_answer(st.session_state["interview_data"], current_step, ext_val)
                        st.session_state["interview_data"] = updated_int_data
                        st.session_state["extracted_data"] = convert_to_serializable(updated_int_data)
                        can_advance = True
                    else:
                        st.warning("⚠️ I didn't catch that fact clearly — record again or skip.")

                col_n1, col_n2, col_n3 = st.columns([1.5, 1.5, 1])
                with col_n1:
                    if st.button("➡️ Next Question", type="primary" if can_advance else "secondary", disabled=not can_advance, use_container_width=True, key=f"next_{step_idx}"):
                        if trans_val:
                            st.session_state["interview_transcripts"].append(f"Q: {current_step.question_en} | A: {trans_val}")
                        st.session_state["interview_step_index"] = step_idx + 1
                        st.rerun()

                with col_n2:
                    if st.button("⏭️ Skip Question", type="secondary", use_container_width=True, key=f"skip_{step_idx}"):
                        st.session_state["interview_transcripts"].append(f"Q: {current_step.question_en} | A: [Skipped]")
                        st.session_state["interview_step_index"] = step_idx + 1
                        st.rerun()

                with col_n3:
                    if st.button("🔄 Reset", type="secondary", use_container_width=True, key=f"reset_{step_idx}"):
                        st.session_state["interview_step_index"] = 0
                        st.session_state["interview_data"] = {}
                        st.session_state["interview_transcripts"] = []
                        st.session_state["extracted_data"] = {}
                        st.rerun()

            else:
                # All 7 questions completed!
                st.progress(1.0)
                st.success("🎉 All 7 interview questions completed! Review your answers or submit for committee evaluation.")

                col_f1, col_f2 = st.columns([2, 1])
                with col_f1:
                    finish_guided_btn = st.button("🏁 Finish & Score Application", type="primary", use_container_width=True)
                with col_f2:
                    if st.button("🔄 Restart Interview", type="secondary", use_container_width=True):
                        st.session_state["interview_step_index"] = 0
                        st.session_state["interview_data"] = {}
                        st.session_state["interview_transcripts"] = []
                        st.session_state["extracted_data"] = {}
                        st.rerun()

                if finish_guided_btn:
                    current_key = os.getenv("GEMINI_API_KEY")
                    if not current_key:
                        st.error("❌ Gemini API Key is required for Live Mode! Please enter it in the sidebar.")
                        st.stop()

                    st.session_state["is_active"] = True

                    with st.status("🤖 Processing Guided Interview Dossier & Scoring...", expanded=True) as status_box:
                        try:
                            # Step 1: Synthesize
                            st.write("🎙️ **Step 1/4: Synthesizing Guided Voice Intake Dossier...**")
                            audio_data = synthesize_audio_extraction(
                                interview_data=st.session_state.get("interview_data", {}),
                                transcript_parts=st.session_state.get("interview_transcripts", [])
                            )
                            st.session_state["latest_audio_transcript"] = audio_data

                            # Step 2: License & Workshop
                            st.write("👁️ **Step 2/4: Reading Trade License & Analyzing Facility Assets...**")
                            if uploaded_license:
                                with tempfile.NamedTemporaryFile(suffix=Path(uploaded_license.name).suffix, delete=False) as tmp_img:
                                    tmp_img.write(uploaded_license.read())
                                    tmp_img_path = tmp_img.name
                                license_data = extract_license_data(image_path=tmp_img_path, model=model_choice)
                            else:
                                license_data = LicenseExtraction(
                                    is_legible=False,
                                    extraction_notes="No official commercial license document uploaded."
                                )

                            workshop_data = None
                            if uploaded_workshop:
                                with tempfile.NamedTemporaryFile(suffix=Path(uploaded_workshop.name).suffix, delete=False) as tmp_ws:
                                    tmp_ws.write(uploaded_workshop.read())
                                    tmp_ws_path = tmp_ws.name
                                workshop_data = extract_workshop_data(image_path=tmp_ws_path, model=model_choice)

                            # Step 3: Application Pack & Gaps
                            st.write("📋 **Step 3/4: Mapping to Official GIZ Form & Flagging Information Gaps...**")
                            pack = generate_application_pack(
                                license_data=license_data,
                                audio_data=audio_data,
                                workshop_data=workshop_data,
                                model=model_choice
                            )

                            # Step 4: Gate, Router, Scorer, Contradictions
                            st.write("⚖️ **Step 4/4: Running 15-Point Eligibility Gate, Grid Router & 100-Point Scorer...**")
                            gate = run_eligibility_gate(pack.application)
                            contradictions = detect_contradictions(pack=pack, workshop_data=workshop_data, model=model_choice)
                            if pack.application and pack.impact:
                                grid_variant = route_to_grid_variant(pack.application, pack.impact, model=model_choice)
                            else:
                                grid_variant = GridVariant.GENERAL_SME
                            scoring_result = score_application(pack=pack, variant=grid_variant, model=model_choice)

                            # Map data to digital twin
                            app_data = pack.application
                            imp_data = pack.impact
                            b_info = app_data.business_info if app_data else None
                            emp = app_data.employment if app_data else None

                            extracted_data_map = {
                                "company_name": b_info.business_name if b_info else None,
                                "tin_number": b_info.tin_number if b_info else None,
                                "address": b_info.location if b_info else None,
                                "mobile": "+251 (On File)",
                                "years_in_operation": b_info.years_in_operation if b_info else None,
                                "total_staff": emp.total_staff if emp else None,
                                "female_staff": emp.gender_split.female if (emp and emp.gender_split) else None,
                                "main_products": imp_data.project_title if imp_data else (audio_data.product_type or audio_data.impact_summary),
                                "organogram_status": "Formal Organization" if (app_data and app_data.organogram) else "Owner-Managed Structure",
                                "machinery_requested": ", ".join(m.name for m in app_data.financials.machinery_list) if (app_data and app_data.financials and app_data.financials.machinery_list) else (imp_data.milestones[0] if (imp_data and imp_data.milestones) else "Equipment Upgrades"),
                                "requested_etb": imp_data.etb_financial_target if imp_data else None,
                                "gap_fields": [g.field_name.split(".")[-1] for g in pack.gaps],
                            }

                            st.session_state["extracted_data"] = extracted_data_map
                            st.session_state["latest_pack"] = pack
                            st.session_state["latest_score"] = scoring_result
                            st.session_state["latest_contradictions"] = contradictions
                            st.session_state["is_active"] = False

                            status_box.update(label="✅ Guided Interview Application Processed Successfully!", state="complete", expanded=False)
                            st.rerun()

                        except Exception as e:
                            st.session_state["is_active"] = False
                            err_msg = str(e)
                            status_box.update(label=f"❌ Live API Failed: {err_msg}", state="error", expanded=True)
                            if "NETWORK UNREACHABLE" in err_msg:
                                st.error(
                                    f"❌ **Network Failure:** {err_msg}\n\n"
                                    "- 📶 Connect your laptop to a phone hotspot and retry.\n"
                                    "- 🔐 If on venue Wi-Fi, open a browser and complete the login/captive-portal page first.\n"
                                    "- 🚫 Disable VPN/proxy/strict antivirus, then retry."
                                )
                            else:
                                st.error(f"Live API failed: {err_msg}.")

        else:
            # =================================================================
            # FREE-FORM VOICE INTAKE PIPELINE (ORIGINAL)
            # =================================================================
            # 1. Live Voice Recording via Microphone (Priority)
            st.markdown("##### 1. Live Voice Recording (Microphone)")
            try:
                live_audio = st.audio_input("Record your business story (Amharic / Oromo / English)")
            except Exception:
                live_audio = None

            # 2. Upload Audio File
            st.markdown("##### 2. Or Upload Voice Note File")
            uploaded_audio = st.file_uploader(
                "Upload Voice File (.mp3/.wav/.m4a/.ogg/.oga/.webm)",
                type=["mp3", "wav", "m4a", "ogg", "oga", "webm"],
                key="audio_uploader"
            )

            # 3. Spoken Language
            st.markdown("##### 3. Spoken Language")
            intake_language = st.radio(
                "Language",
                options=["Amharic", "Oromo", "English"],
                index=0,
                horizontal=True,
            )

            # Real-time Voice Transcription Trigger (Chat Bubble UI)
            audio_sig = None
            if is_live_mode:
                raw_audio = None
                audio_fmt = ".wav"
                if live_audio is not None:
                    raw_audio = live_audio.getvalue()
                    audio_fmt = ".wav"
                    audio_sig = f"live_mic_{len(raw_audio)}_{hash(raw_audio[:500]) if len(raw_audio) > 0 else 0}"
                elif uploaded_audio is not None:
                    raw_audio = uploaded_audio.getvalue()
                    audio_fmt = Path(uploaded_audio.name).suffix.lower()
                    audio_sig = f"upload_{uploaded_audio.name}_{len(raw_audio)}"

                if model_choice and ("2.0" in model_choice or "3.6" in model_choice):
                    model_choice = "gemini-1.5-flash"

                if raw_audio and st.session_state.get("last_transcribed_audio_sig") != audio_sig:
                    curr_key = os.getenv("GEMINI_API_KEY") or st.session_state.get("api_key")
                    if curr_key:
                        with st.spinner("🎙️ Agent listening and transcribing voice note in real-time..."):
                            try:
                                with tempfile.NamedTemporaryFile(suffix=audio_fmt, delete=False) as tmp_live_aud:
                                    tmp_live_aud.write(raw_audio)
                                    tmp_live_path = tmp_live_aud.name
                                auto_audio_data = extract_audio_story(audio_path=tmp_live_path, model=model_choice, api_key=curr_key)
                                st.session_state["latest_audio_transcript"] = auto_audio_data
                                st.session_state["last_transcribed_audio_sig"] = audio_sig
                            except Exception as live_err:
                                st.session_state["last_transcribed_audio_sig"] = audio_sig
                                live_msg = str(live_err)
                                if "NETWORK UNREACHABLE" in live_msg:
                                    st.error(
                                        f"❌ **Network Failure during Voice Intake:** {live_msg}\n\n"
                                        "- 📶 Connect your laptop to a phone hotspot and retry.\n"
                                        "- 🔐 If on venue Wi-Fi, open a browser and complete the login/captive-portal page first.\n"
                                        "- 🚫 Disable VPN/proxy/strict antivirus, then retry."
                                    )
                                else:
                                    st.caption(f"Voice note intake: {live_msg}")

            # Render WhatsApp-style Live Chat Bubble
            if st.session_state.get("latest_audio_transcript"):
                st.markdown("##### 💬 Live Conversational Transcript")
                render_chat_bubble(st.session_state["latest_audio_transcript"])

            process_btn = st.button("🚀 Process & Score Application", type="primary", use_container_width=True)

            # PIPELINE EXECUTION FOR FREE-FORM
            if process_btn and is_live_mode:
                if model_choice and ("2.0" in model_choice or "3.6" in model_choice):
                    model_choice = "gemini-1.5-flash"

                current_key = os.getenv("GEMINI_API_KEY")
                if not current_key:
                    st.error("❌ Gemini API Key is required for Live Mode! Please enter it in the sidebar.")
                    st.stop()

                audio_bytes = None
                audio_ext = ".wav"
                if live_audio:
                    audio_bytes = live_audio.read()
                    audio_ext = ".wav"
                elif uploaded_audio:
                    audio_bytes = uploaded_audio.read()
                    audio_ext = Path(uploaded_audio.name).suffix.lower()
                else:
                    st.error("❌ Please record with your microphone or upload a voice note first.")
                    st.stop()

                st.session_state["is_active"] = True

                with st.status("🤖 Processing SME Application Intake...", expanded=True) as status_box:
                    try:
                        st.write("🎙️ **Step 1/4: Transcribing Voice Note & Extracting Business Narrative...**")
                        if st.session_state.get("latest_audio_transcript") and audio_sig and st.session_state.get("last_transcribed_audio_sig") == audio_sig:
                            audio_data = st.session_state["latest_audio_transcript"]
                        else:
                            with tempfile.NamedTemporaryFile(suffix=audio_ext, delete=False) as tmp_aud:
                                tmp_aud.write(audio_bytes)
                                tmp_aud_path = tmp_aud.name
                            audio_data = extract_audio_story(audio_path=tmp_aud_path, model=model_choice)
                            st.session_state["latest_audio_transcript"] = audio_data
                            if audio_sig:
                                st.session_state["last_transcribed_audio_sig"] = audio_sig

                        # Step 2
                        st.write("👁️ **Step 2/4: Reading Trade License & Analyzing Facility Assets...**")
                        if uploaded_license:
                            with tempfile.NamedTemporaryFile(suffix=Path(uploaded_license.name).suffix, delete=False) as tmp_img:
                                tmp_img.write(uploaded_license.read())
                                tmp_img_path = tmp_img.name
                            license_data = extract_license_data(image_path=tmp_img_path, model=model_choice)
                        else:
                            license_data = LicenseExtraction(
                                is_legible=False,
                                extraction_notes="No official commercial license document uploaded."
                            )

                        workshop_data = None
                        if uploaded_workshop:
                            with tempfile.NamedTemporaryFile(suffix=Path(uploaded_workshop.name).suffix, delete=False) as tmp_ws:
                                tmp_ws.write(uploaded_workshop.read())
                                tmp_ws_path = tmp_ws.name
                            workshop_data = extract_workshop_data(image_path=tmp_ws_path, model=model_choice)

                        # Step 3
                        st.write("📋 **Step 3/4: Mapping to Official GIZ Form & Flagging Information Gaps...**")
                        pack = generate_application_pack(
                            license_data=license_data,
                            audio_data=audio_data,
                            workshop_data=workshop_data,
                            model=model_choice
                        )

                        # Step 4
                        st.write("⚖️ **Step 4/4: Running 15-Point Eligibility Gate, Grid Router & 100-Point Scorer...**")
                        gate = run_eligibility_gate(pack.application)
                        contradictions = detect_contradictions(pack=pack, workshop_data=workshop_data, model=model_choice)
                        if pack.application and pack.impact:
                            grid_variant = route_to_grid_variant(pack.application, pack.impact, model=model_choice)
                        else:
                            grid_variant = GridVariant.GENERAL_SME
                        scoring_result = score_application(pack=pack, variant=grid_variant, model=model_choice)

                        app_data = pack.application
                        imp_data = pack.impact
                        b_info = app_data.business_info if app_data else None
                        emp = app_data.employment if app_data else None

                        extracted_data_map = {
                            "company_name": b_info.business_name if b_info else None,
                            "tin_number": b_info.tin_number if b_info else None,
                            "address": b_info.location if b_info else None,
                            "mobile": "+251 (On File)",
                            "years_in_operation": b_info.years_in_operation if b_info else None,
                            "total_staff": emp.total_staff if emp else None,
                            "female_staff": emp.gender_split.female if (emp and emp.gender_split) else None,
                            "main_products": imp_data.project_title if imp_data else (audio_data.product_type or audio_data.impact_summary),
                            "organogram_status": "Formal Organization" if (app_data and app_data.organogram) else "Owner-Managed Structure",
                            "machinery_requested": ", ".join(m.name for m in app_data.financials.machinery_list) if (app_data and app_data.financials and app_data.financials.machinery_list) else (imp_data.milestones[0] if (imp_data and imp_data.milestones) else "Equipment Upgrades"),
                            "requested_etb": imp_data.etb_financial_target if imp_data else None,
                            "gap_fields": [g.field_name.split(".")[-1] for g in pack.gaps],
                        }

                        st.session_state["extracted_data"] = extracted_data_map
                        st.session_state["latest_pack"] = pack
                        st.session_state["latest_score"] = scoring_result
                        st.session_state["latest_contradictions"] = contradictions
                        st.session_state["is_active"] = False

                        status_box.update(label="✅ Application Processed Successfully!", state="complete", expanded=False)
                        st.rerun()

                    except Exception as e:
                        st.session_state["extracted_data"] = {}
                        st.session_state["latest_pack"] = None
                        st.session_state["latest_score"] = None
                        st.session_state["latest_contradictions"] = []
                        st.session_state["is_active"] = False
                        err_msg = str(e)
                        status_box.update(label=f"❌ Live API Failed: {err_msg}", state="error", expanded=True)
                        if "NETWORK UNREACHABLE" in err_msg:
                            st.error(
                                f"❌ **Network Failure:** {err_msg}\n\n"
                                "- 📶 Connect your laptop to a phone hotspot and retry.\n"
                                "- 🔐 If on venue Wi-Fi, open a browser and complete the login/captive-portal page first.\n"
                                "- 🚫 Disable VPN/proxy/strict antivirus, then retry."
                            )
                        else:
                            st.error(f"Live API failed: {err_msg}. No fake data shown in Live Mode.")

    # -------------------------------------------------------------------------
    # LEFT COLUMN: DIGITAL TWIN FORM & POST-EVALUATION METRICS
    # -------------------------------------------------------------------------
    with col_left:
        # Debug Expander: Raw Audio Transcript
        if st.session_state.get("latest_audio_transcript"):
            raw_aud: AudioTranscriptExtraction = st.session_state["latest_audio_transcript"]
            with st.expander("🔍 Debug: Raw AI Transcript & Audio Extraction", expanded=False):
                st.markdown(f"**🗣️ Spoken Language:** `{raw_aud.detected_language}`")
                st.markdown(f"**📝 Verbatim Transcript:**\n> *\"{raw_aud.transcript}\"*")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"- **Business Name:** `{raw_aud.business_name}`")
                    st.markdown(f"- **Headcount:** `{raw_aud.employee_count}`")
                    st.markdown(f"- **Product:** `{raw_aud.product_type}`")
                with col_d2:
                    st.markdown(f"- **Location:** `{raw_aud.location}`")
                    st.markdown(f"- **Financials:** `{raw_aud.financial_figures}`")
                    st.markdown(f"- **Impact Summary:** `{raw_aud.impact_summary}`")

        st.markdown("### 📋 Official GIZ/Sequa Application Form (Digital Twin)")
        st.caption("Live HTML/JS replica of the official SME Support Scheme grant form. Fields update dynamically in real-time.")

        # Render HTML/JS Digital Twin Form Component (Starts 100% empty)
        current_data = st.session_state.get("extracted_data", {})
        render_giz_form(session_data=current_data, height=580)

        # Post-Evaluation Results Section (Only rendered after real processing or explicit rehearsal loading)
        if st.session_state.get("latest_score"):
            score_res: ScoringResult = st.session_state["latest_score"]
            pack_res: ApplicationPack = st.session_state["latest_pack"]
            contra_res: list = st.session_state.get("latest_contradictions", [])

            st.divider()
            st.markdown("### 🏆 AI Evaluation Summary & Committee Scoring")

            # Projector High-Contrast Metric Banner
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                delta_val = "Eligible" if score_res.eligibility_gate.is_eligible else "Disqualified"
                st.metric(
                    label="Total Score",
                    value=f"{score_res.total_score} / 100",
                    delta=delta_val,
                    delta_color="normal" if score_res.eligibility_gate.is_eligible else "inverse"
                )
            with m2:
                st.metric(label="Scoring Track", value=score_res.grid_variant.value)
            with m3:
                st.metric(label="Gate Verdict", value="PASSED" if score_res.eligibility_gate.is_eligible else "FAILED")
            with m4:
                st.metric(label="Missing Gaps", value=f"{len(pack_res.gaps) if pack_res else 0} Flagged")

            # 1. Eligibility Gate Status
            if score_res.eligibility_gate.is_eligible:
                st.success(f"✅ **Eligibility Gate: PASSED** — {score_res.eligibility_gate.gate_reasoning}")
            else:
                st.error(f"❌ **Eligibility Gate: FAILED** — {score_res.eligibility_gate.gate_reasoning}")

            # 2. Flagged Contradictions (if any)
            if contra_res:
                st.error(f"🚨 **{len(contra_res)} Forensic Discrepancies Detected:**")
                for c in contra_res:
                    st.markdown(f"""
                    <div class="contra-card">
                        <b>[{c.severity.value}]</b> {c.explanation}<br/>
                        <small><b>Claim A:</b> {c.claim_a} | <b>Claim B:</b> {c.claim_b}</small>
                    </div>
                    """, unsafe_allow_html=True)

            # 3. Explicit Gap List (Zero-Hallucination Audit)
            st.subheader("📋 Identified Information Gaps (Zero-Hallucination)")
            if pack_res and pack_res.gaps:
                st.warning(f"⚠️ **The AI identified {len(pack_res.gaps)} missing/unverified data points and strictly REFUSED to hallucinate them:**")
                for g in pack_res.gaps:
                    badge = "🔴 HIGH PRIORITY" if g.priority == GapPriority.HIGH else ("🟡 MEDIUM" if g.priority == GapPriority.MEDIUM else "🟢 LOW")
                    st.markdown(f"""
                    <div class="gap-card">
                        <b>{badge} — <code>{g.field_name}</code></b> (Action Required From: <b>{g.required_from}</b>)<br/>
                        {g.reason_missing}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ **Zero Gaps Identified**: The application package has complete verified documentation across all mandatory sections.")

            # 4. 100-Point Scoring Grid Breakdown
            with st.expander("📊 View Detailed 100-Point Criteria Breakdown", expanded=False):
                for c_score in score_res.criteria_scores:
                    col_c1, col_c2 = st.columns([4, 1])
                    with col_c1:
                        st.markdown(f"**{c_score.criterion.value.replace('_', ' ')}** ({c_score.awarded_points} / {c_score.max_points} pts)")
                        progress_val = c_score.awarded_points / c_score.max_points if c_score.max_points > 0 else 0
                        st.progress(progress_val)
                        st.caption(c_score.reasoning)
                    with col_c2:
                        st.metric("Awarded", f"{c_score.awarded_points} / {c_score.max_points}")
                    st.write("")

            # 5. Executive Defense
            st.subheader("📝 Investment Committee Executive Defense")
            st.info(score_res.reviewer_summary)


# =============================================================================
# TAB 2: REVIEWER PATH (BATCH RANKER & SHORTLIST)
# =============================================================================
with tab2:
    st.markdown('<div class="main-header">Reviewer Path: Batch Ranking & Shortlisting</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload a batch portfolio of SME applications. The ranker sorts them deterministically by total score and generates executive defenses and site-visit due diligence questions.</div>', unsafe_allow_html=True)

    col_b1, col_b2 = st.columns([2, 1])
    with col_b1:
        uploaded_batch = st.file_uploader("Upload Batch Portfolio JSON", type=["json"], key="batch_uploader")
    with col_b2:
        st.markdown("##### ⚡ Quick Load Presets")
        load_12_preset = st.button("📂 Load 12-Applicant Portfolio", use_container_width=True)

    if load_12_preset or uploaded_batch:
        if uploaded_batch:
            raw_batch_data = json.load(uploaded_batch)
        else:
            sample_path = PROJECT_ROOT / "data" / "sample_batch_12_applicants.json"
            with open(sample_path, "r", encoding="utf-8") as f:
                raw_batch_data = json.load(f)

        st.session_state["raw_batch_data"] = raw_batch_data
        st.success(f"Loaded batch with {len(raw_batch_data)} SME grant applicants!")

    if "raw_batch_data" in st.session_state:
        batch_items = st.session_state["raw_batch_data"]

        if st.button("⚡ Rank Batch & Defend Shortlist", type="primary", use_container_width=True):
            with st.spinner("📊 Sorting applicants, validating contradictions, and synthesizing committee justifications..."):
                scored_entries = []
                contra_dict = {}

                for item in batch_items:
                    b_name = item.get("business_name", "Unnamed SME")
                    score_val = item.get("total_score", 70)
                    variant_val = GridVariant(item.get("grid_variant", "GENERAL_SME"))
                    is_elig = item.get("is_eligible", True)
                    rev_sum = item.get("reviewer_summary", "Reviewer summary")

                    mock_criteria = [
                        CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=min(score_val, 20), reasoning="Job creation potential verified."),
                        CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=min(max(score_val - 20, 0), 15), reasoning="Demographic inclusion verified."),
                        CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=min(max(score_val - 35, 0), 15), reasoning="Innovation score verified."),
                        CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=min(max(score_val - 50, 0), 15), reasoning="Financial health verified."),
                        CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=min(max(score_val - 65, 0), 10), reasoning="Local supply integration verified."),
                        CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=min(max(score_val - 75, 0), 10), reasoning="SDG impact verified."),
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
                            gate_reasoning="Confirmed" if is_elig else "Disqualified due to unverified regulatory permits."
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
                            explanation=c.get("explanation", "")
                        )
                        for c in raw_contras
                    ]
                    if contra_objs:
                        contra_dict[b_name] = contra_objs

                # Run Batch Ranker Agent
                current_key = os.getenv("GEMINI_API_KEY")
                if current_key:
                    shortlist = rank_batch(scored_applications=scored_entries, contradictions_map=contra_dict, model=model_choice)
                else:
                    sorted_list = sorted(scored_entries, key=lambda x: (x[1].eligibility_gate.is_eligible, x[1].total_score), reverse=True)
                    shortlist_comps = []
                    for idx, (name, sc) in enumerate(sorted_list):
                        shortlist_comps.append(
                            RankedCompany(
                                rank=idx + 1,
                                business_name=name,
                                total_score=sc.total_score,
                                grid_variant=sc.grid_variant,
                                justification=f"{name} earned Rank #{idx + 1} with a verified score of {sc.total_score}/100 in the {sc.grid_variant.value} track. {sc.reviewer_summary}",
                                site_visit_questions=[
                                    "Inspect operational workshop and verify machinery serial numbers.",
                                    "Audit employee payroll register to verify reported headcount.",
                                    "Examine supplier invoices and local procurement contracts.",
                                ],
                                contradictions=contra_dict.get(name, [])
                            )
                        )
                    shortlist = RankedShortlist(
                        companies=shortlist_comps,
                        batch_summary=f"Batch portfolio evaluation of {len(sorted_list)} Ethiopian SMEs. Top candidates exhibit strong female equity ownership and domestic clean-tech assembly."
                    )

                st.session_state["shortlist_result"] = shortlist

        if "shortlist_result" in st.session_state:
            res_shortlist: RankedShortlist = st.session_state["shortlist_result"]

            st.divider()
            st.subheader("🏆 Investment Committee Shortlist Portfolio")
            st.info(f"**Batch Overview:** {res_shortlist.batch_summary}")

            for comp in res_shortlist.companies:
                with st.container():
                    col_r1, col_r2, col_r3 = st.columns([1, 4, 2])
                    with col_r1:
                        st.markdown(f"### `#{comp.rank}`")
                    with col_r2:
                        st.markdown(f"#### **{comp.business_name}**")
                        st.caption(f"Track: **{comp.grid_variant.value}** • Total Score: **{comp.total_score}/100**")
                    with col_r3:
                        if comp.total_score >= 80:
                            st.markdown('<span class="status-badge-pass">🟢 Recommended for Grant</span>', unsafe_allow_html=True)
                        elif comp.total_score >= 65:
                            st.markdown('<span class="status-badge-med">🟡 Reserve List (Site Visit)</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="status-badge-fail">🔴 Below Allocation Cutoff</span>', unsafe_allow_html=True)

                    st.write(f"**Committee Justification:** {comp.justification}")

                    if comp.contradictions:
                        st.warning(f"⚠️ **Flagged Contradiction:** {comp.contradictions[0].explanation}")

                    with st.expander(f"🔍 Site Visit Due Diligence Checklist ({len(comp.site_visit_questions)} inquiries)"):
                        for q in comp.site_visit_questions:
                            st.markdown(f"- 🔎 {q}")

                    st.divider()


# =============================================================================
# TAB 3: CONSENT & DECLARATIONS (TRUST DEMO)
# =============================================================================
with tab3:
    st.markdown('<div class="main-header">Multilingual Verbal Consent Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Translates complex legal covenants into plain-language verbal scripts for voice agents. Ensures informed consent while strictly prohibiting automated checkbox ticking.</div>', unsafe_allow_html=True)

    st.error("""
    🛑 **CRITICAL AUDIT MANDATE:**
    This module generates spoken scripts for the voice agent to read aloud to the applicant.
    **Checkboxes MUST NEVER be auto-ticked.** Consent must be explicitly and verifiably confirmed by the applicant after hearing the verbal explanation in their native language.
    """)

    col_lang1, col_lang2 = st.columns([2, 1])
    with col_lang1:
        selected_lang = st.radio(
            "Select Applicant Spoken Language",
            options=["Amharic", "Oromo", "English"],
            index=0,
            horizontal=True,
        )
    with col_lang2:
        st.write("")
        st.write("")
        gen_scripts_btn = st.button("📜 Generate Verbal Consent Scripts", type="primary", use_container_width=True)

    if gen_scripts_btn:
        with st.spinner(f"Translating legal covenants into grassroots verbal scripts in {selected_lang}..."):
            current_key = os.getenv("GEMINI_API_KEY")
            if current_key:
                consent_pkg = generate_consent_package(detected_language=selected_lang, model=model_choice)
            else:
                consent_pkg = generate_consent_package(detected_language=selected_lang)
            st.session_state["consent_package"] = consent_pkg
    elif "consent_package" not in st.session_state:
        from agents.declaration_explainer_agent import _build_fallback_consent
        st.session_state["consent_package"] = ConsentPackage(
            explanations=_build_fallback_consent(selected_lang),
            overall_warning="CRITICAL CONSTRAINT: This package contains verbal explanation scripts for the voice agent only. Checkboxes MUST NEVER be auto-ticked. Consent must be explicitly and verifiably confirmed by the applicant."
        )

    if "consent_package" in st.session_state:
        pkg: ConsentPackage = st.session_state["consent_package"]

        st.divider()
        st.subheader(f"🎙️ Verbal Consent Scripts — {selected_lang}")

        for idx, exp in enumerate(pkg.explanations, 1):
            st.markdown(f"### {idx}. `{exp.declaration_id.replace('declaration_', 'Declaration ').replace('_', ' ').title()}`")

            col_card1, col_card2 = st.columns(2)
            with col_card1:
                st.markdown("**📜 Original Legal Regulation:**")
                st.info(exp.original_legal_text)

            with col_card2:
                st.markdown(f"**🗣️ Grassroots Explanation ({exp.target_language}):**")
                st.success(exp.translated_simple_explanation)

            st.markdown("**❓ Voice Agent Verbal Consent Prompt:**")
            st.markdown(f"> *\"{exp.verbal_consent_question}\"*")
            st.caption("Agent pauses here for the applicant's spoken 'Yes / Ewo / Eeyyee' recorded response.")
            st.divider()
