"""
Heartbeat EKG Animation Component for TeraGrant Agent.
Renders an animated SVG pulse line indicating whether the AI agent is actively listening,
extracting multimodal audio/vision inputs, or in an idle standby state.
"""

import streamlit.components.v1 as components


def render_heartbeat(is_active: bool = False, height: int = 75):
    """
    Renders an animated SVG EKG heartbeat status indicator.

    Args:
        is_active: True if the multimodal agent is actively processing/listening.
        height: Height of the component in pixels.
    """
    active_class = "pulse-active" if is_active else "pulse-idle"
    status_text = "🟢 Agent Active: Listening, Transcribing & Filling Form..." if is_active else "⚪ Agent Idle: Ready for Voice / Document Input"
    line_color = "#10B981" if is_active else "#94A3B8"
    glow_style = "filter: drop-shadow(0 0 6px #10B981);" if is_active else ""

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
                padding: 4px 10px;
                background-color: transparent;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .ekg-container {{
                display: flex;
                align-items: center;
                gap: 12px;
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 6px 14px;
            }}
            .ekg-status {{
                font-size: 12px;
                font-weight: 600;
                color: #334155;
                white-space: nowrap;
            }}
            .ekg-svg-wrap {{
                flex: 1;
                height: 38px;
                overflow: hidden;
                position: relative;
            }}
            svg {{
                width: 100%;
                height: 100%;
            }}
            .ekg-path {{
                stroke: {line_color};
                stroke-width: 2.5;
                stroke-linecap: round;
                stroke-linejoin: round;
                fill: none;
                {glow_style}
            }}
            .pulse-active .ekg-path {{
                stroke-dasharray: 600;
                stroke-dashoffset: 600;
                animation: ekg-draw 2.2s linear infinite;
            }}
            @keyframes ekg-draw {{
                0% {{
                    stroke-dashoffset: 600;
                }}
                100% {{
                    stroke-dashoffset: 0;
                }}
            }}
            .pulse-idle .ekg-path {{
                stroke-dasharray: none;
                opacity: 0.6;
            }}
        </style>
    </head>
    <body>
        <div class="ekg-container {active_class}">
            <div class="ekg-svg-wrap">
                <svg viewBox="0 0 500 60" preserveAspectRatio="none">
                    <path class="ekg-path" d="M0,30 L60,30 L75,10 L90,50 L105,25 L120,35 L135,30 L220,30 L235,10 L250,50 L265,25 L280,35 L295,30 L380,30 L395,10 L410,50 L425,25 L440,35 L455,30 L500,30" />
                </svg>
            </div>
            <div class="ekg-status">{status_text}</div>
        </div>
    </body>
    </html>
    """

    components.html(html_content, height=height, scrolling=False)
