"""
Pulsing Waveform Component for TeraGrant Agent.
Renders an animated Siri-style CSS audio waveform indicator (equalizer bars)
that dynamically animates when the AI is actively listening or transcribing.
"""

import streamlit.components.v1 as components


def render_heartbeat(is_active: bool = False, height: int = 70):
    """
    Renders a Siri-style pulsing audio waveform component.

    Args:
        is_active: True if the microphone is recording or the agent is actively processing.
        height: Component height in pixels.
    """
    status_text = "🎙️ AI Listening & Transcribing Live..." if is_active else "⚪ AI Standby • Drop voice note or start speaking"
    status_color = "#10B981" if is_active else "#64748B"
    bg_color = "#F0FDF4" if is_active else "#F8FAFC"
    border_color = "#86EFAC" if is_active else "#E2E8F0"

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
            .waveform-card {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                background-color: {bg_color};
                border: 1.5px solid {border_color};
                border-radius: 10px;
                padding: 8px 16px;
                gap: 16px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                transition: all 0.3s ease;
            }}
            .status-label {{
                font-size: 12px;
                font-weight: 600;
                color: {status_color};
                display: flex;
                align-items: center;
                gap: 6px;
            }}
            .bars-container {{
                display: flex;
                align-items: center;
                gap: 4px;
                height: 24px;
            }}
            .bar {{
                width: 3.5px;
                border-radius: 4px;
                background: linear-gradient(180deg, #3B82F6 0%, #10B981 100%);
                height: {'16px' if is_active else '5px'};
                opacity: {'1' if is_active else '0.4'};
                animation: {'pulse-bar 0.8s ease-in-out infinite alternate' if is_active else 'none'};
                transform-origin: bottom;
            }}
            .bar:nth-child(1) {{ animation-delay: 0.1s; height: {'18px' if is_active else '6px'}; }}
            .bar:nth-child(2) {{ animation-delay: 0.3s; height: {'24px' if is_active else '8px'}; }}
            .bar:nth-child(3) {{ animation-delay: 0.5s; height: {'14px' if is_active else '4px'}; }}
            .bar:nth-child(4) {{ animation-delay: 0.2s; height: {'22px' if is_active else '7px'}; }}
            .bar:nth-child(5) {{ animation-delay: 0.4s; height: {'16px' if is_active else '5px'}; }}

            @keyframes pulse-bar {{
                0% {{
                    transform: scaleY(0.25);
                }}
                50% {{
                    transform: scaleY(1.0);
                }}
                100% {{
                    transform: scaleY(0.4);
                }}
            }}
        </style>
    </head>
    <body>
        <div class="waveform-card">
            <div class="status-label">{status_text}</div>
            <div class="bars-container">
                <div class="bar"></div>
                <div class="bar"></div>
                <div class="bar"></div>
                <div class="bar"></div>
                <div class="bar"></div>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(html_content, height=height, scrolling=False)
