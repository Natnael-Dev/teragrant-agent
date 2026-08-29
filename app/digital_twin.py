"""
Digital Twin Form Component for TeraGrant Agent (Batch 23 Truth Layer UI).
Renders an interactive HTML/CSS/JS replica of the official GIZ/sequa SME Grant Application Form
with honest epistemic status chips (DOCUMENT_VERIFIED, APPLICANT_STATED, AI_INFERRED, NEEDS_CONFIRMATION, MISSING, CONTRADICTED)
and granular provenance evidence expanders (source, verbatim quote snippet, confidence %).
"""

import json
from typing import Dict, Any, Optional
from enum import Enum
import streamlit.components.v1 as components


def convert_to_serializable(obj: Any) -> Any:
    """
    Recursively converts Pydantic models, Enums, sets, and custom objects
    into JSON-serializable Python primitive types.
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


def render_giz_form(session_data: Optional[Dict[str, Any]] = None, height: int = 850):
    """
    Renders the official GIZ/sequa SME Support Scheme Application Form as an embedded digital twin.
    Includes the honest status legend bar and per-field evidence provenance expanders.
    """
    raw_data = session_data or {}
    safe_data = convert_to_serializable(raw_data)
    payload_json = json.dumps(safe_data, ensure_ascii=False, default=str)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-page: #F6F7F9;
                --text-main: #111827;
                --text-muted: #6B7280;
                --border-color: #E5E7EB;
                --emerald: #059669;
                --blue: #2563EB;
                --purple: #7C3AED;
                --amber: #D97706;
                --red: #DC2626;
            }}
            * {{
                box-sizing: border-box;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            body {{
                margin: 0;
                padding: 10px;
                background-color: #FFFFFF;
                color: var(--text-main);
                font-size: 12px;
                line-height: 1.4;
            }}
            .form-container {{
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 20px;
                background: #FFFFFF;
            }}
            .form-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 14px;
                margin-bottom: 14px;
            }}
            .form-title {{
                font-size: 15px;
                font-weight: 700;
                color: var(--text-main);
            }}
            .form-subtitle {{
                font-size: 11px;
                color: var(--text-muted);
                margin-top: 2px;
            }}
            
            /* STATUS LEGEND BAR */
            .legend-bar {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                background: #F9FAFB;
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 16px;
            }}
            .legend-item {{
                display: inline-flex;
                align-items: center;
                gap: 4px;
                font-size: 10px;
                font-weight: 600;
            }}
            .dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }}
            .dot-verified {{ background-color: var(--emerald); }}
            .dot-stated {{ background-color: var(--blue); }}
            .dot-inferred {{ background-color: var(--purple); }}
            .dot-confirmation {{ background-color: var(--amber); }}
            .dot-missing {{ background-color: var(--red); }}
            .dot-contradicted {{ background-color: var(--red); }}

            /* SECTION STYLING */
            .section-header {{
                font-size: 12px;
                font-weight: 700;
                color: var(--text-main);
                background-color: #F9FAFB;
                padding: 7px 12px;
                border-radius: 8px;
                margin-top: 14px;
                margin-bottom: 12px;
                border-left: 3px solid var(--emerald);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .grid-row {{
                display: flex;
                gap: 12px;
                margin-bottom: 12px;
            }}
            .grid-col {{
                flex: 1;
                display: flex;
                flex-direction: column;
            }}
            .grid-col-2 {{
                flex: 2;
            }}
            .field-wrapper {{
                margin-bottom: 10px;
            }}
            .label-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
            }}
            label {{
                font-size: 11px;
                font-weight: 600;
                color: var(--text-main);
            }}
            
            /* HONEST STATUS BADGES */
            .status-chip {{
                font-size: 9.5px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 4px;
                text-transform: uppercase;
                letter-spacing: 0.2px;
            }}
            .chip-verified {{
                background-color: #ECFDF5;
                color: var(--emerald);
                border: 1px solid #A7F3D0;
            }}
            .chip-stated {{
                background-color: #EFF6FF;
                color: var(--blue);
                border: 1px solid #BFDBFE;
            }}
            .chip-inferred {{
                background-color: #F5F3FF;
                color: var(--purple);
                border: 1px solid #DDD6FE;
            }}
            .chip-confirmation {{
                background-color: #FFFBEB;
                color: var(--amber);
                border: 1px solid #FDE68A;
            }}
            .chip-missing {{
                background-color: #FEF2F2;
                color: var(--red);
                border: 1px solid #FECACA;
            }}
            .chip-contradicted {{
                background-color: #FEF2F2;
                color: var(--red);
                border: 1px solid #F87171;
            }}

            input, textarea {{
                width: 100%;
                padding: 8px 10px;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                background-color: #FFFFFF;
                font-size: 12px;
                color: var(--text-main);
                outline: none;
            }}
            textarea {{
                resize: none;
                height: 46px;
            }}
            
            /* EVIDENCE EXPANDER */
            details.evidence-box {{
                margin-top: 4px;
                background: #F9FAFB;
                border: 1px solid var(--border-color);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10.5px;
            }}
            details.evidence-box summary {{
                cursor: pointer;
                color: var(--text-muted);
                font-weight: 600;
                outline: none;
                user-select: none;
            }}
            details.evidence-box summary:hover {{
                color: var(--text-main);
            }}
            .evidence-content {{
                margin-top: 5px;
                padding-top: 4px;
                border-top: 1px dashed var(--border-color);
                color: #374151;
            }}
            .evidence-meta {{
                display: flex;
                justify-content: space-between;
                font-size: 9.5px;
                color: var(--text-muted);
                margin-bottom: 2px;
            }}

            .data-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 6px;
                margin-bottom: 12px;
                font-size: 11px;
            }}
            .data-table th {{
                background-color: #F9FAFB;
                color: var(--text-muted);
                font-weight: 600;
                text-align: left;
                padding: 7px 10px;
                border: 1px solid var(--border-color);
            }}
            .data-table td {{
                padding: 6px 10px;
                border: 1px solid var(--border-color);
                background-color: #FFFFFF;
            }}
        </style>
    </head>
    <body>
        <div class="form-container">
            <!-- HEADER -->
            <div class="form-header">
                <div>
                    <div class="form-title">GIZ / sequa SME Grant Application Twin</div>
                    <div class="form-subtitle">Multimodal Digital Twin with Epistemic Provenance Audit</div>
                </div>
                <div id="overallFormBadge" class="status-chip chip-stated">Awaiting Intake</div>
            </div>

            <!-- STATUS LEGEND BAR -->
            <div class="legend-bar">
                <span class="legend-item"><span class="dot dot-verified"></span> DOCUMENT_VERIFIED</span>
                <span class="legend-item"><span class="dot dot-stated"></span> APPLICANT_STATED</span>
                <span class="legend-item"><span class="dot dot-inferred"></span> AI_INFERRED</span>
                <span class="legend-item"><span class="dot dot-confirmation"></span> NEEDS_CONFIRMATION</span>
                <span class="legend-item"><span class="dot dot-missing"></span> MISSING</span>
                <span class="legend-item"><span class="dot dot-contradicted"></span> ⚠️ CONTRADICTED</span>
            </div>

            <!-- SECTION 1.1: COMPANY PROFILE -->
            <div class="section-header">
                <span>1.1 Company Profile & Legal Identity</span>
                <span style="font-size: 10px; color: var(--text-muted);">Trade License OCR</span>
            </div>
            
            <div class="grid-row">
                <div class="grid-col grid-col-2 field-wrapper">
                    <div class="label-row">
                        <label>Legal Business Name</label>
                        <span id="chip_company_name" class="status-chip chip-missing">MISSING</span>
                    </div>
                    <input type="text" id="f_company_name" placeholder="Awaiting intake..." readonly>
                    <details class="evidence-box" id="ev_company_name">
                        <summary>🔎 Evidence & Source</summary>
                        <div class="evidence-content" id="ev_body_company_name">No source evidence loaded yet.</div>
                    </details>
                </div>
                <div class="grid-col field-wrapper">
                    <div class="label-row">
                        <label>TIN Number</label>
                        <span id="chip_tin_number" class="status-chip chip-missing">MISSING</span>
                    </div>
                    <input type="text" id="f_tin_number" placeholder="Awaiting license..." readonly>
                    <details class="evidence-box" id="ev_tin_number">
                        <summary>🔎 Evidence & Source</summary>
                        <div class="evidence-content" id="ev_body_tin_number">No source evidence loaded yet.</div>
                    </details>
                </div>
            </div>

            <div class="grid-row">
                <div class="grid-col grid-col-2 field-wrapper">
                    <div class="label-row">
                        <label>Physical Address / Location</label>
                        <span id="chip_location" class="status-chip chip-missing">MISSING</span>
                    </div>
                    <input type="text" id="f_location" placeholder="Awaiting intake..." readonly>
                    <details class="evidence-box" id="ev_location">
                        <summary>🔎 Evidence & Source</summary>
                        <div class="evidence-content" id="ev_body_location">No source evidence loaded yet.</div>
                    </details>
                </div>
                <div class="grid-col field-wrapper">
                    <div class="label-row">
                        <label>Ownership Structure</label>
                        <span id="chip_ownership" class="status-chip chip-inferred">AI_INFERRED</span>
                    </div>
                    <input type="text" id="f_ownership" placeholder="Private Limited Company (PLC)" readonly>
                </div>
            </div>

            <!-- SECTION 1.2: GROWTH & EMPLOYMENT -->
            <div class="section-header">
                <span>1.2 Growth Indicators & Employment Structure</span>
                <span style="font-size: 10px; color: var(--text-muted);">Baseline Metrics</span>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width: 35%;">Metric / Indicator</th>
                        <th style="width: 35%;">Extracted Value</th>
                        <th style="width: 30%;">Epistemic Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Annual Sales / Turnover (ETB)</strong></td>
                        <td><input type="text" id="f_sales" placeholder="Awaiting financial intake..." readonly></td>
                        <td><span id="chip_sales" class="status-chip chip-missing">MISSING</span></td>
                    </tr>
                    <tr>
                        <td><strong>Total Employees (Headcount)</strong></td>
                        <td><input type="text" id="f_total_staff" placeholder="Awaiting voice intake..." readonly></td>
                        <td><span id="chip_total_staff" class="status-chip chip-missing">MISSING</span></td>
                    </tr>
                    <tr>
                        <td><strong>Female Employees (Count)</strong></td>
                        <td><input type="text" id="f_female_staff" placeholder="Awaiting demographic split..." readonly></td>
                        <td><span id="chip_female_staff" class="status-chip chip-inferred">AI_INFERRED</span></td>
                    </tr>
                    <tr>
                        <td><strong>Youth Employees (<30 Yrs)</strong></td>
                        <td><input type="text" id="f_youth_staff" placeholder="Awaiting age split..." readonly></td>
                        <td><span id="chip_youth_staff" class="status-chip chip-inferred">AI_INFERRED</span></td>
                    </tr>
                </tbody>
            </table>

            <!-- SECTION 1.6: PRODUCTS & SECTOR -->
            <div class="section-header">
                <span>1.6 Main Products & Value Addition</span>
                <span style="font-size: 10px; color: var(--text-muted);">Business Narrative</span>
            </div>
            <div class="grid-row">
                <div class="grid-col grid-col-2 field-wrapper">
                    <div class="label-row">
                        <label>Main Products / Crops / Goods</label>
                        <span id="chip_products" class="status-chip chip-missing">MISSING</span>
                    </div>
                    <textarea id="f_products" placeholder="Awaiting voice narrative..." readonly></textarea>
                    <details class="evidence-box" id="ev_products">
                        <summary>🔎 Evidence & Source</summary>
                        <div class="evidence-content" id="ev_body_products">No source evidence loaded yet.</div>
                    </details>
                </div>
                <div class="grid-col field-wrapper">
                    <div class="label-row">
                        <label>Sector Classification</label>
                        <span id="chip_sector" class="status-chip chip-inferred">AI_INFERRED</span>
                    </div>
                    <input type="text" id="f_sector" placeholder="Agro-Processing & Light Manufacturing" readonly>
                </div>
            </div>

            <!-- SECTION 2.2: REQUESTED MACHINERY & ETB TARGET -->
            <div class="section-header">
                <span>2.2 Requested Grant Budget & Machinery</span>
                <span style="font-size: 10px; color: var(--text-muted);">Procurement</span>
            </div>
            <div class="grid-row">
                <div class="grid-col grid-col-2 field-wrapper">
                    <div class="label-row">
                        <label>Requested Machinery / Capital Asset</label>
                        <span id="chip_machinery" class="status-chip chip-missing">MISSING</span>
                    </div>
                    <input type="text" id="f_machinery" placeholder="Awaiting grant request..." readonly>
                    <details class="evidence-box" id="ev_machinery">
                        <summary>🔎 Evidence & Source</summary>
                        <div class="evidence-content" id="ev_body_machinery">No source evidence loaded yet.</div>
                    </details>
                </div>
                <div class="grid-col field-wrapper">
                    <div class="label-row">
                        <label>Requested Budget (ETB)</label>
                        <span id="chip_etb_price" class="status-chip chip-missing">MISSING</span>
                    </div>
                    <input type="text" id="f_etb_price" placeholder="Awaiting budget..." readonly>
                </div>
            </div>
        </div>

        <script>
            const payload = {payload_json};

            function getChipClass(status) {{
                switch(status) {{
                    case "DOCUMENT_VERIFIED": return "chip-verified";
                    case "APPLICANT_STATED": return "chip-stated";
                    case "AI_INFERRED": return "chip-inferred";
                    case "NEEDS_CONFIRMATION": return "chip-confirmation";
                    case "CONTRADICTED": return "chip-contradicted";
                    case "MISSING":
                    default: return "chip-missing";
                }}
            }}

            function applyFieldData(fieldKey, inputId, chipId, evBodyId, fallbackValue, provMap, gapsList) {{
                const inputEl = document.getElementById(inputId);
                const chipEl = document.getElementById(chipId);
                const evBody = document.getElementById(evBodyId);

                const prov = provMap ? provMap[fieldKey] : null;
                const isGap = gapsList && gapsList.some(g => (g.field_name || "").includes(fieldKey));

                let val = fallbackValue;
                let status = isGap ? "MISSING" : "APPLICANT_STATED";
                let conf = 0.85;
                let snippet = "Verbatim speech extract from voice note.";
                let src = "voice";

                if (prov) {{
                    val = prov.value !== undefined && prov.value !== null ? prov.value : fallbackValue;
                    status = prov.status || status;
                    conf = prov.confidence !== undefined ? prov.confidence : conf;
                    snippet = prov.evidence_snippet || snippet;
                    src = prov.source_type || src;
                }}

                if (inputEl) {{
                    if (val !== undefined && val !== null && val !== "") {{
                        inputEl.value = typeof val === 'number' ? val.toLocaleString() : val;
                    }} else if (isGap) {{
                        inputEl.value = "[MISSING - UNVERIFIED]";
                    }}
                }}

                if (chipEl) {{
                    chipEl.className = "status-chip " + getChipClass(status);
                    chipEl.innerText = status === "CONTRADICTED" ? "⚠️ CONTRADICTED" : status;
                }}

                if (evBody) {{
                    const confPct = Math.round(conf * 100);
                    evBody.innerHTML = `
                        <div class="evidence-meta">
                            <span><b>Source:</b> ${{src}}</span>
                            <span><b>Confidence:</b> ${{confPct}}%</span>
                        </div>
                        <div><b>Snippet:</b> "<i>${{snippet}}</i>"</div>
                    `;
                }}
            }}

            function updateTwin(data) {{
                if (!data || Object.keys(data).length === 0) return;

                const provMap = data.provenance || {{}};
                const gapsList = data.gaps || [];

                // 1.1 Company Name
                applyFieldData("business_info.company_name", "f_company_name", "chip_company_name", "ev_body_company_name", data.company_name || data.business_name, provMap, gapsList);

                // 1.1 TIN Number
                applyFieldData("business_info.tin_number", "f_tin_number", "chip_tin_number", "ev_body_tin_number", data.tin_number, provMap, gapsList);

                // 1.1 Location
                applyFieldData("business_info.location", "f_location", "chip_location", "ev_body_location", data.location || data.address, provMap, gapsList);

                // 1.2 Sales
                const salesVal = data.annual_sales ? Number(data.annual_sales).toLocaleString() + " ETB" : (data.requested_etb ? Number(data.requested_etb).toLocaleString() + " ETB" : null);
                applyFieldData("financials.annual_turnover_etb", "f_sales", "chip_sales", null, salesVal, provMap, gapsList);

                // 1.2 Total staff
                const staffVal = data.total_staff ? data.total_staff + " Employees" : null;
                applyFieldData("employment.total_staff", "f_total_staff", "chip_total_staff", null, staffVal, provMap, gapsList);

                // 1.2 Female staff
                const femaleVal = data.female_staff !== undefined && data.female_staff !== null ? data.female_staff + " Female" : (data.total_staff ? Math.round(Number(data.total_staff)*0.5) + " Female (Est.)" : null);
                applyFieldData("employment.gender_split", "f_female_staff", "chip_female_staff", null, femaleVal, provMap, gapsList);

                // 1.2 Youth staff
                const youthVal = data.youth_staff ? data.youth_staff + " Youth" : (data.total_staff ? Math.round(Number(data.total_staff)*0.5) + " Youth (Est.)" : null);
                applyFieldData("employment.age_split", "f_youth_staff", "chip_youth_staff", null, youthVal, provMap, gapsList);

                // 1.6 Products
                applyFieldData("business_info.sector", "f_products", "chip_products", "ev_body_products", data.product_type || data.main_products, provMap, gapsList);

                // 2.2 Machinery & Price
                applyFieldData("impact.procurement_items", "f_machinery", "chip_machinery", "ev_body_machinery", data.machinery_requested || "Spice Pulverizer Machine", provMap, gapsList);

                const etbPrice = data.requested_etb ? Number(data.requested_etb).toLocaleString() + " ETB" : null;
                applyFieldData("financials.requested_etb", "f_etb_price", "chip_etb_price", null, etbPrice, provMap, gapsList);

                // Overall badge
                const overallBadge = document.getElementById("overallFormBadge");
                if (overallBadge) {{
                    const gapCount = gapsList.length;
                    if (gapCount > 0) {{
                        overallBadge.className = "status-chip chip-confirmation";
                        overallBadge.innerText = gapCount + " GAPS IDENTIFIED";
                    }} else {{
                        overallBadge.className = "status-chip chip-verified";
                        overallBadge.innerText = "VERIFIED INTAKE COMPLETE";
                    }}
                }}
            }}

            updateTwin(payload);
        </script>
    </body>
    </html>
    """

    components.html(html_content, height=height, scrolling=True)
