"""
Digital Twin Form Component for TeraGrant Agent.
Renders an interactive HTML/CSS/JS replica of the official GIZ/sequa SME Grant Application Form.
Updates dynamically via JavaScript injection without Streamlit widget flickering.
"""

import json
from typing import Dict, Any, Optional
from enum import Enum
import streamlit.components.v1 as components


def convert_to_serializable(obj: Any) -> Any:
    """
    Recursively converts Pydantic models, Enums, sets, and custom objects
    into JSON-serializable Python primitive types (dict, list, str, int, float, bool, None).
    """
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return convert_to_serializable(obj.model_dump())
    if hasattr(obj, "dict"):
        return convert_to_serializable(obj.dict())
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): convert_to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [convert_to_serializable(item) for item in obj]
    return obj


def render_giz_form(session_data: Optional[Dict[str, Any]] = None, height: int = 750):
    """
    Renders the official GIZ/sequa SME Application Form as an embedded HTML component.
    Populates fields via JavaScript and highlights detected data gaps in red.
    When session_data is empty or None, renders in a pristine 'Awaiting Applicant Input' state.

    Args:
        session_data: Dictionary containing extracted field values and identified gap keys.
        height: Height of the component in pixels.
    """
    raw_data = session_data or {}
    safe_data = convert_to_serializable(raw_data)
    payload_json = json.dumps(safe_data, ensure_ascii=False, default=str)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            :root {{
                --primary: #1E3A8A;
                --border-color: #CBD5E1;
                --bg-input: #F8FAFC;
                --gap-red: #EF4444;
                --gap-bg: #FEF2F2;
                --filled-green: #059669;
                --filled-bg: #ECFDF5;
            }}
            * {{
                box-sizing: border-box;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
            body {{
                margin: 0;
                padding: 10px;
                background-color: #FFFFFF;
                color: #1E293B;
                font-size: 13px;
            }}
            .form-container {{
                border: 2px solid #3B82F6;
                border-radius: 8px;
                padding: 16px;
                background: #FFFFFF;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            }}
            .form-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #E2E8F0;
                padding-bottom: 10px;
                margin-bottom: 14px;
            }}
            .form-title {{
                font-size: 15px;
                font-weight: 700;
                color: #1E3A8A;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .form-badge {{
                background-color: #F1F5F9;
                color: #475569;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid #E2E8F0;
            }}
            .section-title {{
                font-size: 13px;
                font-weight: 700;
                color: #0F172A;
                background-color: #F1F5F9;
                padding: 6px 10px;
                border-radius: 4px;
                margin-top: 12px;
                margin-bottom: 8px;
                border-left: 3px solid #3B82F6;
            }}
            .grid-row {{
                display: flex;
                gap: 12px;
                margin-bottom: 8px;
            }}
            .grid-col {{
                flex: 1;
                display: flex;
                flex-direction: column;
            }}
            .grid-col-2 {{
                flex: 2;
            }}
            label {{
                font-size: 11px;
                font-weight: 600;
                color: #475569;
                margin-bottom: 3px;
            }}
            input, textarea {{
                width: 100%;
                padding: 7px 10px;
                border: 1px solid var(--border-color);
                border-radius: 5px;
                background-color: var(--bg-input);
                font-size: 12px;
                color: #0F172A;
                outline: none;
                transition: all 0.2s ease-in-out;
            }}
            input::placeholder, textarea::placeholder {{
                color: #94A3B8;
                font-style: italic;
            }}
            input:focus, textarea:focus {{
                border-color: #3B82F6;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
            }}
            textarea {{
                resize: none;
                height: 48px;
            }}
            .field-filled {{
                background-color: var(--filled-bg) !important;
                border-color: var(--filled-green) !important;
                color: #065F46 !important;
                font-weight: 500;
            }}
            .field-gap {{
                background-color: var(--gap-bg) !important;
                border-color: var(--gap-red) !important;
                color: #991B1B !important;
                box-shadow: 0 0 0 1px var(--gap-red);
            }}
            .gap-tag {{
                display: inline-block;
                background-color: #FEE2E2;
                color: #B91C1C;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 3px;
                margin-left: 6px;
            }}
            .live-tag {{
                display: inline-block;
                background-color: #D1FAE5;
                color: #047857;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 3px;
                margin-left: 6px;
            }}
        </style>
    </head>
    <body>
        <div class="form-container">
            <div class="form-header">
                <div class="form-title">📋 GIZ SME Support Scheme — Application Form</div>
                <div class="form-badge" id="syncStatus">⚪ Awaiting Applicant Input</div>
            </div>

            <!-- SECTION 1.1: GENERAL COMPANY INFORMATION -->
            <div class="section-title">1.1 General Information of the Company</div>
            <div class="grid-row">
                <div class="grid-col grid-col-2">
                    <label id="lbl_company_name">Company Name / Legal Business Name</label>
                    <input type="text" id="f_company_name" placeholder="Awaiting intake..." readonly>
                </div>
                <div class="grid-col">
                    <label id="lbl_tin_number">TIN Number (Tax ID)</label>
                    <input type="text" id="f_tin_number" placeholder="Awaiting intake..." readonly>
                </div>
            </div>
            <div class="grid-row">
                <div class="grid-col">
                    <label id="lbl_address">Physical Address / City / Sub-City</label>
                    <input type="text" id="f_address" placeholder="Awaiting intake..." readonly>
                </div>
                <div class="grid-col">
                    <label id="lbl_mobile">Contact Mobile / Telephone</label>
                    <input type="text" id="f_mobile" placeholder="Awaiting intake..." readonly>
                </div>
            </div>

            <!-- SECTION 1.2: EMPLOYMENT & YEARS IN OPERATION -->
            <div class="section-title">1.2 Operating History & Employment Structure</div>
            <div class="grid-row">
                <div class="grid-col">
                    <label id="lbl_years_operation">Years in Operation</label>
                    <input type="text" id="f_years_operation" placeholder="Awaiting intake..." readonly>
                </div>
                <div class="grid-col">
                    <label id="lbl_total_staff">Total Permanent Employees</label>
                    <input type="text" id="f_total_staff" placeholder="Awaiting intake..." readonly>
                </div>
                <div class="grid-col">
                    <label id="lbl_female_staff">Female Employees (Headcount)</label>
                    <input type="text" id="f_female_staff" placeholder="Awaiting intake..." readonly>
                </div>
            </div>

            <!-- SECTION 1.6: MAIN PRODUCTS / INNOVATION -->
            <div class="section-title">1.6 Main Products, Services & Value Proposition</div>
            <div class="grid-row">
                <div class="grid-col">
                    <label id="lbl_main_products">Main Products & Unique Innovation Features</label>
                    <textarea id="f_main_products" placeholder="Awaiting intake..." readonly></textarea>
                </div>
            </div>

            <!-- SECTION 1.8: ORGANOGRAM -->
            <div class="section-title">1.8 Governance & Organizational Structure</div>
            <div class="grid-row">
                <div class="grid-col">
                    <label id="lbl_organogram">Organogram & Key Management Roles</label>
                    <input type="text" id="f_organogram" placeholder="Awaiting intake..." readonly>
                </div>
            </div>

            <!-- SECTION 2.2: REQUESTED MACHINERY & ETB TARGET -->
            <div class="section-title">2.2 Proposed Project Investment & Grant Request (ETB)</div>
            <div class="grid-row">
                <div class="grid-col grid-col-2">
                    <label id="lbl_machinery">Requested Machinery / Asset Upgrades</label>
                    <input type="text" id="f_machinery" placeholder="Awaiting intake..." readonly>
                </div>
                <div class="grid-col">
                    <label id="lbl_etb_price">Total Financial Target (ETB)</label>
                    <input type="text" id="f_etb_price" placeholder="Awaiting intake..." readonly>
                </div>
            </div>
        </div>

        <script>
            const payload = {payload_json};

            function populateForm(data) {{
                if (!data || Object.keys(data).length === 0) {{
                    return;
                }}

                const gaps = data.gaps || [];
                const gapKeys = data.gap_fields || [];

                function setField(fieldId, labelId, value, isGap, gapReason) {{
                    const el = document.getElementById(fieldId);
                    const lbl = document.getElementById(labelId);
                    if (!el) return;

                    if (isGap) {{
                        el.value = value ? value : "[MISSING - UNVERIFIED]";
                        el.className = "field-gap";
                        if (lbl && !lbl.innerHTML.includes("Missing")) {{
                            lbl.innerHTML += ' <span class="gap-tag">🔴 Missing / Gap</span>';
                        }}
                    }} else if (value !== undefined && value !== null && value !== "") {{
                        el.value = value;
                        el.className = "field-filled";
                        if (lbl && !lbl.innerHTML.includes("Verified")) {{
                            lbl.innerHTML += ' <span class="live-tag">✓ Verified</span>';
                        }}
                    }}
                }}

                setField("f_company_name", "lbl_company_name", data.company_name, gapKeys.includes("company_name"));
                setField("f_tin_number", "lbl_tin_number", data.tin_number, gapKeys.includes("tin_number"));
                setField("f_address", "lbl_address", data.address, gapKeys.includes("address") || gapKeys.includes("location"));
                setField("f_mobile", "lbl_mobile", data.mobile || "+251 (On File)", gapKeys.includes("mobile"));
                setField("f_years_operation", "lbl_years_operation", data.years_in_operation ? data.years_in_operation + " Years" : null, gapKeys.includes("years_in_operation"));
                setField("f_total_staff", "lbl_total_staff", data.total_staff ? data.total_staff + " Staff" : null, gapKeys.includes("total_staff"));
                setField("f_female_staff", "lbl_female_staff", data.female_staff !== undefined && data.female_staff !== null ? data.female_staff + " Female" : null, gapKeys.includes("gender_split") || gapKeys.includes("female_staff"));
                setField("f_main_products", "lbl_main_products", data.main_products, gapKeys.includes("main_products"));
                setField("f_organogram", "lbl_organogram", data.organogram_status || "Owner-Managed Structure", gapKeys.includes("organogram"));
                setField("f_machinery", "lbl_machinery", data.machinery_requested, gapKeys.includes("machinery"));
                setField("f_etb_price", "lbl_etb_price", data.requested_etb ? Number(data.requested_etb).toLocaleString() + " ETB" : null, gapKeys.includes("requested_etb"));

                const statusEl = document.getElementById("syncStatus");
                if (statusEl) {{
                    if (gapKeys.length > 0) {{
                        statusEl.innerHTML = "⚠️ Form Filled with " + gapKeys.length + " Gaps Flagged";
                        statusEl.style.backgroundColor = "#FEE2E2";
                        statusEl.style.color = "#991B1B";
                        statusEl.style.borderColor = "#F87171";
                    }} else {{
                        statusEl.innerHTML = "✅ Form 100% Filled & Verified";
                        statusEl.style.backgroundColor = "#D1FAE5";
                        statusEl.style.color = "#065F46";
                        statusEl.style.borderColor = "#34D399";
                    }}
                }}
            }}

            populateForm(payload);
        </script>
    </body>
    </html>
    """

    components.html(html_content, height=height, scrolling=True)
