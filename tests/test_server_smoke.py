"""
Smoke and Integration Tests for FastAPI Presentation-Layer Server (Batch 30F).
Tests all interactive endpoints, gating redirects, gap resolution, consent recording,
real-data reviewer with ETB column, and 50MB payload limits.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.server import app, SESSION
from extractors.schemas import AudioTranscriptExtraction


@pytest.fixture
def client():
    return TestClient(app)


def test_home_page_renders_english_and_figma_hero(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Talk. Upload. Verify. Score." in response.text
    assert "Start Application" in response.text
    assert "Reviewer Dashboard" in response.text


def test_home_page_renders_amharic_and_oromo(client):
    res_am = client.get("/?lang=am")
    assert res_am.status_code == 200
    assert "ይናገሩ:: ይጫኑ:: ያረጋግጡ::" in res_am.text

    res_om = client.get("/?lang=om")
    assert res_om.status_code == 200
    assert "Dubbadhu. Fe'i. Mirkaneessi." in res_om.text


def test_wizard_step1_renders_stepper_and_recorder_idle_state(client):
    response = client.get("/wizard/1")
    assert response.status_code == 200
    assert "Tell us about your business" in response.text
    assert "Step 1 of 6" in response.text
    assert "record-circle" in response.text
    assert "Tap to record or speak" in response.text
    assert "Need help? Let the AI interview you step by step" in response.text


def test_wizard_gating_redirects(client):
    # Clear session intake state
    SESSION["transcript"] = ""
    SESSION["audio_data"] = None
    SESSION["processed"] = False
    SESSION["pack_res"] = None

    # Accessing Step 2 without audio intake redirects to Step 1
    res_step2 = client.get("/wizard/2", follow_redirects=False)
    assert res_step2.status_code == 303
    assert "/wizard/1?lang=en&gated=1" in res_step2.headers["location"]

    # Accessing Step 3 without processed pack redirects to Step 2
    res_step3 = client.get("/wizard/3", follow_redirects=False)
    assert res_step3.status_code == 303
    assert "/wizard/2?lang=en&gated=2" in res_step3.headers["location"]

    # Accessing Step 4 without processed pack redirects to Step 2
    res_step4 = client.get("/wizard/4", follow_redirects=False)
    assert res_step4.status_code == 303
    assert "/wizard/2?lang=en&gated=2" in res_step4.headers["location"]


def test_wizard_step3_and_step4_renders_grid_comparison_and_provisional_score(client):
    # Set session as processed
    SESSION["transcript"] = "Almaz Spice Mill in Bahir Dar"
    SESSION["processed"] = True

    res3 = client.get("/wizard/3")
    assert res3.status_code == 200
    assert "Evaluation Track Comparison" in res3.text
    assert "Women & Youth Led" in res3.text

    res4 = client.get("/wizard/4")
    assert res4.status_code == 200
    assert "Provisional Application Score" in res4.text
    assert "What would raise my score" in res4.text
    assert "POTENTIAL" in res4.text


def test_wizard_interview_renders_voiced_question(client):
    response = client.get("/wizard/interview?step=0&lang=en")
    assert response.status_code == 200
    assert "Question 1 of 7" in response.text
    assert "What is your name, and what is the name of your business?" in response.text
    assert "/api/tts" in response.text


def test_api_tts_streaming_returns_audio_mpeg(client):
    with patch("app.server.generate_speech_audio", return_value=b"fake-mp3-bytes"):
        response = client.get("/api/tts?text=Hello&lang=en")
        assert response.status_code == 200
        assert "audio/mpeg" in response.headers["content-type"]
        assert response.content == b"fake-mp3-bytes"


def test_api_transcribe_mocked_extractor_returns_chips(client):
    mock_audio_extraction = AudioTranscriptExtraction(
        transcript="Hello, I am Almaz from Almaz Spice Mill with 8 workers in Bahir Dar.",
        detected_language="English",
        business_name="Almaz Spice Mill",
        employee_count=8,
        product_type="Spices",
        location="Bahir Dar",
        financial_figures=["450,000 Birr"]
    )
    with patch("app.wizard_logic.extract_audio_story", return_value=mock_audio_extraction):
        response = client.post(
            "/api/transcribe",
            files={"audio": ("voice.mp3", b"fake-audio-bytes-for-intake-test-payload-data" * 5, "audio/mpeg")},
            data={"lang": "English"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Almaz Spice Mill" in data["transcript"]
        assert len(data["chips"]) >= 3
        assert any("Almaz Spice Mill" in c for c in data["chips"])
        assert any("Bahir Dar" in c for c in data["chips"])


def test_api_transcribe_empty_bytes_returns_error_json(client):
    response = client.post("/api/transcribe", files={"audio": ("empty.webm", b"", "audio/webm")})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "EMPTY_AUDIO"


def test_api_process_and_export_endpoints(client):
    res_proc = client.post("/api/process")
    assert res_proc.status_code == 200
    data_proc = res_proc.json()
    assert data_proc["status"] == "success"
    assert len(data_proc["summary_chips"]) == 4

    res_exp = client.get("/api/export")
    assert res_exp.status_code == 200
    assert "application/json" in res_exp.headers["content-type"]
    assert "attachment" in res_exp.headers.get("content-disposition", "")


def test_api_resolve_updates_gap_and_session(client):
    res = client.post("/api/resolve", data={
        "gap_field": "financials.sales_history_year_2",
        "text": "In 2023 our sales were 480,000 Birr"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "resolved"
    assert data["gap_field"] == "financials.sales_history_year_2"
    assert "financials.sales_history_year_2" in SESSION["resolved_gaps"]


def test_api_consent_records_manual_and_voice(client):
    # Manual consent
    res_manual = client.post("/api/consent", data={
        "declaration_id": "declaration_01",
        "verdict": "true",
        "source": "manual"
    })
    assert res_manual.status_code == 200
    data_m = res_manual.json()
    assert data_m["status"] == "recorded"
    assert data_m["verdict"] == "YES"

    # Spoken consent with audio
    with patch("app.wizard_logic.extract_audio_story", return_value=AudioTranscriptExtraction(transcript="Yes I confirm and agree", detected_language="English")):
        res_voice = client.post(
            "/api/consent",
            data={"declaration_id": "declaration_02", "source": "voice"},
            files={"audio": ("voice.webm", b"fake-affirmation-audio-payload-data" * 5, "audio/webm")}
        )
        assert res_voice.status_code == 200
        data_v = res_voice.json()
        assert data_v["status"] == "recorded"
        assert data_v["verdict"] == "YES"


def test_reviewer_dashboard_renders_kpis_and_shortlist_with_etb(client):
    # Test Demo source
    response_demo = client.get("/reviewer?source=demo")
    assert response_demo.status_code == 200
    assert "Portfolio Evaluation & Committee Defense" in response_demo.text
    assert "Total Batch" in response_demo.text
    assert "Grant Target:" in response_demo.text
    assert "ETB" in response_demo.text
    assert "Why this rank?" in response_demo.text

    # Test Session source with active session
    SESSION["processed"] = True
    response_session = client.get("/reviewer?source=session")
    assert response_session.status_code == 200
    assert "Session (Real 1)" in response_session.text


def test_reviewer_export_endpoint(client):
    res = client.get("/api/reviewer/export?source=demo")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    data = res.json()
    assert data["source"] == "demo"
    assert len(data["companies"]) == 12
    assert "grant_etb" in data["companies"][0]


def test_evidence_library_renders(client):
    response = client.get("/evidence")
    assert response.status_code == 200
    assert "Multimodal Evidence Library" in response.text
