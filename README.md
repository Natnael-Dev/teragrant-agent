# 🌱 TeraGrant Agent
### AI Builder Hackathon 2026 — Challenge 1: SME Grant Automation System

**TeraGrant Agent** is an end-to-end multi-agent AI system designed to solve the grant access bottleneck for micro, small, and medium enterprises (MSMEs) in Ethiopia and East Africa. 

It takes **unseen, unstructured inputs** (a photo of a paper trade license and a spoken voice note in Amharic, Afaan Oromo, or English) and transforms them into an **audit-grade, fundable grant application pack**, evaluates eligibility deterministically, scores across a 100-point matrix, detects cross-document discrepancies, and defends ranked portfolio shortlists for investment committees.

---

## 🎯 The Problem Statement

In emerging markets like Ethiopia, thousands of viable, high-impact small businesses—from rural honey cooperatives to urban clean-tech assembly workshops—fail to secure grant funding because:
1. **Intake Barrier**: Formal grant portals require complex English forms, organogram charts, and financial spreadsheets that exclude low-literacy or non-English-speaking entrepreneurs.
2. **Reviewer Overhead**: Grant reviewers are inundated with hundreds of applications, leading to arbitrary scoring, unvetted fraud/sanctions risks, and missed evaluation criteria.
3. **Data Gaps & Hallucinations**: Standard AI assistants frequently fabricate missing numbers (like TINs or sales history) rather than transparently flagging gaps for site-visit follow-up.
4. **Consent Ambiguity**: Checkbox declarations are often automatically clicked or agreed to without true grassroots comprehension in native languages.

---

## 🏗️ System Architecture

TeraGrant is architected across 6 modular, decoupled engineering layers:

```
                          ┌───────────────────────────┐
                          │   MULTIMODAL INTAKE       │
                          │ • Trade License Photo     │
                          │ • Multilingual Voice Note │
                          └─────────────┬─────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                             ▼
               ┌───────────────────┐         ┌───────────────────┐
               │ Vision OCR Agent  │         │ Audio Transcriber │
               │ (Anti-Hallucinate)│         │ (Amharic/Oromo/En)│
               └─────────┬─────────┘         └─────────┬─────────┘
                         │                             │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │ Intake Mapper & Gap Engine  │
                         │ • ApplicationSchema (1.1-2.6│
                         │ • ImpactProtocol (SDGs 1-17)│
                         │ • Explicit Gaps (High/Med)  │
                         └──────────────┬──────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────────┐
        ▼                               ▼                               ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│ Deterministic Gate    │   │ Forensic Contradiction│   │ 100-Point Scorer &    │
│ • Pure Python 15-Check│   │ • Math sum verification│   │   Grid Track Router   │
│ • 3 Instant Kills     │   │ • Semantic discrepancy│   │ • General SME (100pt) │
└───────────┬───────────┘   └───────────┬───────────┘   │ • Women/Youth (30pt)  │
            │                           │               │ • Innovation (30pt)   │
            └───────────────────────────┼───────────────┴───────────┬───────────┘
                                        ▼                           ▼
                         ┌─────────────────────────────┐┌───────────────────────┐
                         │ Portfolio Batch Ranker      ││ Multilingual Verbal   │
                         │ • Descending score sort     ││ Consent Engine        │
                         │ • Executive justifications  ││ • Never auto-tick     │
                         │ • 3 Site-visit questions    ││ • Spoken voice scripts│
                         └──────────────┬──────────────┘└───────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │ Streamlit UI Orchestrator   │
                         │ • 1. Applicant Intake Demo  │
                         │ • 2. Reviewer Ranker Demo   │
                         │ • 3. Verbal Consent Demo    │
                         └─────────────────────────────┘
```

---

## 🔑 Key Features & Design Innovations

### 1. Zero-Hallucination Multimodal Intake
- **Vision OCR**: Reads official Ethiopian commercial registration and trade licenses. If a TIN or date is smudged, it returns `null` and records a **Gap** rather than guessing digits.
- **Audio Voice Intake**: Faithfully transcribes spoken stories in **Amharic**, **Afaan Oromo**, or **English**, extracting verified headcount, crop/product types, and locations.

### 2. Deterministic Eligibility Gate (Pure Python)
- **15 Mandatory Declarations**: Default to `False` (zero auto-ticking).
- **3 Instant-Kill Exclusions**: Bankruptcy/insolvency, sanctions/criminal convictions, and prohibited sectors (weapons, illicit logging).
- Pure deterministic logic—guaranteeing 100% predictable compliance without LLM hallucination risk.

### 3. Adaptive 100-Point Scoring Matrix with 3 Grid Tracks
Standardized across 9 evaluation criteria with automatic multiplier reweighting:
- **General SME**: Balanced weights (Job Creation: 20, Financials: 15, Innovation: 15, Gender: 15, Supply Chain: 10, SDG: 10, Management: 5, Community: 5, Scalability: 5).
- **Women & Youth-Led**: Double weight on Gender/Youth Inclusion (30 pts).
- **Innovation & Tech**: Double weight on Innovation & Unique Features (30 pts).
- **Mandatory Gap Penalties**: Automatically deducts points when data gaps exist and cites: `"Score penalized due to missing data: [field_name]"`.

### 4. Forensic Contradiction Detection
- Runs pure Python math checks (e.g. gender split sum != declared headcount) + Gemini semantic cross-checks (e.g. license issued in 2024 vs 10-year operating claim).

### 5. Multilingual Verbal Consent Engine
- Translates legal covenants into warm, plain spoken scripts for rural workshop owners with low literacy.
- **Strict Constraint**: Checkboxes are never auto-ticked. Outputs only verbatim reading scripts for voice agents.

---

## 💻 Tech Stack

- **Language**: Python 3.13
- **Data Validation & Schemas**: Pydantic v2
- **AI / LLM Multimodal Foundation**: Google GenAI SDK (`google-genai` / Gemini 2.0 Flash)
- **Web Application UI**: Streamlit
- **Automated Testing Suite**: Pytest (34 unit & mock tests)

---

## 🚀 Installation & Local Setup

### 1. Clone & Enter Project Directory
```bash
git clone <repo-url>
cd "AI Hackaton"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Gemini API Key
Create a `.env` file at the root or set in your environment:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY="your_api_key_here"

# Linux / macOS
export GEMINI_API_KEY="your_api_key_here"
```

### 4. Launch the Streamlit Web Application
```bash
streamlit run app/streamlit_app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Automated Tests

Run the complete test suite verifying all 6 batches:
```bash
pytest tests/ -v
```

Expected output:
```
============================= 34 passed in 1.40s ==============================
```

---

## 📁 Repository Structure

```
├── app/
│   └── streamlit_app.py          # Master Streamlit UI orchestrator (3 Tabs)
├── agents/
│   ├── mapper_agent.py           # Multimodal synthesis & gap analysis
│   ├── eligibility_agent.py      # Deterministic pure-Python gatekeeper
│   ├── router_agent.py           # 3-track scoring grid router
│   ├── scorer_agent.py           # 100-point reviewer evaluation scorer
│   ├── contradiction_agent.py    # Forensic math & semantic discrepancy auditor
│   ├── batch_ranker_agent.py     # Deterministic portfolio sorting & defense
│   └── declaration_explainer_agent.py # Multilingual verbal consent scripts
├── extractors/
│   ├── vision_extractor.py       # Paper trade license OCR extractor
│   ├── audio_extractor.py        # Multilingual voice note transcriber
│   ├── config.py                 # Gemini client & key configuration
│   └── schemas.py                # Intermediate OCR & Audio Pydantic schemas
├── schemas/
│   ├── application_schema.py     # Master Sections 1.1-2.6 Application Schema
│   ├── impact_schema.py          # 17 SDGs & Verifiable Milestones Schema
│   ├── gap_schema.py             # Gap & ApplicationPack Schema
│   ├── scoring_schema.py         # 100-Pt Grid, Eligibility & Variant Schema
│   ├── reviewer_schema.py        # Contradictions & RankedShortlist Schema
│   └── consent_schema.py         # Grassroots Declaration Explanation Schema
├── data/
│   ├── mock_application.json     # Sample structured application payload
│   ├── mock_impact.json          # Sample structured impact protocol
│   └── sample_batch_12_applicants.json # Realistic 12-applicant portfolio
├── scripts/
│   └── live_extraction_demo.py   # Manual live CLI extraction test script
├── tests/
│   ├── test_schemas.py           # Batch 1 Schema validation tests (15 tests)
│   ├── test_extractors.py        # Batch 2 Extractor mock tests (8 tests)
│   ├── test_mapper.py            # Batch 3 Mapper & Gap tests (2 tests)
│   ├── test_scoring.py           # Batch 4 Scoring & Gate tests (5 tests)
│   └── test_batch5.py            # Batch 5 Contradictions, Ranker & Consent (4 tests)
├── requirements.txt              # Core project dependencies
└── README.md                     # Master documentation
```

---

## 🏆 Hackathon Evaluation Checklist

| Hackathon Requirement | Status | Implementation File |
| :--- | :---: | :--- |
| **Unseen Intake to Fundable Proposal** | ✅ Complete | [`extractors/`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/extractors/), [`agents/mapper_agent.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/agents/mapper_agent.py) |
| **Zero-Hallucination Gap Tracking** | ✅ Complete | [`schemas/gap_schema.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/schemas/gap_schema.py) |
| **Deterministic 15-Declaration Gate** | ✅ Complete | [`agents/eligibility_agent.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/agents/eligibility_agent.py) |
| **3-Track 100-Point Scoring Grid** | ✅ Complete | [`agents/scorer_agent.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/agents/scorer_agent.py), [`schemas/scoring_schema.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/schemas/scoring_schema.py) |
| **Forensic Contradiction Detection** | ✅ Complete | [`agents/contradiction_agent.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/agents/contradiction_agent.py) |
| **Batch in, Defended Ranking out** | ✅ Complete | [`agents/batch_ranker_agent.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/agents/batch_ranker_agent.py) |
| **Multilingual Grassroots Consent (Never Auto-Tick)** | ✅ Complete | [`agents/declaration_explainer_agent.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/agents/declaration_explainer_agent.py) |
| **Interactive UI for Live Judging** | ✅ Complete | [`app/streamlit_app.py`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/app/streamlit_app.py) |
| **Comprehensive Pytest Suite (34 Tests)** | ✅ Complete | [`tests/`](file:///c:/Users/HP/OneDrive/Desktop/AI%20Hackaton/tests/) |

---
*Built with ❤️ for the AI Builder Hackathon 2026.*
