"""
Browser Text-to-Speech (TTS) Component using Web Speech API (window.speechSynthesis).
Enables the AI interviewer to speak questions aloud with an interactive audio replay button.
"""

import html
import json
import streamlit.components.v1 as components


def speak_question(
    text: str,
    lang: str = "en",
    autoplay: bool = False,
    height: int = 44,
):
    """
    Renders an HTML5 / Web Speech API audio control that speaks the given question text.

    Args:
        text: The text to be spoken aloud.
        lang: Target language code ('en', 'am', 'om').
        autoplay: Whether to trigger speech synthesis immediately on component load.
        height: Component height in pixels.
    """
    if not text:
        return

    js_text = json.dumps(text)
    safe_lang = json.dumps(lang)
    auto_trigger = "window.addEventListener('load', function() { setTimeout(speak, 300); });" if autoplay else ""

    html_code = f"""
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
                padding: 2px 0;
                background-color: transparent;
                display: flex;
                align-items: center;
            }}
            .tts-btn {{
                background: linear-gradient(135deg, #0F766E 0%, #0D9488 100%);
                color: #FFFFFF;
                border: none;
                border-radius: 20px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
                transition: all 0.15s ease;
            }}
            .tts-btn:hover {{
                background: linear-gradient(135deg, #0D9488 0%, #14B8A6 100%);
                transform: translateY(-1px);
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.18);
            }}
            .tts-btn:active {{
                transform: translateY(0);
            }}
            .tts-status {{
                font-size: 11px;
                color: #64748B;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <button class="tts-btn" onclick="speak()" title="Listen to question audio">
            <span>🔊</span>
            <span>Read Question Aloud</span>
        </button>
        <span id="tts-feedback" class="tts-status"></span>

        <script>
            var textToSpeak = {js_text};
            var targetLang = {safe_lang};

            function speak() {{
                try {{
                    if (!('speechSynthesis' in window)) {{
                        document.getElementById('tts-feedback').innerText = "TTS not supported in this browser";
                        return;
                    }}

                    window.speechSynthesis.cancel();
                    var utterance = new SpeechSynthesisUtterance(textToSpeak);
                    utterance.rate = 0.92;
                    utterance.pitch = 1.0;

                    var voices = window.speechSynthesis.getVoices();
                    for (var i = 0; i < voices.length; i++) {{
                        if (voices[i].lang && voices[i].lang.toLowerCase().indexOf(targetLang.toLowerCase()) === 0) {{
                            utterance.voice = voices[i];
                            break;
                        }}
                    }}

                    utterance.onstart = function() {{
                        document.getElementById('tts-feedback').innerText = "Speaking...";
                    }};
                    utterance.onend = function() {{
                        document.getElementById('tts-feedback').innerText = "";
                    }};
                    utterance.onerror = function(e) {{
                        document.getElementById('tts-feedback').innerText = "";
                    }};

                    window.speechSynthesis.speak(utterance);
                }} catch (err) {{
                    console.warn("SpeechSynthesis error:", err);
                }}
            }}

            {auto_trigger}
        </script>
    </body>
    </html>
    """

    components.html(html_code, height=height, scrolling=False)
