"""
WhatsApp-style Live Chat Bubble Component for Audio Transcripts and Extracted Fact Chips.
Displays spoken business stories in real-time with an AI avatar, speech bubble triangle,
and pill-shaped entity tags.
"""

from typing import Optional, Union, Dict, Any
import html
import streamlit.components.v1 as components

from extractors.schemas import AudioTranscriptExtraction


def render_chat_bubble(
    transcript_data: Union[AudioTranscriptExtraction, Dict[str, Any]],
    height: Optional[int] = None,
):
    """
    Renders an iOS/WhatsApp-style chat bubble containing the raw audio transcript
    and pill-shaped chips for extracted facts.

    Args:
        transcript_data: AudioTranscriptExtraction object or equivalent dict.
        height: Optional height override for Streamlit iframe.
    """
    if not transcript_data:
        return

    # Normalize data extraction
    if isinstance(transcript_data, dict):
        transcript = transcript_data.get("transcript", "")
        language = transcript_data.get("detected_language") or "Detected Audio"
        business_name = transcript_data.get("business_name")
        location = transcript_data.get("location")
        employee_count = transcript_data.get("employee_count")
        product_type = transcript_data.get("product_type")
        financials = transcript_data.get("financial_figures") or []
        impact_summary = transcript_data.get("impact_summary")
    else:
        transcript = transcript_data.transcript or ""
        language = transcript_data.detected_language or "Detected Audio"
        business_name = transcript_data.business_name
        location = transcript_data.location
        employee_count = transcript_data.employee_count
        product_type = transcript_data.product_type
        financials = transcript_data.financial_figures or []
        impact_summary = transcript_data.impact_summary

    # Sanitize strings for HTML safe rendering
    safe_transcript = html.escape(transcript)
    safe_language = html.escape(str(language))

    # Build chips
    chips_html = []
    if business_name:
        chips_html.append(f'<span class="tag-chip">🏢 {html.escape(str(business_name))}</span>')
    if location:
        chips_html.append(f'<span class="tag-chip">📍 {html.escape(str(location))}</span>')
    if employee_count is not None:
        chips_html.append(f'<span class="tag-chip">👥 {employee_count} Staff</span>')
    if product_type:
        chips_html.append(f'<span class="tag-chip">📦 {html.escape(str(product_type))}</span>')
    if financials:
        fin_str = financials[0] if isinstance(financials, list) and len(financials) > 0 else str(financials)
        chips_html.append(f'<span class="tag-chip">💰 {html.escape(str(fin_str))}</span>')
    if impact_summary:
        short_impact = (impact_summary[:35] + "...") if len(impact_summary) > 35 else impact_summary
        chips_html.append(f'<span class="tag-chip">🎯 {html.escape(short_impact)}</span>')
    if language:
        chips_html.append(f'<span class="tag-chip">🌐 {safe_language}</span>')

    chips_block = "".join(chips_html)

    # Dynamic height calculation to prevent ugly internal scrollbars
    if height is None:
        text_length = len(transcript)
        base_h = 130
        extra_text_h = (text_length // 50) * 18
        extra_chips_h = (len(chips_html) // 3) * 26
        height = max(140, min(320, base_h + extra_text_h + extra_chips_h))

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }}
            body {{
                margin: 0;
                padding: 4px 6px;
                background-color: transparent;
            }}
            .chat-wrapper {{
                display: flex;
                align-items: flex-start;
                gap: 10px;
                width: 100%;
            }}
            .avatar-container {{
                flex-shrink: 0;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background: linear-gradient(135deg, #10B981 0%, #047857 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 5px rgba(16, 185, 129, 0.3);
                font-size: 18px;
            }}
            .bubble-container {{
                position: relative;
                flex-grow: 1;
                background: #F1F5F9;
                border: 1px solid #CBD5E1;
                border-radius: 15px;
                padding: 10px 14px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            }}
            /* WhatsApp CSS Triangle */
            .bubble-container::before {{
                content: "";
                position: absolute;
                top: 12px;
                left: -7px;
                width: 0;
                height: 0;
                border-top: 6px solid transparent;
                border-bottom: 6px solid transparent;
                border-right: 7px solid #CBD5E1;
            }}
            .bubble-container::after {{
                content: "";
                position: absolute;
                top: 12px;
                left: -6px;
                width: 0;
                height: 0;
                border-top: 6px solid transparent;
                border-bottom: 6px solid transparent;
                border-right: 6px solid #F1F5F9;
            }}
            .bubble-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
            }}
            .bubble-title {{
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #0F766E;
            }}
            .bubble-time {{
                font-size: 10px;
                color: #64748B;
            }}
            .transcript-body {{
                font-size: 13px;
                line-height: 1.45;
                color: #1E293B;
                margin: 0 0 8px 0;
                word-wrap: break-word;
            }}
            .chips-wrapper {{
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-top: 6px;
                padding-top: 6px;
                border-top: 1px dashed #CBD5E1;
            }}
            .tag-chip {{
                background: #E2E8F0;
                color: #1E293B;
                padding: 3px 9px;
                border-radius: 20px;
                font-size: 11px;
                font-weight: 600;
                display: inline-flex;
                align-items: center;
                border: 1px solid #CBD5E1;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
            }}
        </style>
    </head>
    <body>
        <div class="chat-wrapper">
            <div class="avatar-container" title="TeraGrant Voice Intake Agent">
                🎙️
            </div>
            <div class="bubble-container">
                <div class="bubble-header">
                    <span class="bubble-title">Transcribed Voice Story ({safe_language})</span>
                    <span class="bubble-time">Live Intake</span>
                </div>
                <div class="transcript-body">
                    "{safe_transcript}"
                </div>
                <div class="chips-wrapper">
                    {chips_block}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html_content, height=height, scrolling=False)


def render_question_bubble(
    question_en: str,
    question_am: str,
    question_or: str,
    step_id: str = "S1",
    step_num: int = 1,
    total_steps: int = 7,
    height: int = 160,
):
    """
    Renders an AI interviewer speech bubble showing the question in English, Amharic, and Afaan Oromo.
    """
    safe_en = html.escape(question_en)
    safe_am = html.escape(question_am)
    safe_or = html.escape(question_or)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            body {{
                margin: 0;
                padding: 4px 6px;
                background-color: transparent;
            }}
            .chat-wrapper {{
                display: flex;
                align-items: flex-start;
                gap: 10px;
                width: 100%;
            }}
            .avatar-container {{
                flex-shrink: 0;
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background: linear-gradient(135deg, #059669 0%, #047857 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 6px rgba(5, 150, 105, 0.35);
                font-size: 18px;
            }}
            .bubble-container {{
                position: relative;
                flex-grow: 1;
                background: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 15px;
                padding: 10px 14px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
            }}
            /* Speech triangle */
            .bubble-container::before {{
                content: "";
                position: absolute;
                top: 12px;
                left: -7px;
                width: 0;
                height: 0;
                border-top: 6px solid transparent;
                border-bottom: 6px solid transparent;
                border-right: 7px solid #BBF7D0;
            }}
            .bubble-container::after {{
                content: "";
                position: absolute;
                top: 12px;
                left: -6px;
                width: 0;
                height: 0;
                border-top: 6px solid transparent;
                border-bottom: 6px solid transparent;
                border-right: 6px solid #F0FDF4;
            }}
            .bubble-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }}
            .bubble-title {{
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #047857;
            }}
            .step-badge {{
                background: #DCFCE7;
                color: #15803D;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 10.5px;
                font-weight: 700;
                border: 1px solid #86EFAC;
            }}
            .question-en {{
                font-size: 13.5px;
                font-weight: 600;
                color: #14532D;
                margin: 0 0 6px 0;
                line-height: 1.4;
            }}
            .question-translations {{
                border-top: 1px dashed #BBF7D0;
                padding-top: 5px;
                margin-top: 4px;
                display: flex;
                flex-direction: column;
                gap: 2px;
            }}
            .trans-line {{
                font-size: 12px;
                color: #374151;
                line-height: 1.35;
            }}
            .trans-label {{
                font-weight: 600;
                color: #059669;
                font-size: 10.5px;
            }}
        </style>
    </head>
    <body>
        <div class="chat-wrapper">
            <div class="avatar-container" title="AI Intake Interviewer">
                🤖
            </div>
            <div class="bubble-container">
                <div class="bubble-header">
                    <span class="bubble-title">TeraGrant AI Interviewer</span>
                    <span class="step-badge">{step_id} • Question {step_num}/{total_steps}</span>
                </div>
                <div class="question-en">
                    {safe_en}
                </div>
                <div class="question-translations">
                    <div class="trans-line"><span class="trans-label">AM:</span> {safe_am}</div>
                    <div class="trans-line"><span class="trans-label">OR:</span> {safe_or}</div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html_content, height=height, scrolling=False)

