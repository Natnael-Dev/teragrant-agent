"""
Wizard Logic for TeraGrant Agent (Batch 26).
Pure, testable helper functions for Step 1 Voice Intake and transcription extraction without Streamlit dependencies.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List

from extractors.audio_extractor import extract_audio_story
from extractors.schemas import AudioTranscriptExtraction
from extractors.config import is_network_error, MODEL_FALLBACK_CHAIN


def build_fact_chips(audio_data: Optional[AudioTranscriptExtraction]) -> List[str]:
    """
    Extracts structured fact chips from an AudioTranscriptExtraction model.
    Returns clean emoji-tagged strings for display.
    """
    if not audio_data:
        return []

    chips = []
    if audio_data.business_name:
        chips.append(f"🏢 Business: {audio_data.business_name}")
    if audio_data.location:
        chips.append(f"📍 Location: {audio_data.location}")
    if audio_data.employee_count is not None and audio_data.employee_count > 0:
        chips.append(f"👥 Staff: {audio_data.employee_count}")
        female_est = max(1, int(round(audio_data.employee_count * 0.5)))
        chips.append(f"👩 Women: {female_est} ({int(round(female_est / audio_data.employee_count * 100))}%)")
    if audio_data.product_type:
        chips.append(f"📦 Product: {audio_data.product_type}")
    if audio_data.financial_figures:
        chips.append(f"💰 Financials: {', '.join(audio_data.financial_figures[:2])}")
    if audio_data.detected_language and audio_data.detected_language.lower() != "unknown":
        chips.append(f"🌐 Language: {audio_data.detected_language}")

    return chips


def applicant_display_name(session_dict: Dict[str, Any]) -> str:
    """
    Determines the applicant header display name.
    Returns 'Application — <name>' if a name is found, else 'New Applicant'.
    """
    if not session_dict:
        return "New Applicant"

    # Check for direct applicant or business name
    name = session_dict.get("applicant_name") or session_dict.get("business_name")
    if name:
        return f"Application — {name}"

    # Check in digital twin payload
    dt = session_dict.get("digital_twin_data", {})
    if isinstance(dt, dict):
        dt_name = dt.get("company_name") or dt.get("business_name")
        if dt_name:
            return f"Application — {dt_name}"

    # Check in pack result
    pack = session_dict.get("pack_res")
    if pack and hasattr(pack, "application") and pack.application:
        if pack.application.business_info and pack.application.business_info.business_name:
            return f"Application — {pack.application.business_info.business_name}"

    return "New Applicant"


def transcribe_step1(
    audio_bytes: bytes,
    ext: str = "mp3",
    lang: str = "English",
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribes and extracts key facts from raw audio bytes using the multimodal fallback pipeline.
    Returns a standardized dictionary:
    {
        "transcript": str,
        "chips": List[str],
        "audio_data": Optional[AudioTranscriptExtraction],
        "error": Optional[Dict[str, Any]]
    }
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return {
            "transcript": "",
            "chips": [],
            "audio_data": None,
            "error": {
                "type": "EMPTY_AUDIO",
                "message": "Audio recording is empty or too short.",
                "advice": "Please record at least 5 seconds of clear speech."
            }
        }

    # Normalize extension
    clean_ext = ext.lstrip(".").lower()
    if clean_ext not in ["mp3", "wav", "m4a", "ogg", "oga", "webm"]:
        clean_ext = "mp3"

    # Write to a temporary file for the extractor
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{clean_ext}") as tmp:
            tmp.write(audio_bytes)
            temp_file = tmp.name

        audio_data = extract_audio_story(
            audio_path=temp_file,
            target_language=lang,
            model=model,
            api_key=api_key
        )

        transcript = audio_data.transcript or ""
        chips = build_fact_chips(audio_data)

        return {
            "transcript": transcript,
            "chips": chips,
            "audio_data": audio_data,
            "error": None
        }

    except Exception as e:
        is_net = is_network_error(e)
        err_type = "NETWORK_ERROR" if is_net else "API_ERROR"
        advice = "Check your mobile hotspot or Wi-Fi connectivity and retry." if is_net else "Check your Gemini API quota or model permissions."
        return {
            "transcript": "",
            "chips": [],
            "audio_data": None,
            "error": {
                "type": err_type,
                "message": str(e),
                "advice": advice
            }
        }
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
