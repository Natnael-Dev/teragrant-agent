"""
TeraGrant Design System & Unified Theme (Batch 27).
Single source of truth for all CSS styles, tokens, and widget overrides.
"""

THEME_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Ethiopic:wght@400;500;600;700&display=swap');

    /* 1. Hide default Streamlit chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stDecoration"] {display: none;}

    /* 2. Global Page Styling */
    .stApp {
        background-color: #F6F7F9;
        font-family: 'Inter', 'Noto Sans Ethiopic', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #111827;
    }

    /* 3. Light Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #111827;
    }

    /* 4. Unified Button System (White secondary, Emerald primary, Hover states) */
    .stButton > button, [data-testid="stBaseButton-secondary"] {
        background: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #E5E7EB !important;
        min-height: 48px;
        border-radius: 10px;
        font-weight: 600;
        font-family: 'Inter', 'Noto Sans Ethiopic', sans-serif;
        transition: all 0.15s ease-in-out;
    }
    .stButton > button:hover, [data-testid="stBaseButton-secondary"]:hover {
        border-color: #059669 !important;
        color: #059669 !important;
        background: #F9FAFB !important;
    }
    .stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
        background-color: #059669 !important;
        border-color: #059669 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover {
        background-color: #047857 !important;
        border-color: #047857 !important;
        color: #FFFFFF !important;
    }
    .stButton > button:disabled, [data-testid="stBaseButton-secondary"]:disabled, [data-testid="stBaseButton-primary"]:disabled {
        background-color: #F3F4F6 !important;
        border-color: #E5E7EB !important;
        color: #9CA3AF !important;
        cursor: not-allowed !important;
    }

    /* 5. Clean Single-Border Cards (No card-in-card nesting) */
    .tg-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }

    /* 6. Top Bar Single Flex Row */
    .top-bar-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 0 16px 0;
        margin-bottom: 8px;
        border-bottom: 1px solid #E5E7EB;
    }
    .top-bar-title {
        font-size: 14px;
        font-weight: 700;
        color: #111827;
        text-align: center;
    }
    .top-bar-step {
        font-size: 12px;
        color: #6B7280;
        font-weight: 600;
        text-align: right;
    }

    /* 7. Stepper Navigation Row */
    .stepper-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }
    .step-node {
        font-size: 12px;
        color: #6B7280;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .step-node.active {
        color: #059669;
        font-weight: 700;
        border-bottom: 2px solid #059669;
        padding-bottom: 4px;
    }
    .step-node.completed {
        color: #059669;
        font-weight: 600;
    }

    /* 8. Language Switcher Pills */
    .lang-pill-container {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 12px auto 20px auto;
    }
    .lang-pill {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 11.5px;
        font-weight: 600;
        color: #4B5563;
        display: inline-block;
    }
    .lang-pill.active {
        background: #111827;
        color: #FFFFFF;
        border-color: #111827;
    }

    /* 9. Step 1 96px Red Pulsing Recording Circle & Waveform */
    .recorder-wrapper {
        text-align: center;
        margin: 16px auto 12px auto;
        max-width: 480px;
    }
    .record-circle-96 {
        width: 96px;
        height: 96px;
        border-radius: 50%;
        background: #DC2626;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-size: 38px;
        margin: 0 auto 12px auto;
        box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7);
        animation: pulse-ring 1.8s infinite;
    }
    @keyframes pulse-ring {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.7); }
        70% { transform: scale(1.04); box-shadow: 0 0 0 16px rgba(220, 38, 38, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
    }
    .wave-bars {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 4px;
        height: 20px;
        margin-bottom: 6px;
    }
    .wave-bar {
        width: 3px;
        background: #DC2626;
        border-radius: 2px;
        animation: wave 1.2s ease-in-out infinite alternate;
    }
    .wave-bar:nth-child(1) { height: 8px; animation-delay: 0.1s; }
    .wave-bar:nth-child(2) { height: 16px; animation-delay: 0.2s; }
    .wave-bar:nth-child(3) { height: 20px; animation-delay: 0.3s; }
    .wave-bar:nth-child(4) { height: 14px; animation-delay: 0.4s; }
    .wave-bar:nth-child(5) { height: 18px; animation-delay: 0.2s; }
    .wave-bar:nth-child(6) { height: 10px; animation-delay: 0.5s; }
    @keyframes wave {
        0% { transform: scaleY(0.4); }
        100% { transform: scaleY(1.0); }
    }

    /* 10. Native Widget Restyle (Audio input & File uploader) */
    [data-testid="stAudioInput"] {
        background: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 12px !important;
        padding: 6px 12px !important;
        margin: 0 auto !important;
        max-width: 480px !important;
    }
    [data-testid="stFileUploader"] {
        background: #FFFFFF !important;
        border-radius: 12px !important;
        padding: 8px !important;
    }
    [data-testid="stFileUploader"] section {
        border: 1px dashed #D1D5DB !important;
        border-radius: 12px !important;
        padding: 16px !important;
        background: #FAFAFA !important;
    }

    /* 11. WhatsApp-style Chat Bubble */
    .whatsapp-bubble {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #059669;
        border-radius: 12px;
        padding: 16px;
        margin: 16px auto;
        max-width: 580px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        text-align: left;
    }
    .whatsapp-bubble-title {
        font-size: 11px;
        font-weight: 700;
        color: #059669;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .whatsapp-transcript {
        font-size: 13px;
        color: #111827;
        line-height: 1.5;
        font-style: italic;
        margin-bottom: 12px;
    }
    .fact-chips-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }
    .fact-chip-pill {
        background: #F3F4F6;
        border: 1px solid #E5E7EB;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        color: #374151;
        font-weight: 600;
    }

    /* 12. Black Decorative Pill in Bottom Bar */
    .bottom-status-pill {
        background: #111827;
        color: #FFFFFF;
        border-radius: 24px;
        padding: 8px 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-size: 12px;
        font-weight: 600;
        margin: 0 auto;
        width: fit-content;
    }

    /* 13. Step 2 Upload Cards with Dashed Dropzones */
    .upload-card-container {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 1.5rem;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .upload-dropzone-box {
        border: 1px dashed #D1D5DB;
        border-radius: 12px;
        padding: 24px 16px;
        text-align: center;
        background: #FAFAFA;
        margin-top: 12px;
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    /* 14. Status Chips per Status Key */
    .chip {
        font-size: 10px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        text-transform: uppercase;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        letter-spacing: 0.2px;
    }
    .chip-verified     { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .chip-stated       { background: #EFF6FF; color: #2563EB; border: 1px solid #BFDBFE; }
    .chip-inferred     { background: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; }
    .chip-confirmation { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .chip-missing      { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .chip-contradicted { background: #FEF2F2; color: #DC2626; border: 1px solid #F87171; }

    /* 15. Home Step Cards */
    .home-step-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .home-step-icon {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        margin-bottom: 12px;
    }

    /* 16. Responsive Media Queries for Mobile/Tablet */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem 0.75rem 4rem 0.75rem !important;
        }
        .hero-title {
            font-size: 1.6rem !important;
        }
        .hero-subtitle {
            font-size: 0.95rem !important;
        }
    }
</style>
"""


def apply_theme():
    """Applies the single source of CSS theme to the Streamlit page."""
    import streamlit as st
    st.markdown(THEME_CSS, unsafe_allow_html=True)
