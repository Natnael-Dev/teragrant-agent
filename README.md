# 🌱 TeraGrant Agent
### Autonomous Multimodal SME Grant Intake, Epistemic Provenance & Reviewer Defense System

> **TeraGrant converts voice and document evidence into a reviewer-ready application while preserving the provenance and uncertainty of every extracted field.**

[![Python Version](https://img.shields.io/badge/Python-3.13-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Google GenAI](https://img.shields.io/badge/Google_GenAI-Gemini_2.0_Flash-ff6f00?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLite Audit Trail](https://img.shields.io/badge/SQLite-Audit_Engine-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Status](https://img.shields.io/badge/Status-Audited_%26_Shippable-00c853?style=for-the-badge)](https://github.com/Natnael-Dev/teragrant-agent)

---

## 🎯 Product Principle & Problem Statement

In emerging markets such as Ethiopia and East Africa, thousands of viable, high-impact micro, small, and medium enterprises (MSMEs) are locked out of grant capital because formal applications demand lengthy English business plans, organograms, and complex tax schedules. Entrepreneurs who operate viable businesses—holding only paper trade licenses and speaking Amharic, Afaan Oromoo, or Tigrinya—struggle with bureaucratic barriers.

Generic AI solutions fail this challenge in the opposite direction: they are **confidently complete**. When an applicant leaves out their revenue or employee count, typical LLMs hallucinate reasonable-sounding numbers, silently paper over contradictions, or assign arbitrary numerical scores.

**TeraGrant solves this by enforcing strict epistemic honesty**:
- **Zero Fabrication**: If evidence is missing, the system records `None` and marks the field `MISSING`.
- **Forensic Contradiction Preservation**: If spoken audio claims 20 workers while workshop photos show 5, both claims are preserved and flagged as `CONTRADICTED`.
- **Epistemic Provenance**: Every number in the grant dossier links directly back to verbatim evidence and a cryptographic provenance state.

---

## 🏛️ Core Architecture: Code Owns the Numbers. AI Owns the Sentences.

TeraGrant enforces a strict architectural boundary between qualitative language understanding and quantitative decision-making: **"Code owns the numbers. AI owns the sentences."**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SCORING DECISION CONTRACT                             │
├───────────────────────────────────────┬─────────────────────────────────────────┤
│          AI RESPONSIBILITIES          │         PYTHON CODE RESPONSIBILITIES     │
│       ("AI OWNS THE SENTENCES")       │          ("CODE OWNS THE NUMBERS")      │
├───────────────────────────────────────┼─────────────────────────────────────────┤
│ • Transcribe multilingual audio       │ • Pure Python deterministic step-rules  │
│ • Extract raw facts from OCR text     │ • Calculate exact criterion points      │
│ • Detect semantic contradictions      │ • Enforce strict provenance score caps  │
│ • Synthesize qualitative narratives   │ • Evaluate pass/fail eligibility gates │
│ • Explain covenants in vernacular     │ • Execute portfolio sorting & ranking   │
│ ❌ FORBIDDEN: Awarding points         │ ❌ FORBIDDEN: Delegating math to LLMs   │
└───────────────────────────────────────┴─────────────────────────────────────────┘
```

All numerical calculations are executed by `agents/rule_engine.py`—a zero-dependency, deterministic Python rule engine governed by mathematical step-functions. The Gemini LLM is restricted exclusively to generating executive narrative summaries and conversational guidance. If the LLM goes offline or exhausts quota, the scoring engine functions identically, flagging the session with an honest fallback declaration.

---

## 🧾 The Provenance Ledger: 6 Epistemic States

Every extracted attribute inside the `ApplicationPack` is tied to an audit-grade provenance entry (`schemas/provenance_schema.py`). Rather than collapsing uncertain data into a single boolean, TeraGrant tracks 6 explicit epistemic states:

| Epistemic State | Description | Provenance Score Cap |
| :--- | :--- | :--- |
| `DOCUMENT_VERIFIED` | Extracted directly from official, legible documentation (e.g. OCR tax license, audited statements). | **100% of available points** |
| `APPLICANT_STATED` | Declared verbally by applicant via audio recording or guided interview, pending documentation. | **70% cap** |
| `AI_INFERRED` | Deduced by multimodal reasoning (e.g. machinery capacity inferred from workshop photo). | **50% cap** |
| `NEEDS_CONFIRMATION` | Ambiguous, low-confidence, or partially legible data requiring applicant verification. | **40% cap** |
| `CONTRADICTED` | Conflicting facts detected between independent multimodal sources (e.g. 20 audio staff vs 5 photo staff). | **0% (Requires manual review)** |
| `MISSING` | No evidence provided or documentation completely unreadable. No silent defaults allowed. | **0 points** |

---

## ⚖️ Scoring Methodology: ALPHAX Internal Prototype Grid (v1.0-prototype)

> [!IMPORTANT]
> **Prototype Framework Disclaimer**:
> The 9-criterion, 100-point scoring framework currently implemented in this repository is the **ALPHAX Internal Prototype Grid (v1.0-prototype)**. It was engineered as a comprehensive heuristic for the hackathon prototype. It is **NOT** the official SEQUA or GIZ evaluation matrix.

The prototype grid scores applications across 9 weighted criteria across 3 specialized SME tracks (`GENERAL_SME`, `WOMEN_AND_YOUTH_LED_SME`, and `INNOVATION_AND_TECH_SME`):

1. **Job Creation & Retention** (Up to 20 pts) — Evaluated against documented employee payroll bands.
2. **Gender & Youth Inclusion** (Up to 15 pts) — Female ownership percentage and youth workforce ratios.
3. **Innovation & Unique Features** (Up to 15 pts) — Operational capital machinery and technological milestones.
4. **Financial Viability & Turnover** (Up to 15 pts) — Documented annual sales history and valid TIN.
5. **Local Supply Chain Integration** (Up to 10 pts) — Domestic raw material sourcing and cooperative links.
6. **SDG & Environmental Compliance** (Up to 10 pts) — Alignment with SDG 2, 7, 8, 12, 13 and circular waste policies.
7. **Management Structure & Organogram** (Up to 5 pts) — Documented executive governance and operational leadership.
8. **Community & Social Impact** (Up to 5 pts) — Documented direct rural household beneficiaries.
9. **Scalability & Market Expansion** (Up to 5 pts) — Documented production capacity and facility headroom.

---

## 💾 Persistence & Audit Trail (SQLite + SQLAlchemy)

All processed application dossiers, criteria point breakdowns, and reviewer decisions persist to an on-disk SQLite database (`teragrant.db`) through SQLAlchemy ORM models (`app/models.py`):

- **Applications Ledger**: Stores applicant name, language, total score, grid variant, and JSON snapshots.
- **Evidence Audit Ledger**: Records multimodal source files, hash digests, file sizes, and MIME types.
- **Extracted Fields Ledger**: Persists each schema field path alongside its epistemic state and evidence snippet.
- **Criteria Scores Ledger**: Records point values, max points, rule names applied, and provenance caps.
- **Reviewer Audit Ledger**: Logs reviewer decisions (`RECOMMENDED_FOR_APPROVAL`, `REQUEST_FIELD_AUDIT`, `REJECTED`), reviewer name, decision timestamps, and committee defense notes.

---

## ⚡ Quickstart: Installation & Configuration

### Prerequisites
- Python 3.11, 3.12, or 3.13
- Git

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/Natnael-Dev/teragrant-agent.git
cd teragrant-agent

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional for Offline Replay)
Copy `.env.example` (or configure `.env`):
```env
# Optional for live AI extraction and narratives:
GEMINI_API_KEY=your_gemini_api_key_here
PORT=8000
```
*(Note: If no API key is set, the application automatically operates in deterministic offline fallback mode.)*

---

## 🚀 Running the Live System

To launch the FastAPI multimodal presentation server:

```bash
uvicorn app.server:app --port 8000 --reload
```

Open your browser and navigate to:
- **Applicant Intake Wizard**: [`http://localhost:8000`](http://localhost:8000)
- **Reviewer Committee Dashboard**: [`http://localhost:8000/reviewer`](http://localhost:8000/reviewer)
- **Interactive Evidence Library**: [`http://localhost:8000/evidence`](http://localhost:8000/evidence)
- **Health Check**: [`http://localhost:8000/healthz`](http://localhost:8000/healthz)

---

## 🧪 Running the Keyless Demo (Offline Replay)

You can verify the entire deterministic scoring pipeline **without any Google Gemini API key or network connection**:

```bash
python scripts/run_keyless_demo.py
```

### What this proves:
1. Loads the pre-recorded fixture from `data/fixtures/demo_extraction.json`.
2. Verifies 12 real epistemic provenance ledger records.
3. Evaluates all 9 criteria using pure Python step-functions from `agents/rule_engine.py`.
4. Outputs the exact rule applied and points awarded for every criterion.
5. Proves that the system is 100% reproducible and verifiable by an independent auditor.

---

## 🔬 Test Suite & Quality Assurance

Run the automated test suite covering deterministic scoring, rule engine precision, epistemic traversal, SQLite persistence, and shippable hygiene:

```bash
# Run shippable hygiene tests
pytest tests/test_shippable.py -v

# Run epistemic traversal & truthfulness tests
pytest tests/test_unverified_traversal.py -v

# Run full test suite (157+ tests)
pytest -q
```

---

## 📂 Repository Structure

```
teragrant-agent/
├── agents/                      # Specialized intelligent & deterministic agents
│   ├── rule_engine.py           # Pure Python deterministic scoring engine (Code owns numbers)
│   ├── scorer_agent.py          # Scorer orchestrator (Gemini LLM owns reviewer sentences)
│   ├── mapper_agent.py          # Multimodal synthesis & provenance ledger builder
│   ├── contradiction_agent.py   # Cross-modal contradiction & discrepancy detector
│   ├── eligibility_agent.py     # Deterministic 15-point compliance gate
│   ├── router_agent.py          # Automatic SME track routing engine
│   └── intake_orchestrator.py   # Concurrent intake processor (voice + vision)
├── app/                         # FastAPI presentation & persistence layer
│   ├── server.py                # Web application routes & export endpoints
│   ├── models.py                # SQLAlchemy ORM models (Audit trail & review state)
│   ├── database.py              # SQLite connection lifecycle & migrations
│   ├── templates/               # Hand-crafted HTML/CSS templates (EN, AM, OM)
│   └── static/                  # Responsive CSS, icons, and client interactions
├── data/                        # Sample data, test fixtures, and audio assets
│   └── fixtures/                # Pre-recorded deterministic fixtures for keyless demo
├── extractors/                  # Computer vision and audio extractors
│   ├── config.py                # Gemini model fallback chain & error handling
│   ├── vision_extractor.py      # Trade license OCR extractor
│   ├── workshop_extractor.py    # Workshop facility computer vision inspector
│   └── audio_extractor.py       # Multilingual voice note transcription & facts
├── schemas/                     # Strict Pydantic models & validation contracts
│   ├── application_schema.py    # Normalized MSME grant schema
│   ├── scoring_schema.py        # Criteria scores, audit records, and grid definitions
│   ├── provenance_schema.py     # 6 epistemic states and audit trail metadata
│   └── gap_schema.py            # ApplicationPack and explicit gap tracking
├── scripts/                     # Operational & demonstration utilities
│   └── run_keyless_demo.py      # Offline keyless replay script
└── tests/                       # Complete pytest regression & verification suite
```

---

## 📜 License
Developed for the **AI Builder Hackathon 2026** by Team ALPHAX. Licensed under the MIT License.
