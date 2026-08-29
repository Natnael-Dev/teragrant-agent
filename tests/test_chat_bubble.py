"""
Unit tests for Chat Bubble UI component.
"""

from unittest.mock import patch
from app.chat_bubble_ui import render_chat_bubble
from extractors.schemas import AudioTranscriptExtraction


def test_render_chat_bubble_with_pydantic_model():
    sample_extraction = AudioTranscriptExtraction(
        transcript="We operate a spice processing enterprise in Bahir Dar with 8 employees.",
        detected_language="Amharic",
        business_name="Almaz Spice Mill",
        employee_count=8,
        product_type="Ground Spices",
        location="Bahir Dar",
        financial_figures=["450,000 Birr"],
        impact_summary="Spice processing cooperative."
    )

    with patch("streamlit.components.v1.html") as mock_html:
        render_chat_bubble(sample_extraction)
        assert mock_html.called
        html_arg = mock_html.call_args[0][0]
        assert "Almaz Spice Mill" in html_arg
        assert "Bahir Dar" in html_arg
        assert "8 Staff" in html_arg
        assert "Amharic" in html_arg
        assert "Ground Spices" in html_arg
        assert "450,000 Birr" in html_arg
        assert "tag-chip" in html_arg
        assert "chat-wrapper" in html_arg


def test_render_chat_bubble_with_dict():
    sample_dict = {
        "transcript": "Solar repair and parts assembly in Hawassa.",
        "detected_language": "English",
        "business_name": "Nahom Tech",
        "location": "Hawassa",
        "employee_count": 12,
        "product_type": "Charge Controllers",
        "financial_figures": ["850,000 Birr"],
        "impact_summary": "Clean tech assembly."
    }

    with patch("streamlit.components.v1.html") as mock_html:
        render_chat_bubble(sample_dict)
        assert mock_html.called
        html_arg = mock_html.call_args[0][0]
        assert "Nahom Tech" in html_arg
        assert "Hawassa" in html_arg
        assert "12 Staff" in html_arg


def test_render_chat_bubble_none():
    with patch("streamlit.components.v1.html") as mock_html:
        render_chat_bubble(None)
        assert not mock_html.called
