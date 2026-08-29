"""
Unit tests for Vision and Audio intake extractors.
Uses unittest.mock to mock Gemini API calls without external network dependencies.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from extractors.config import get_api_key, get_gemini_client, is_network_error, call_gemini_with_fallback, MODEL_FALLBACK_CHAIN
from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction
from extractors.vision_extractor import extract_license_data
from extractors.audio_extractor import extract_audio_story


# =========================================================================
# CONFIG TESTS
# =========================================================================

def test_config_api_key_missing():
    """Verify that get_api_key raises ValueError when environment variables are unset."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            get_api_key()
        assert "Gemini API key is not configured" in str(exc_info.value)


def test_config_api_key_found():
    """Verify that get_api_key retrieves the key from GEMINI_API_KEY or GOOGLE_API_KEY."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key-12345"}):
        assert get_api_key() == "test-gemini-key-12345"

    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-google-key-67890"}, clear=True):
        assert get_api_key() == "test-google-key-67890"


# =========================================================================
# VISION EXTRACTOR TESTS (MOCKED)
# =========================================================================

def test_extract_license_data_valid_mock():
    """Test vision extraction parsing valid OCR output from Gemini."""
    mock_license_json = json.dumps({
        "business_name": "Tana Agro-Processing PLC",
        "tin_number": "0098765432",
        "registration_date": "12/04/2015 E.C.",
        "owner_name": "Almaz Tadesse",
        "location": "Bahir Dar, Amhara Region",
        "is_legible": True,
        "extraction_notes": "Clean official trade license with visible revenue authority stamp."
    })

    # Create temporary dummy image file
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
        tmp_file.write(b"\xFF\xD8\xFF\xE0dummy_jpeg_header_content")
        tmp_path = tmp_file.name

    try:
        mock_response = MagicMock()
        mock_response.text = mock_license_json

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        result = extract_license_data(image_path=tmp_path, client=mock_client)

        assert isinstance(result, LicenseExtraction)
        assert result.business_name == "Tana Agro-Processing PLC"
        assert result.tin_number == "0098765432"
        assert result.registration_date == "12/04/2015 E.C."
        assert result.owner_name == "Almaz Tadesse"
        assert result.location == "Bahir Dar, Amhara Region"
        assert result.is_legible is True
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_extract_license_data_missing_fields_and_unreadable():
    """
    ANTI-HALLUCINATION TEST:
    Verify that unreadable or absent fields properly resolve to None rather than being hallucinated.
    """
    mock_blurry_json = json.dumps({
        "business_name": "Selam Honey Producers",
        "tin_number": None,
        "registration_date": None,
        "owner_name": None,
        "location": "Gondar",
        "is_legible": True,
        "extraction_notes": "TIN and Owner sections are obstructed by coffee stain."
    })

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_file.write(b"\x89PNG\r\n\x1a\ndummy_png_content")
        tmp_path = tmp_file.name

    try:
        mock_response = MagicMock()
        mock_response.text = mock_blurry_json

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        result = extract_license_data(image_path=tmp_path, client=mock_client)

        assert result.business_name == "Selam Honey Producers"
        assert result.tin_number is None
        assert result.owner_name is None
        assert result.location == "Gondar"
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_extract_license_file_not_found():
    """Verify that a non-existent image path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        extract_license_data(image_path="non_existent_file_path_12345.jpg")


# =========================================================================
# AUDIO EXTRACTOR TESTS (MOCKED)
# =========================================================================

def test_extract_audio_story_amharic_mock():
    """Test audio extraction parsing Amharic voice note transcript and facts."""
    mock_audio_json = json.dumps({
        "transcript": "ስሜ በቀለ ደረሰ እባላለሁ። በቢሾፍቱ የዶሮ እርባታ እና የዶሮ መኖ ማምረቻ አለን። በአሁኑ ወቅት 18 ሰራተኞች አሉን። በዓመት 2 ሚሊዮን ብር ገደማ ሽያጭ እናደርጋለን።",
        "detected_language": "Amharic",
        "business_name": "Bekele Poultry & Feed",
        "employee_count": 18,
        "product_type": "Poultry farming and livestock feed manufacturing",
        "location": "Bishoftu, Oromia",
        "financial_figures": ["2,000,000 ETB annual sales"],
        "impact_summary": "Poultry business with 18 employees seeking expansion funding for automated feeding systems."
    })

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        tmp_file.write(b"ID3\x03\x00\x00dummy_mp3_content")
        tmp_path = tmp_file.name

    try:
        mock_response = MagicMock()
        mock_response.text = mock_audio_json

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        result = extract_audio_story(audio_path=tmp_path, client=mock_client)

        assert isinstance(result, AudioTranscriptExtraction)
        assert result.detected_language == "Amharic"
        assert result.employee_count == 18
        assert "ዶሮ እርባታ" in result.transcript
        assert result.location == "Bishoftu, Oromia"
        assert len(result.financial_figures) == 1
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_extract_audio_story_afaan_oromo_mock():
    """Test audio extraction parsing Afaan Oromo voice note transcript and facts."""
    mock_audio_json = json.dumps({
        "transcript": "Maqaan koo Tolosaa jedhama. Nuti Oromiyaa keessatti buna qulqullina olaanaa qabu oomishee gabaaf dhiyeessina. Hojjettoota 30 qabna.",
        "detected_language": "Afaan Oromo",
        "business_name": "Tolosa Specialty Coffee",
        "employee_count": 30,
        "product_type": "Specialty export coffee processing",
        "location": "Jimma, Oromia",
        "financial_figures": ["5,000,000 ETB revenue target"],
        "impact_summary": "Specialty coffee washing station employing 30 workers in Jimma zone."
    })

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_file.write(b"RIFFdummy_wav_content")
        tmp_path = tmp_file.name

    try:
        mock_response = MagicMock()
        mock_response.text = mock_audio_json

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        result = extract_audio_story(audio_path=tmp_path, client=mock_client)

        assert isinstance(result, AudioTranscriptExtraction)
        assert result.detected_language == "Afaan Oromo"
        assert result.employee_count == 30
        assert "Maqaan koo Tolosaa" in result.transcript
    finally:
        if Path(tmp_path).exists():
            Path(tmp_path).unlink()


def test_extract_audio_file_not_found():
    """Verify that a non-existent audio path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        extract_audio_story(audio_path="non_existent_voice_note.mp3")


# =========================================================================
# NETWORK RESILIENCE & SMART FAILOVER TESTS
# =========================================================================

def test_client_timeout_http_options():
    """Verify that get_gemini_client configures the 30-second (30000ms) timeout cap."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("google.genai.Client") as mock_genai_client:
            get_gemini_client()
            assert mock_genai_client.called
            call_kwargs = mock_genai_client.call_args[1]
            assert "http_options" in call_kwargs
            assert call_kwargs["http_options"].timeout == 30000


def test_is_network_error_classification():
    """Verify classification of network vs API error types."""
    import socket
    import httpx

    # Network errors
    assert is_network_error(TimeoutError("Operation timed out")) is True
    assert is_network_error(ConnectionError("Connection reset by peer")) is True
    assert is_network_error(socket.timeout("Socket timed out")) is True
    assert is_network_error(OSError(10060, "WinError 10060 A connection attempt failed")) is True
    assert is_network_error(httpx.ConnectTimeout("Connect timeout")) is True
    assert is_network_error(Exception("WinError 10060 TCP connection timed out")) is True

    # Non-network API errors
    assert is_network_error(Exception("404 NOT_FOUND models/gemini-1.5-flash")) is False
    assert is_network_error(ValueError("Invalid JSON schema structure")) is False


def test_call_gemini_with_fallback_network_retry_and_fail_fast():
    """Verify that network errors retry the candidate model and eventually report failure across chain."""
    mock_client = MagicMock()
    # Simulate repeated network failure (e.g. WinError 10060)
    mock_client.models.generate_content.side_effect = ConnectionError("[WinError 10060] A connection attempt failed")

    with patch("time.sleep") as mock_sleep:
        with pytest.raises(RuntimeError) as exc_info:
            call_gemini_with_fallback(
                client=mock_client,
                model="gemini-1.5-flash",
                contents="test content",
                config=None,
            )

        assert "All models failed" in str(exc_info.value)
        assert mock_client.models.generate_content.call_count >= 2
        assert mock_sleep.called


def test_call_gemini_with_fallback_api_404_walks_chain():
    """Verify that API 404/model retired errors walk the fallback chain."""
    mock_client = MagicMock()
    success_resp = MagicMock()
    success_resp.text = '{"status": "ok"}'

    # First model returns 404, second model succeeds
    mock_client.models.generate_content.side_effect = [
        Exception("404 NOT_FOUND models/gemini-1.5-flash is not found"),
        success_resp
    ]

    resp, model_used = call_gemini_with_fallback(
        client=mock_client,
        model=None,
        contents="test content",
        config=None,
    )

    assert resp == success_resp
    assert model_used == MODEL_FALLBACK_CHAIN[1]
    assert mock_client.models.generate_content.call_count == 2


def test_call_gemini_with_fallback_surfaces_all_model_errors():
    """Verify that when all models fail, a JSON dict with each candidate's error is surfaced."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED Quota exceeded")

    with pytest.raises(RuntimeError) as exc_info:
        call_gemini_with_fallback(
            client=mock_client,
            model=None,
            contents="test content",
            config=None,
        )

    err_str = str(exc_info.value)
    assert "All models failed. Details:" in err_str
    assert "gemini-1.5-flash" in err_str
    assert "429 RESOURCE_EXHAUSTED" in err_str


