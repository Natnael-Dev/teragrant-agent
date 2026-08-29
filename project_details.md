# 🌱 TeraGrant Agent — Comprehensive System Architecture & Codebase Dossier
### AI Builder Hackathon 2026 — Challenge 1: SME Grant Automation System

---

## 📑 Table of Contents
1. [Executive Summary & Core Mission](#1-executive-summary--core-mission)
2. [End-to-End System Architecture](#2-end-to-end-system-architecture)
3. [Complete Repository Map & Codebase Inventory](#3-complete-repository-map--codebase-inventory)
4. [Master Data Schemas & Strict Validation Logic](#4-master-data-schemas--strict-validation-logic)
5. [Multimodal Extractor Layer](#5-multimodal-extractor-layer)
6. [API Resilience, Timeout Cap & Smart Error Failover](#6-api-resilience-timeout-cap--smart-error-failover)
7. [Multi-Agent Orchestration Layer](#7-multi-agent-orchestration-layer)
8. [Guided Conversational Interview State Machine](#8-guided-conversational-interview-state-machine)
9. [UI Component Engineering & Digital Twin Form](#9-ui-component-engineering--digital-twin-form)
10. [Click-by-Click User Interaction & Feature Flow Guide](#10-click-by-click-user-interaction--feature-flow-guide)
11. [Automated Test Suite & Quality Verification](#11-automated-test-suite--quality-verification)
12. [Installation, Configuration & Deployment Guide](#12-installation-configuration--deployment-guide)

---

## 1. Executive Summary & Core Mission

### 1.1 The Grassroots SME Grant Challenge
In emerging economies such as Ethiopia and across East Africa, thousands of viable, productive micro, small, and medium enterprises (MSMEs)—including spice millers in Sidama, organic honey cooperatives in Lake Tana, clean-tech solar refurbishers in Addis Ababa, and leather artisans in Entoto—are locked out of catalytic grant financing.

The fundamental barriers include:
1. **The Multimodal Intake Barrier**: Traditional grant portals demand multi-page PDF application forms, complex English narrative proposals, formal organogram charts, and spreadsheet financials. Grassroots entrepreneurs often operate informally, speak indigenous languages (Amharic, Afaan Oromo, Tigrinya), and hold paper registration certificates with physical rubber stamps.
2. **Reviewer Overhead & Inconsistent Evaluation**: Grant review committees are inundated with hundreds of unstructured applications. This results in manual review fatigue, arbitrary scoring variances, and missed evaluation criteria.
3. **AI Hallucination & Data Fabrication**: Standard generative AI models frequently hallucinate missing information (e.g., inventing 10-digit Tax Identification Numbers [TINs] or fabricating sales figures) rather than transparently flagging gaps for physical site-visit inspection.
4. **Consent Ambiguity & Automated Checkbox Abuse**: Checkbox declarations (e.g., anti-corruption, child labor prohibition) are routinely checked automatically by systems without ensuring genuine, plain-language comprehension by the applicant.

### 1.2 The TeraGrant Solution
**TeraGrant Agent** is an end-to-end multi-agent AI system built to automate the full lifecycle of SME grant ingestion, compliance verification, scoring, and portfolio ranking.

Key Capabilities:
- **Zero-Hallucination Multimodal Ingestion**: Ingests raw smartphone photos of paper trade licenses and spoken voice notes in **Amharic**, **Afaan Oromo**, or **English**. If data is unreadable or missing, the system strictly outputs `null` and creates explicit, prioritized **Gap** records.
- **Real-Time Interactive "Digital Twin"**: An embedded, reactive HTML/JS/CSS replica of the official GIZ/sequa SME Support Scheme application form that updates in real time as the AI listens to the applicant, highlighting verified fields in green and unverified data gaps in red.
- **7-Step Guided Trilingual Voice Interview**: An interactive state machine that walks the entrepreneur through 7 targeted questions with live audio recording, Web Speech API text-to-speech (TTS), and instant atomic fact extraction.
- **Deterministic 15-Declaration Eligibility Gate**: Pure Python business logic validating 15 mandatory compliance declarations and 3 instant-kill exclusion criteria (bankruptcy, fraud/sanctions, banned activities) without LLM unpredictability.
- **100-Point Adaptive Scoring Matrix with 3 Grid Tracks**: Automatically routes applicants into **General SME**, **Women & Youth-Led** (double weight on gender/youth inclusion: 30 pts), or **Innovation & Tech** (double weight on innovation: 30 pts) and enforces deterministic point penalties when data gaps exist.
- **Forensic Contradiction Detection**: Cross-checks mathematical sums (gender/age splits vs. total staff) in pure Python and runs deep semantic auditing using Google Gemini to catch timeline discrepancies (e.g., claiming 10 years of operations with a license issued 6 months ago).
- **Portfolio Batch Ranker & Executive Defense**: Ingests multi-applicant batches, executes deterministic score sorting, and generates committee justifications and 3 targeted site-visit due diligence questions per candidate.
- **Multilingual Verbal Consent Engine**: Translates complex legal covenants into plain-language spoken scripts for voice intake agents, enforcing a strict zero-automated-ticking constraint.

---

## 2. End-to-End System Architecture

```
                               ┌─────────────────────────────────────────┐
                               │       MULTIMODAL INTAKE STREAMS         │
                               │ • Paper Trade License Photo (.jpg/.png) │
                               │ • Workshop / Factory Photo (.jpg/.png)  │
                               │ • Spoken Voice Note (Amharic/Oromo/Eng) │
                               │ • Guided 7-Step Conversational Voice    │
                               └────────────────────┬────────────────────┘
                                                    │
                      ┌─────────────────────────────┴─────────────────────────────┐
                      ▼                                                           ▼
       ┌─────────────────────────────┐                             ┌─────────────────────────────┐
       │     Vision OCR Agent        │                             │  Multilingual Audio Agent   │
       │ (extractors/vision_extractor)│                             │ (extractors/audio_extractor)│
       │ • Zero-hallucination OCR    │                             │ • 2-Step Verbatim + Facts   │
       │ • Unreadable fields -> null │                             │ • Amharic / Oromo / English │
       └──────────────┬──────────────┘                             └──────────────┬──────────────┘
                      │                                                           │
                      │               ┌─────────────────────────────┐             │
                      │               │  Workshop Evaluator Agent   │             │
                      │               │(extractors/workshop_extractor)            │
                      │               │ • Machinery & Tool Presence │             │
                      │               │ • Worker Count & Safety Obs │             │
                      │               └──────────────┬──────────────┘             │
                      │                              │                            │
                      └──────────────────────────────┼────────────────────────────┘
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │   Intake & Gap Mapper Agent │
                                      │   (agents/mapper_agent.py)  │
                                      │ • ApplicationSchema (1.1-2.6│
                                      │ • ImpactProtocol (17 SDGs)  │
                                      │ • Explicit Gap Records (H/M)│
                                      └──────────────┬──────────────┘
                                                     │
         ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
         ▼                                           ▼                                           ▼
┌────────────────────────────────┐   ┌────────────────────────────────┐   ┌────────────────────────────────┐
│   Deterministic Gatekeeper     │   │  Forensic Contradiction Auditor│   │  Adaptive 100-Point Scorer &   │
│   (agents/eligibility_agent)   │   │  (agents/contradiction_agent)  │   │  Grid Variant Router Agent     │
│ • Pure Python 15-Declaration   │   │ • Mathematical Headcount Sums  │   │ (agents/scorer & router_agent) │
│ • 3 Instant-Kill Exclusions    │   │ • Photo Asset Cross-Checks     │   │ • 3 Tracks (General/Women/Tech)│
│ • Zero LLM Disqualification   │   │ • Gemini Semantic Discrepancy  │   │ • Mandatory Gap Deductions     │
└──────────────┬─────────────────┘   └───────────────┬────────────────┘   └────────────────┬───────────────┘
               │                                     │                                     │
               └─────────────────────────────────────┼─────────────────────────────────────┘
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │    Portfolio Batch Ranker   │
                                      │ (agents/batch_ranker_agent) │
                                      │ • Descending deterministic  │
                                      │ • Executive committee memo  │
                                      │ • 3 Site-visit questions    │
                                      └──────────────┬──────────────┘
                                                     │
                                                     ▼
                                      ┌─────────────────────────────┐
                                      │   Streamlit Web Platform    │
                                      │ • Tab 1: Live Digital Twin  │
                                      │ • Tab 2: Batch Ranker Demo  │
                                      │ • Tab 3: Grassroots Consent │
                                      └─────────────────────────────┘
```

---

## 3. Complete Repository Map & Codebase Inventory

Below is the directory structure and file index for the TeraGrant codebase:

```
AI Hackaton/
├── .env                                 # Environment file (stores GEMINI_API_KEY)
├── .gitignore                           # Git exclusion rules (__pycache__, temp files)
├── README.md                            # High-level hackathon summary documentation
├── requirements.txt                     # Core dependencies (streamlit, google-genai, pydantic, etc.)
│
├── agents/                              # Multi-Agent Logic & Business Engines
│   ├── __init__.py                      # Package initializer exporting agent functions
│   ├── batch_ranker_agent.py            # Deterministic portfolio sorter & committee justification generator
│   ├── contradiction_agent.py           # Hybrid pure-Python math + Gemini semantic discrepancy auditor
│   ├── declaration_explainer_agent.py   # Plain-language multilingual consent translator (Amharic/Oromo/Eng)
│   ├── eligibility_agent.py             # 100% Pure Python deterministic 15-declaration gatekeeper
│   ├── interview_agent.py               # 7-Step guided conversational intake state machine & extractor
│   ├── mapper_agent.py                  # Multimodal synthesis & explicit information gap analyzer
│   ├── router_agent.py                  # Evaluates profile to route to 1 of 3 100-point grid variants
│   └── scorer_agent.py                  # 100-Point scoring engine with weighted rubrics & gap penalties
│
├── app/                                 # UI Components & Web Presentation Layer
│   ├── __init__.py                      # App package initializer
│   ├── chat_bubble_ui.py                # WhatsApp/iOS-style transcript chat bubble with pill entity tags
│   ├── digital_twin.py                  # HTML/JS/CSS replica of official GIZ/sequa SME grant form
│   ├── heartbeat_ui.py                  # Animated SVG EKG pulse status indicator
│   ├── rehearsal_data.py                # Pre-calculated stage backup scenarios (Almaz & Nahom)
│   ├── streamlit_app.py                 # Master Streamlit application orchestrator (Tabs 1, 2, 3)
│   └── tts_ui.py                        # Web Speech API text-to-speech audio control for guided questions
│
├── extractors/                          # Multimodal Vision, Audio & Facility Parsers
│   ├── __init__.py                      # Extractor package exports
│   ├── audio_extractor.py               # 2-Step verbatim transcriber & fact extractor for voice notes
│   ├── config.py                        # GenAI client factory, 30s timeout cap, network error classifier & fallback chain
│   ├── schemas.py                       # Intermediate Pydantic schemas (License, Audio, Workshop)
│   ├── vision_extractor.py              # Zero-hallucination OCR parser for official paper trade licenses
│   └── workshop_extractor.py            # Facility due diligence vision agent for machinery & safety
│
├── schemas/                             # Enterprise Pydantic v2 Domain Models & Strict Types
│   ├── __init__.py                      # Schema package exports
│   ├── application_schema.py            # Sections 1.1 - 2.6 master grant application model
│   ├── consent_schema.py                # Plain-language declaration explanation & consent package models
│   ├── gap_schema.py                    # Explicit Gap, GapPriority, and ApplicationPack models
│   ├── impact_schema.py                 # 17 UN SDGs, verifiable milestones, and impact targets
│   ├── interview_schema.py              # Interview step definitions & atomic answer extraction models
│   ├── reviewer_schema.py               # Contradiction records, ranked company, and shortlist models
│   └── scoring_schema.py                # 9-criteria 100-point grid, EligibilityGate, and GridVariants
│
├── utils/                               # Shared Engineering Utilities
│   ├── __init__.py                      # Utils initializer
│   └── schema_sanitizer.py              # Inlines nested Pydantic $refs for Gemini API OpenAPI 3.0 compatibility
│
├── data/                                # Sample Payloads & Portfolio Datasets
│   ├── mock_application.json            # Reference JSON payload of a completed SME application
│   ├── mock_impact.json                 # Reference JSON payload of an impact protocol
│   └── sample_batch_12_applicants.json  # 12-applicant portfolio representing diverse Ethiopian SMEs
│
├── scripts/                             # Utility & Live CLI Scripts
│   ├── __init__.py                      # Scripts initializer
│   ├── check_models.py                  # Live script querying available Gemini API models
│   └── live_extraction_demo.py          # Standalone CLI demo testing vision and audio extraction
│
└── tests/                               # Comprehensive Automated Pytest Suite (50 Tests)
    ├── __init__.py                      # Test package initializer
    ├── test_batch5.py                   # Tests for contradictions, ranker sorting, and consent scripts
    ├── test_chat_bubble.py              # Tests for chat bubble HTML/CSS rendering and serialization
    ├── test_extractors.py               # Tests for vision, audio, config failover, and network error handling
    ├── test_interview.py                # Tests for guided interview steps, regex parser, and answer merge
    ├── test_mapper.py                   # Tests for multimodal mapper and zero-hallucination gap generation
    ├── test_schemas.py                  # 15 schema validation tests (validators, constraints, defaults)
    ├── test_scoring.py                  # Tests for eligibility gate, grid router, and 100-point scorer
    └── test_streamlit_smoke.py          # Smoke test verifying Streamlit app module import and boot
```

---

## 4. Master Data Schemas & Strict Validation Logic

All data structures in TeraGrant are defined using **Pydantic v2** with `extra="forbid"` (or `extra="ignore"` where intermediate parsing requires flexibility), field length constraints, range boundaries, and cross-field validator functions.

### 4.1 Application Schema (`schemas/application_schema.py`)
Maps directly to the official grant application sections:

#### Section 1.1: Business Information (`BusinessInfo`)
- `business_name` (`str`, min length 2, max length 255): Official registered legal enterprise name.
- `tin_number` (`Optional[str]`, min length 9, max length 15): Taxpayer Identification Number (returns `None` if unreadable).
- `location` (`str`, min length 2): Registered operating location/region/woreda/city.
- `sector` (`str`, min length 2): Industry sector (Agri-processing, Manufacturing, Clean-Tech, etc.).
- `years_in_operation` (`int`, ge 0): Years actively operating.
- `ownership_structure` (`str`): Sole Proprietorship, PLC, Share Company, Cooperative.
- `female_ownership_percentage` (`float`, 0.0 to 100.0): Percentage of equity held by women.

#### Section 1.2: Employment Breakdown (`EmploymentBreakdown`)
- `total_staff` (`int`, ge 0): Total full-time and regular employee headcount.
- `gender_split` (`GenderSplit`): `male` (int), `female` (int), `other` (int).
- `age_split` (`AgeBandSplit`): `youth_18_29` (int), `adults_30_50` (int), `seniors_above_50` (int).
- **Strict Validation Rules**:
  - `@model_validator`: `gender_split.male + female + other == total_staff` (raises `ValueError` on mismatch).
  - `@model_validator`: `age_split.youth + adults + seniors == total_staff` (raises `ValueError` on mismatch).

#### Sections 2.1 - 2.3: Financial History & Machinery (`FinancialHistory`)
- `sales_history` (`List[AnnualSales]`, max length 5): Historical annual sales in Ethiopian Birr (ETB), gross profit, and net profit.
- `machinery_list` (`List[MachineryItem]`): Inventory of key equipment, quantity, estimated asset value in ETB, and condition status (`Operational`, `Needs Repair`, `Decommissioned`).

#### Section 2.4: Management Structure (`OrganogramNode`)
- List of management positions: `role_title`, `holder_name`, `reports_to`, `department`, `responsibilities`.

#### Section 2.5: Mandatory Declarations (`MandatoryDeclarations`)
- **15 Statutory Legal Declarations**:
  1. `declaration_01_legal_compliance` (Valid trade license and local compliance)
  2. `declaration_02_truthful_information` (Information is true and accurate)
  3. `declaration_03_no_conflict_of_interest` (No conflict with grant committee)
  4. `declaration_04_no_double_funding` (No duplicate funding from other donors)
  5. `declaration_05_anti_bribery_corruption` (Zero tolerance to bribery/corruption)
  6. `declaration_06_environmental_compliance` (Environmental standard adherence)
  7. `declaration_07_fair_labor_standards` (Fair wages and non-discrimination)
  8. `declaration_08_child_labor_prevention` (Zero child labor / forced labor)
  9. `declaration_09_tax_compliance` (Active tax registration and good standing)
  10. `declaration_10_safeguarding_policy` (Workplace safety and gender protection)
  11. `declaration_11_data_privacy_consent` (Consent to audit verification)
  12. `declaration_12_financial_record_access` (Access to books of accounts)
  13. `declaration_13_fund_utilization_commitment` (Use grant solely on milestones)
  14. `declaration_14_regular_reporting_agreement` (Submit quarterly reports)
  15. `declaration_15_repayment_on_misuse` (Immediate repayment on misuse)
- **STRICT ARCHITECTURAL MANDATE**: All 15 fields **default to `False`**. Automated auto-ticking is strictly prohibited in code and schemas.

#### Section 2.6: Exclusion Factors (`ExclusionFactors`)
- **3 Instant-Kill Disqualification Flags** (default to `False`):
  1. `bankruptcy_or_insolvency` (Active bankruptcy or liquidation)
  2. `sanctions_or_criminal_convictions` (Sanctions, money laundering, fraud)
  3. `prohibited_activities` (Weapons, tobacco, gambling, illicit logging)
- If any flag is `True`, `is_disqualified` returns `True`.

---

### 4.2 Impact Protocol Schema (`schemas/impact_schema.py`)
- `project_title` (`str`, min 3, max 255 chars)
- `location` (`str`, min 2 chars)
- `target_beneficiaries` (`int`, ge 1)
- `etb_financial_target` (`float`, ge 0.0)
- `sector` (`str`, min 2 chars)
- `sdgs` (`List[SDGIndicator]`, min length 1): Enum selection of the 17 UN Sustainable Development Goals (e.g., `SDG 2: Zero Hunger`, `SDG 5: Gender Equality`, `SDG 9: Industry, Innovation, and Infrastructure`). Includes automatic deduplication validator.
- `milestones` (`List[Union[Milestone, str]]`, min length 1): Verifiable deliverables with required audit proof (e.g., machinery receipt, training sign-in sheet).

---

### 4.3 Gap Analysis & Application Pack Schema (`schemas/gap_schema.py`)
- `GapPriority` (`Enum`): `HIGH` (blocks compliance/eligibility), `MEDIUM` (impedes scoring precision), `LOW` (cosmetic/supplementary).
- `Gap` (`BaseModel`):
  - `field_name`: Exact schema dot-path (e.g., `"business_info.tin_number"`, `"employment.gender_split"`).
  - `reason_missing`: Detailed reason why extraction failed (e.g., `"TIN was unreadable/obscured by stamp on trade license certificate."`).
  - `required_from`: Responsible stakeholder (`"Applicant"`, `"Tax Office"`, `"Guarantor"`, `"Site Visit"`).
  - `priority`: `GapPriority.HIGH`, `MEDIUM`, or `LOW`.
- `ApplicationPack` (`BaseModel`):
  - `application`: Optional `ApplicationSchema`
  - `impact`: Optional `ImpactProtocol`
  - `gaps`: List of `Gap` records.

---

### 4.4 Scoring & Evaluation Schema (`schemas/scoring_schema.py`)
- `EligibilityGate`: `is_eligible` (bool), `failed_declarations` (list of str), `triggered_exclusions` (list of ExclusionFactor), `gate_reasoning` (str).
- `GridVariant` (`Enum`): `GENERAL_SME`, `WOMEN_YOUTH_LED`, `INNOVATION_TECH`.
- `CriterionName` (`Enum`): 9 standardized evaluation criteria:
  1. `JOB_CREATION`
  2. `GENDER_YOUTH_INCLUSION`
  3. `INNOVATION_UNIQUE_FEATURE`
  4. `FINANCIAL_VIABILITY`
  5. `LOCAL_SUPPLY_CHAIN`
  6. `SDG_ENVIRONMENTAL_IMPACT`
  7. `MANAGEMENT_ORGANOGRAM`
  8. `COMMUNITY_IMPACT`
  9. `SCALABILITY`
- `CriterionScore`: `criterion`, `max_points` (1 to 30), `awarded_points` (ge 0, le max_points), `reasoning` (min 10 chars).
- `ScoringResult`: `grid_variant`, `total_score` (sum of 9 criteria, le 100), `criteria_scores` (exactly 9 criteria), `eligibility_gate`, `reviewer_summary`.

---

### 4.5 Reviewer & Shortlist Schema (`schemas/reviewer_schema.py`)
- `ContradictionSeverity` (`Enum`): `CRITICAL` (mathematical impossibility / disqualification), `WARNING` (temporal or narrative variance).
- `Contradiction`: `claim_a`, `claim_b`, `severity`, `explanation`.
- `RankedCompany`: `rank` (1-indexed), `business_name`, `total_score`, `grid_variant`, `justification` (one paragraph memo), `site_visit_questions` (exactly 3 targeted inspection questions), `contradictions` (list).
- `RankedShortlist`: `companies` (list of `RankedCompany` sorted descending by score), `batch_summary` (executive portfolio narrative).

---

## 5. Multimodal Extractor Layer

### 5.1 Vision OCR Extractor (`extractors/vision_extractor.py`)
- **Objective**: Ingests document photos of Ethiopian regional commercial registration and trade license certificates.
- **Supported Formats**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`.
- **Zero-Hallucination Policy**:
  - The model prompt explicitly forbids guessing smudged or obscured digits.
  - If a TIN number or date is unreadable, it outputs `null`.
  - If the document is illegible or corrupted, `is_legible` is set to `False` with detailed extraction notes.
- **Implementation**: Uses `types.Part.from_bytes()` passing the raw image binary and MIME type to Google Gemini with `response_mime_type="application/json"` and `temperature=0.0`. Includes automatic JSON error retry mechanics.

### 5.2 Audio Extractor Agent (`extractors/audio_extractor.py`)
- **Objective**: Transcribes spoken audio stories and extracts structured business narrative facts in **Amharic**, **Afaan Oromo**, and **English**.
- **Supported Formats**: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.oga`, `.webm`.
- **Strict Two-Step Prompt Architecture**:
  - **STEP 1 (Verbatim Transcription)**: The AI transcribes the audio word-for-word in the native language without summarizing or correcting grammar.
  - **STEP 2 (Fact Extraction)**: Based *only* on Step 1, the AI extracts explicitly stated facts: `business_name`, `employee_count`, `female_staff`, `product_type`, `location`, `financial_figures`, and `impact_summary`.
- **Fail-Safe Operation**: Raises descriptive `RuntimeError` on empty transcripts rather than silently passing empty records.

### 5.3 Workshop Facility Evaluator (`extractors/workshop_extractor.py`)
- **Objective**: Analyzes photographs of workshops, factories, or agricultural facilities to corroborate applicant claims.
- **Extracted Attributes**:
  - `estimated_people_present`: Visible worker headcount.
  - `visible_machinery`: Identifiable machines, workbenches, tools, and industrial assets.
  - `workplace_safety_observations`: Lighting, ventilation, PPE, orderliness, clear hazards.
  - `is_legible`: Image quality and facility visibility assessment.

---

## 6. API Resilience, Timeout Cap & Smart Error Failover

The Google Gemini API integration in `extractors/config.py` is engineered for high reliability during live demonstrations and unstable network environments.

```
                  ┌────────────────────────────────────────────────────────┐
                  │              call_gemini_with_fallback()               │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          [Model 1: gemini-2.5-flash]                 [Network or 404/429 Error?]
                       │                                           │
          ┌────────────┴────────────┐                ┌─────────────┴─────────────┐
          ▼                         ▼                ▼                           ▼
     [Success 200]             [Exception]     [Network Error]            [404/429/Retired]
          │                         │                │                           │
   Return Response            Classify Error   Sleep 1s & Retry            Walk Fallback:
                              via is_network_error() Same Model Once       gemini-3.5-flash
                                                     │                     gemini-2.5-pro
                                               ┌─────┴─────┐                     │
                                               ▼           ▼                     ▼
                                           [Success]    [Fails] ───► Next Model in Chain
```

### 6.1 Hard 30-Second Client Timeout Cap
The GenAI client factory explicitly sets a 30-second timeout and forces the `v1` API version:
```python
http_opts = types.HttpOptions(timeout=30000, api_version="v1")
return genai.Client(api_key=effective_key, http_options=http_opts)
```
This guarantees that API requests never hang indefinitely on high-latency connections.

### 6.2 Network Error Classification (`is_network_error`)
A granular classifier inspects both exception types and Windows/Linux socket error codes:
- Python exceptions: `TimeoutError`, `ConnectionError`, `socket.timeout`, `socket.gaierror`, `httpx.TimeoutException`, `httpx.NetworkError`.
- Windows Socket Error Codes: `WinError 10060` (WSAETIMEDOUT), `10061` (WSAECONNREFUSED), `10054` (WSAECONNRESET), `10051` (WSAENETUNREACH), `10065` (WSAEHOSTUNREACH).
- Linux Errno: `110` (ETIMEDOUT), `111` (ECONNREFUSED), `101` (ENETUNREACH), `104` (ECONNRESET).

### 6.3 Smart Failover Chain (`MODEL_FALLBACK_CHAIN`)
When executing `call_gemini_with_fallback()`:
1. It attempts the requested model (`gemini-2.5-flash`).
2. If a **network/transport error** occurs, it pauses 1 second and retries **once** on the same model.
3. If an **API error** (e.g., 404 Not Found, 429 Rate Limit, Model Deprecated, Quota Exceeded) occurs, it automatically fails over to the next candidate in `MODEL_FALLBACK_CHAIN`:
   - `gemini-2.5-flash` ➡️ `gemini-3.5-flash` ➡️ `gemini-2.5-pro`.
4. Detailed error logs across all attempted model candidates are captured.

---

## 7. Multi-Agent Orchestration Layer

### 7.1 Intake & Gap Mapper Agent (`agents/mapper_agent.py`)
- **Responsibility**: Merges raw OCR license data, audio transcripts, and optional workshop observations into a unified `ApplicationPack`.
- **Source Precedence**:
  - Formal identity (Legal Name, TIN, Registered City) prioritizes the License OCR.
  - Operational narrative, headcount, products, and budget targets prioritize Audio transcripts.
- **Demographic Reconciliation**:
  - If total headcount is 8 and female count is 6, it computes male = 2, other = 0 to satisfy Pydantic validators.
  - If gender split is completely omitted, it generates a high-priority `Gap` for `employment.gender_split`.
- **Explicit Gap Generation**: For any missing or unreadable field, it creates a `Gap` record with the dot-path, reason, and responsible party.

### 7.2 Deterministic Eligibility Gatekeeper (`agents/eligibility_agent.py`)
- **Zero LLM Dependency**: Implemented in 100% pure Python for absolute determinism.
- **Evaluation Rules**:
  1. Checks all 15 declarations in `ApplicationSchema.declarations`. Any `False` or `None` value is appended to `failed_declarations`.
  2. Checks the 3 instant-kill exclusion criteria in `ApplicationSchema.exclusion_factors`.
  3. `is_eligible` is `True` if and only if `len(failed_declarations) == 0` AND `len(triggered_exclusions) == 0`.

### 7.3 Grid Variant Router Agent (`agents/router_agent.py`)
Analyzes the applicant's profile and impact goals to assign the optimal 100-point scoring rubric:
- **`WOMEN_YOUTH_LED`**: Assigned if female ownership $\ge 50\%$, or youth ownership $\ge 50\%$, or the workforce is predominantly women/youth.
- **`INNOVATION_TECH`**: Assigned if developing clean-tech, domestic electronics assembly, proprietary software/hardware, or novel import-substituting processes.
- **`GENERAL_SME`**: Assigned for standard retail, trade, agro-processing, or general light manufacturing.

### 7.4 100-Point Scorer Agent (`agents/scorer_agent.py`)
Evaluates the application against 9 standardized criteria. Point weightings adapt based on the selected grid variant:

| Evaluation Criterion | General SME | Women & Youth-Led | Innovation & Tech |
| :--- | :---: | :---: | :---: |
| **1. Job Creation** | 20 pts | 20 pts | 20 pts |
| **2. Gender & Youth Inclusion** | 15 pts | **30 pts** *(Double)* | 5 pts |
| **3. Innovation & Unique Feature** | 15 pts | 5 pts | **30 pts** *(Double)* |
| **4. Financial Viability** | 15 pts | 10 pts | 10 pts |
| **5. Local Supply Chain** | 10 pts | 10 pts | 10 pts |
| **6. SDG & Environmental Impact** | 10 pts | 10 pts | 10 pts |
| **7. Management & Organogram** | 5 pts | 5 pts | 5 pts |
| **8. Community Impact** | 5 pts | 5 pts | 5 pts |
| **9. Scalability** | 5 pts | 5 pts | 5 pts |
| **TOTAL MAXIMUM POINTS** | **100 pts** | **100 pts** | **100 pts** |

- **Mandatory Gap Penalties**: If data relevant to a criterion is missing in the `gaps` list (e.g., missing TIN $\rightarrow$ Financials; missing gender split $\rightarrow$ Gender Inclusion), the agent deducts points and includes the explicit citation: `"Score penalized due to missing data: [field_name]"`.

### 7.5 Forensic Contradiction Auditor (`agents/contradiction_agent.py`)
- **Layer 1 (Pure Python Math Checks)**:
  - Verifies `gender_split.total == total_staff` (flags `CRITICAL` contradiction on mismatch).
  - Verifies `age_split.total == total_staff` (flags `CRITICAL` contradiction on mismatch).
  - Cross-checks workshop photo headcount vs. declared staff (flags `WARNING` if $|observed - declared| > 2$).
- **Layer 2 (Gemini Semantic Cross-Checks)**:
  - Audits operational narrative against legal license dates (e.g., claiming 10 years of business with a license registered in 2024).
  - Audits financial claims against requested equipment capacity.

### 7.6 Portfolio Batch Ranker Agent (`agents/batch_ranker_agent.py`)
- Ingests multiple scored SME dossiers.
- Executes a deterministic sort by `(is_eligible, total_score)` in descending order.
- Generates a 1-paragraph Executive Justification citing specific metrics and flags for each applicant.
- Synthesizes exactly 3 high-impact Due Diligence Questions for field site-visit verification per applicant.
- Generates an overarching Batch Portfolio Summary.

### 7.7 Multilingual Verbal Consent Explainer (`agents/declaration_explainer_agent.py`)
- Translates the 3 most critical legal declarations into plain-language spoken Amharic, Afaan Oromo, or English:
  - `declaration_05_anti_bribery_corruption`
  - `declaration_08_child_labor_prevention`
  - `declaration_02_truthful_information`
- Avoids legal jargon and generates a culturally respectful verbal question script for voice agents to read.
- **Strict Constraint**: Outputs reading scripts only; checkboxes are never auto-ticked.

---

## 8. Guided Conversational Interview State Machine

Located in `agents/interview_agent.py`, this state machine guides entrepreneurs through a structured 7-question audio interview:

```
[S1: Name & Business] ──► [S2: Physical Location] ──► [S3: Sector & Product]
                                                             │
                                                             ▼
[S6: Machinery & ETB] ◄── [S5: Years in Operation] ◄── [S4: Staff & Gender]
         │
         ▼
[S7: Market & Buyers] ──► [Synthesize Full Audio Transcript] ──► [Execute Pipeline]
```

### 8.1 The 7 Trilingual Interview Steps

| Step ID | Target Field Path | English Question | Amharic Question | Afaan Oromo Question |
| :---: | :--- | :--- | :--- | :--- |
| **S1** | `business_info.business_name` | "What is your name, and what is the name of your business?" | ስምዎ ማን ይባል? የንግድ ቋምስ ስም ማን ነው? | Maqaan kee eenyu? Maqaan daldala keetoo maalii? |
| **S2** | `business_info.location` | "Where is your business located? City or woreda." | ንግድዎ የት ቦታ ይገኛል? ከተማ ወይም ወረዳ? | Daldalli kee eessatti argama? |
| **S3** | `business_info.sector` | "What do you make or sell?" | ምን ያመርታሉ ወይም ይሸጣሉ? | Maal oomishtuu ykn gurgurtaa? |
| **S4** | `employment.total_staff` | "How many people work for you, and how many of them are women?" | ስንት ሰዎች ይሰሩልዎታል? ስንቱ ሴቶች ናቸው? | Hojjattoota meeqatu siif hojjeta? Meeqatu dubartoota? |
| **S5** | `business_info.years_in_operation` | "For how many years have you been operating?" | ስንት ዓመት ሆነዎት እየሰሩ? | Waggaa meeqaaf hojjechaa jirta? |
| **S6** | `impact.etb_financial_target` | "What do you need for your business, and how much does it cost in birr?" | ለንግድዎ ምን ያስፈልግዎታል? ዋጋውስ ስንት ብር ነው? | Maaltu daldala keetiif barbaachisa? Birrii meeqa? |
| **S7** | `impact.project_title` | "Who buys your product, and where?" | ማን ነው ምርትዎን የሚገዛው? የትስ? | Eentutu oomisha kee bita? Eessatti? |

### 8.2 Extraction & Headcount Regex Parsing
- `extract_answer()` calls Gemini with `AnswerExtraction` schema returning the atomic `value` and a `confidence` float (0.0 to 1.0).
- `_parse_staff_counts()` utilizes regex pattern matching to extract both total headcount and female staff (e.g., parsing `"8 workers, 6 women"` $\rightarrow$ total=8, female=6).
- `merge_answer()` incrementally populates the `interview_data` session state.
- `synthesize_audio_extraction()` converts the completed interview answers into a standard `AudioTranscriptExtraction` object, allowing the downstream mapper, gate, router, and scorer agents to run without modification.

---

## 9. UI Component Engineering & Digital Twin Form

### 9.1 The Digital Twin Component (`app/digital_twin.py`)
- An embedded HTML5/JS/CSS component that replicates the layout of the official GIZ/sequa application form.
- **Dynamic JavaScript Injection**: The component accepts a JSON payload of extracted fields and missing gap keys.
- **Visual Status Badges**:
  - Verified fields are styled with green background (`#ECFDF5`), green border (`#059669`), and a `✓ Verified` badge.
  - Gaps are styled with red background (`#FEF2F2`), red border (`#EF4444`), and a `🔴 Missing / Gap` tag.
  - The top status badge indicates `✅ Form 100% Filled & Verified` or `⚠️ Form Filled with N Gaps Flagged`.

### 9.2 WhatsApp-Style Chat Bubble Component (`app/chat_bubble_ui.py`)
- Renders an iOS/WhatsApp-style speech bubble with an AI avatar and speech triangle.
- Displays the verbatim transcribed text alongside entity pill tags:
  - `🏢 Business Name`, `📍 Location`, `👥 Headcount`, `📦 Product`, `💰 Funding Target`, `🎯 Impact Summary`, `🌐 Language`.

### 9.3 EKG Heartbeat Animation Component (`app/heartbeat_ui.py`)
- An animated SVG pulse line indicating agent activity:
  - **Active State**: Glowing green line with continuous CSS stroke-dash animation: `🟢 Agent Active: Listening, Transcribing & Filling Form...`
  - **Idle State**: Muted slate line: `⚪ Agent Idle: Ready for Voice / Document Input`.

### 9.4 Web Speech TTS Component (`app/tts_ui.py`)
- Integrates browser-native `window.speechSynthesis` to speak interview questions aloud in English, Amharic, or Afaan Oromo with an interactive replay button.

---

## 10. Click-by-Click User Interaction & Feature Flow Guide

This section details exactly what occurs in the application upon every user interaction and button click.

### 10.1 Sidebar Controls

```
[Sidebar: API Key Input] ──► Sets st.session_state["api_key"] & os.environ["GEMINI_API_KEY"]
[Sidebar: Model Selector] ──► Chooses gemini-2.5-flash / gemini-3.5-flash / gemini-2.5-pro
[Sidebar: "Test API Connection" Button]
  │
  ├──► Initializes get_gemini_client()
  ├──► Calls client.models.list()
  └──► Displays ✅ Connected (with 5 sample models) or ❌ Connection Error
```

---

### 10.2 Tab 1: Applicant Intake & Digital Twin

#### Step 1: Mode Selection (Top Radio Button)
- **Option A: `🎙️ LIVE INTAKE MODE` (Default)**
  - Runs live Gemini API calls on uploaded files or microphone input.
  - Form starts 100% empty (`⚪ Awaiting Applicant Input`).
- **Option B: `🎭 REHEARSAL MODE`**
  - Displays two pre-calculated stage backup scenario buttons:
    - **Clicking "🌶️ Load Almaz Scenario"**:
      1. Loads Almaz Spice Mill data into session state.
      2. Simulates an unreadable/smudged TIN on the trade license and an omitted gender breakdown in the voice note.
      3. Digital Twin immediately displays filled fields with red gap tags on `TIN Number` and `Female Employees`.
      4. Renders 2 High-Priority Gaps, 78/100 Total Score under `WOMEN_YOUTH_LED`, and gap penalty reasoning.
    - **Clicking "⚡ Load Nahom Scenario"**:
      1. Loads Nahom CleanTech data into session state.
      2. Simulates 100% complete documentation with verified TIN (`0098765432`) and clean circular electronics recycling.
      3. Digital Twin displays green `✓ Verified` tags across all fields.
      4. Renders 0 Gaps, 92/100 Total Score under `INNOVATION_TECH`, and immediate grant recommendation.

---

#### Step 2: Selecting Intake Style (Right Column)

#### Flow A: "🗣️ Guided Interview (AI asks you)"

```
[Question Screen: S1 to S7]
  ├── AI Question Bubble displays text in EN, AM, OR
  ├── TTS Audio Button speaks question aloud
  └── User records answer via st.audio_input
        │
        ▼
  [Audio Captured]
        ├── Calls extract_audio_story() to transcribe
        ├── Calls extract_answer() to extract atomic fact
        ├── Displays Spoken Transcript & Extracted Fact with Confidence %
        └── Updates Digital Twin field in real time
              │
              ├── [Click "Next Question"] ──► Advances step counter (step_idx + 1)
              ├── [Click "Skip Question"] ──► Records skipped field & advances
              └── [Click "Reset"]         ──► Clears interview state to S1
```

- **Upon Reaching Question 7 and Clicking "🏁 Finish & Score Application"**:
  1. **Step 1/4 (Synthesize)**: `synthesize_audio_extraction()` combines all 7 Q&A pairs into a unified transcript and updates the chat bubble.
  2. **Step 2/4 (Vision & Facility)**: `extract_license_data()` parses the uploaded license; `extract_workshop_data()` evaluates the workshop photo.
  3. **Step 3/4 (Mapping & Gaps)**: `generate_application_pack()` merges all sources and identifies any missing data gaps.
  4. **Step 4/4 (Evaluation)**: `run_eligibility_gate()` runs deterministic checks; `detect_contradictions()` scans for discrepancies; `route_to_grid_variant()` triages the track; `score_application()` computes the 100-point rubric with gap penalties.
  5. The UI reruns and renders the post-evaluation summary below the Digital Twin.

---

#### Flow B: "📄 Free-form (one voice note)"

```
[Free-form Intake UI]
  ├── 1. Record via st.audio_input OR 2. Upload Voice Note File (.mp3/.wav/etc.)
  ├── 3. Select Language (Amharic / Oromo / English)
  └── [Optional] Upload Supporting Documents (Trade License / Workshop Photo)
        │
        ▼
  [Real-Time Voice Trigger]
        ├── EKG Heartbeat pulses green
        ├── Transcribes audio in real time
        └── Renders WhatsApp-style chat bubble with extracted entity chips
              │
              ▼
  [Click "🚀 Process & Score Application" Button]
        ├── Executes 4-Step Pipeline Status Box
        ├── Populates Digital Twin Form (Green verified / Red gaps)
        └── Renders Post-Evaluation Metrics & Committee Defense
```

---

#### Step 3: Inspecting Post-Evaluation Results (Left Column)
After evaluation completes, the following sections appear:
1. **Metric Banner**: Total Score (out of 100 with Eligible/Disqualified delta), Scoring Track (`WOMEN_YOUTH_LED`, `INNOVATION_TECH`, `GENERAL_SME`), Gate Verdict (`PASSED`/`FAILED`), Missing Gaps Count.
2. **Eligibility Gate Banner**: Green success or red error showing deterministic verdict reasoning.
3. **Forensic Discrepancies**: Red alert cards detailing detected mathematical or narrative contradictions with Claim A vs. Claim B citations.
4. **Identified Information Gaps**: Yellow/Red cards listing exact schema dot-paths, why the AI refused to hallucinate the data, and who must provide it.
5. **100-Point Criteria Breakdown**: Expandable progress bars for each of the 9 criteria showing awarded points, maximum points, and audit reasoning.
6. **Executive Defense Memo**: Full investment committee narrative summary.

---

### 10.3 Tab 2: Reviewer Batch Ranker

```
[Tab 2 Interface]
  ├── [Upload Batch JSON] OR [Click "📂 Load 12-Applicant Portfolio" Preset]
  └── Displays success message with applicant count
        │
        ▼
  [Click "⚡ Rank Batch & Defend Shortlist" Button]
        │
        ├── 1. Iterates through all applicants and maps scoring dossiers
        ├── 2. Runs rank_batch() with deterministic sort by (is_eligible, total_score) DESC
        ├── 3. Synthesizes 1-paragraph Executive Justifications
        ├── 4. Synthesizes 3 targeted Site-Visit Due Diligence Questions per SME
        └── 5. Generates Batch Summary Narrative
              │
              ▼
  [Ranked Portfolio Display]
        ├── Batch Overview Information Box
        └── Ranked Applicant Cards (#1 to #12):
              ├── Rank Badge (#1, #2, ...)
              ├── SME Name, Assigned Track, and Total Score / 100
              ├── Status Badge:
              │     🟢 Recommended for Grant (Score >= 80)
              │     🟡 Reserve List - Site Visit (Score 65-79)
              │     🔴 Below Allocation Cutoff (Score < 65)
              ├── Committee Justification Text
              ├── Flagged Contradiction Warnings (if applicable)
              └── Collapsible "Site Visit Due Diligence Checklist" (3 questions)
```

---

### 10.4 Tab 3: Multilingual Verbal Consent Generator

```
[Tab 3 Interface]
  ├── Select Target Spoken Language (Amharic / Oromo / English)
  └── [Click "📜 Generate Verbal Consent Scripts" Button]
        │
        ▼
  [Execution]
        ├── Calls generate_consent_package()
        ├── Translates 3 critical legal declarations (Anti-Bribery, Child Labor, Truthfulness)
        └── Renders Verbal Consent Cards:
              ├── 1. Declaration Title
              ├── 2. Left Column: Original Legal Regulation Text
              ├── 3. Right Column: Grassroots Plain-Language Translation
              └── 4. Bottom Box: Verbatim Voice Agent Consent Prompt
                    (Agent pauses for spoken "Yes / Ewo / Eeyyee" confirmation)
```

---

## 11. Automated Test Suite & Quality Verification

TeraGrant includes a test suite with **50 automated unit, mock, and integration tests** across 8 test modules.

### 11.1 Test Suite Breakdown

```
============================= test session starts =============================
Platform: Windows (Python 3.13.15) • Pytest: 9.1.1
Root Directory: c:\Users\HP\OneDrive\Desktop\AI Hackaton

Test Module                  Tests   Focus Areas
---------------------------  -----   -------------------------------------------------
tests/test_schemas.py         15     Pydantic constraints, defaults, validators, SDGs
tests/test_extractors.py       8     Vision OCR, Audio 2-step, timeout, network retry
tests/test_interview.py        8     Guided steps, regex parser, answer merge, loops
tests/test_mapper.py           2     Multimodal merge, gap generation, zero-hallucination
tests/test_scoring.py          5     Gate pass/fail, grid router, 100-pt rubric weights
tests/test_batch5.py           4     Pure math contradictions, batch ranker, Oromo consent
tests/test_chat_bubble.py      3     Pydantic & dict chat bubble rendering, sanitization
tests/test_streamlit_smoke.py  1     Full Streamlit app boot and import smoke test
---------------------------  -----   -------------------------------------------------
TOTAL:                        50     100% Passed (0 Failures, 0 Errors)
======================= 50 passed in 20.54s ========================
```

### 11.2 Key Assertions Verified by the Test Suite
1. **Mandatory Declarations Default to `False`**: Verified that instantiating `MandatoryDeclarations()` without arguments has all 15 fields set to `False`.
2. **Instant-Kill Exclusion Triggering**: Verified that setting `bankruptcy_or_insolvency=True` immediately disqualifies the applicant in `EligibilityGate`.
3. **Headcount Mathematical Invariant**: Verified that attempting to instantiate `EmploymentBreakdown` with `male=5, female=5` and `total_staff=12` raises a validation `ValueError`.
4. **Zero-Hallucination Gap Generation**: Verified that passing an unreadable license and a voice note omitting gender breakdown produces exactly 2 `Gap` records with `priority=HIGH`.
5. **Network Resilience Failover**: Verified that transport errors trigger a 1-second pause and retry, and API 404s walk the model chain (`gemini-2.5-flash` $\rightarrow$ `gemini-3.5-flash` $\rightarrow$ `gemini-2.5-pro`).

---

## 12. Installation, Configuration & Deployment Guide

### 12.1 Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13
- Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))
- Git

### 12.2 Installation Steps

```bash
# 1. Clone repository
git clone <repository_url>
cd "AI Hackaton"

# 2. Create and activate virtual environment (optional but recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Environment Variables
# Create a .env file in the root directory:
echo GEMINI_API_KEY="your_api_key_here" > .env
```

### 12.3 Running the Streamlit Application

```bash
streamlit run app/streamlit_app.py
```
The application will open in your default browser at `http://localhost:8501`.

### 12.4 Running Automated Tests

```bash
pytest tests/ -v
```

---

*Authored for the AI Builder Hackathon 2026 — Challenge 1: SME Grant Automation System.*
