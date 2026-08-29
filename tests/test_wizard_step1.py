"""
Unit tests for Wizard Step 1 Pure Logic (Batch 26).
"""

from unittest.mock import patch, MagicMock
import pytest

from extractors.schemas import AudioTranscriptExtraction
from app.wizard_logic import build_fact_chips, applicant_display_name, transcribe_step1


def test_build_fact_chips_complete():
    audio = AudioTranscriptExtraction(
        transcript="I run Almaz Spice Mill with 8 workers in Bahir Dar producing berbere spices.",
        detected_language="English",
        business_name="Almaz Spice Mill",
        location="Bahir Dar",
        employee_count=8,
        product_type="Berbere Spices",
        financial_figures=["480,000 ETB annual sales"],
        impact_summary="Empowering local spice growers.",
    )
    chips = build_fact_chips(audio)
    assert any("🏢 Business: Almaz Spice Mill" in c for c in chips)
    assert any("📍 Location: Bahir Dar" in c for c in chips)
    assert any("👥 Staff: 8" in c for c in chips)
    assert any("👩 Women:" in c for c in chips)
    assert any("📦 Product: Berbere Spices" in c for c in chips)
    assert any("💰 Financials: 480,000 ETB" in c for c in chips)


def test_build_fact_chips_empty_and_partial():
    assert build_fact_chips(None) == []

    empty_audio = AudioTranscriptExtraction(
        transcript="Hello good morning.",
        detected_language="English",
    )
    chips = build_fact_chips(empty_audio)
    assert any("Language: English" in c for c in chips)
    assert not any("Staff:" in c for c in chips)


def test_applicant_display_name_resolution():
    assert applicant_display_name({}) == "New Applicant"
    assert applicant_display_name({"applicant_name": "Tigist Bekele"}) == "Application — Tigist Bekele"
    assert applicant_display_name({"digital_twin_data": {"company_name": "Gondar Sesame"}}) == "Application — Gondar Sesame"


def test_transcribe_step1_empty_bytes():
    res = transcribe_step1(b"too_short")
    assert res["transcript"] == ""
    assert res["error"] is not None
    assert res["error"]["type"] == "EMPTY_AUDIO"


@patch("app.wizard_logic.extract_audio_story")
def test_transcribe_step1_success(mock_extract):
    mock_extract.return_value = AudioTranscriptExtraction(
        transcript="My company is Selam Weaving in Hawassa with 10 staff.",
        detected_language="English",
        business_name="Selam Weaving",
        location="Hawassa",
        employee_count=10,
    )

    fake_audio = b"RIFF" + b"\x00" * 200
    res = transcribe_step1(audio_bytes=fake_audio, ext="mp3", lang="English")

    assert res["error"] is None
    assert "Selam Weaving" in res["transcript"]
    assert len(res["chips"]) >= 3
    assert any("🏢 Business: Selam Weaving" in c for c in res["chips"])
    assert any("👥 Staff: 10" in c for c in res["chips"])


@patch("app.wizard_logic.extract_audio_story")
def test_transcribe_step1_network_error(mock_extract):
    mock_extract.side_effect = ConnectionError("Failed to connect to host: googleapis.com")

    fake_audio = b"RIFF" + b"\x00" * 200
    res = transcribe_step1(audio_bytes=fake_audio, ext="wav")

    assert res["error"] is not None
    assert res["error"]["type"] == "NETWORK_ERROR"
    assert "hotspot" in res["error"]["advice"].lower()
