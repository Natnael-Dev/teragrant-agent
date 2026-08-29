"""
Smoke and Integration Tests for FastAPI Presentation-Layer Server (Batch 29F).
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.server import app, SESSION


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


def test_api_interview_answer_empty_returns_error_json(client):
    response = client.post("/api/interview/answer", data={"step_index": 0})
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "Empty answer" in data["message"]


def test_api_interview_answer_with_text_mocked_gemini(client):
    from schemas.interview_schema import AnswerExtraction
    with patch("app.server.extract_answer", return_value=AnswerExtraction(field_id="business_info.business_name", value="Almaz Spice Mill", confidence=0.95)):
        response = client.post("/api/interview/answer", data={
            "step_index": 0,
            "text": "My name is Almaz and my business is Almaz Spice Mill"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["extraction"]["value"] == "Almaz Spice Mill"


def test_reviewer_dashboard_renders_kpis_and_shortlist(client):
    response = client.get("/reviewer")
    assert response.status_code == 200
    assert "Portfolio Evaluation & Committee Defense" in response.text
    assert "Total Batch" in response.text


def test_evidence_library_renders(client):
    response = client.get("/evidence")
    assert response.status_code == 200
    assert "Multimodal Evidence Library" in response.text


def test_api_transcribe_empty_bytes_returns_error_json(client):
    # Empty audio upload
    response = client.post("/api/transcribe", files={"audio": ("empty.webm", b"", "audio/webm")})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["type"] == "EMPTY_AUDIO"


def test_api_process_and_export_endpoints(client):
    # Process
    res_proc = client.post("/api/process")
    assert res_proc.status_code == 200
    data_proc = res_proc.json()
    assert data_proc["status"] == "success"

    # Export
    res_exp = client.get("/api/export")
    assert res_exp.status_code == 200
    assert "application/json" in res_exp.headers["content-type"]
    assert "attachment" in res_exp.headers.get("content-disposition", "")
