# Batch A — Baseline & Scoring Grid Evidence Audit
**File**: `docs/audits/p0_batch_a_baseline_scoring_grid_audit.md`  
**Execution Timestamp**: 2026-09-04T01:42:00Z  
**Phase**: Batch A (P0-0 / P0-1 / P0-2)  
**Standard**: Evidence > Explanation (Zero unverified assumptions, zero code changes)  
**Governing Principle**:  
> **CODE OWNS THE NUMBERS.**  
> **AI OWNS THE SENTENCES.**

---

## 1. Executive Summary & Audit Scope

This audit establishes the frozen repository baseline and forensically audits the scoring architecture for ALPHAX / TeraGrant Agent. The audit investigates two critical evaluation weaknesses identified during technical review:
1. **Scoring Grid Provenance**: The current 9-criterion, 3-track scoring grid is an internal ALPHAX-created engineering prototype rather than a verified official SEQUA / GIZ evaluation rubric.
2. **Model Ownership of Consequential Numbers**: In `agents/scorer_agent.py`, the generative AI model (`Gemini`) is directly tasked with awarding consequential numerical scores (`awarded_points`) per criterion, rather than pure-Python deterministic code calculating numbers from extracted facts.

---

## 2. P0-0: Baseline Repository State

### 2.1 Git Repository Fingerprint
- **Current Branch**: `main`
- **Current HEAD SHA**: `eab02152323e90becd36afdd0c04d5ecd74726d7`
- **Working Tree Status Prior to Audit**: Clean (`nothing to commit, working tree clean`)
- **Recent Git Log (Last 10 Commits)**:
  ```
  eab0215 docs: remove hackathon evaluation criteria table from README
  7fb8260 docs: complete redesign of README with side-by-side visual tour, live Render links, and full system architecture
  b99e578 feat(keep-alive): add /healthz endpoint and GitHub Actions 10-minute keep-alive uptime pinger
  9f622c3 fix(37.2): wire contradiction detection into processing pipeline
  8671f32 fix(37.1): clear Almaz ghost from startup SESSION state
  67a0fd8 fix(mobile): enforce single-column responsive stacking for home cards with cache buster
  4cf2831 feat(ui): implement full responsiveness across mobile, tablet, laptop, and desktop viewports
  8bf8ced fix(models): update model fallback chain to gemini-3.6/3.5-flash and add 503 error handling
  a8c4952 chore(35): demo launcher + legacy port cleanup
  9dd45da chore(35): pre-demo sync
  ```

### 2.2 Test Suite Execution Baseline
- **Execution Command**: `pytest -q`
- **Execution Result**: `102 passed, 1 warning in 328.12s (0:05:28)`
- **Collected Test Count**: Exactly 102 unit, integration, and smoke tests across 14 test files
- **Warnings Observed**: 1 deprecation warning:
  ```
  tests/test_streamlit_smoke.py::test_app_boots_without_runtime_errors
  C:\Users\HP\AppData\Local\Programs\Python\Python313\Lib\importlib\metadata\__init__.py:476: 
  DeprecationWarning: Implicit None on return values is deprecated and will raise KeyErrors.
    return self.metadata['Name']
  ```
- **Test Integrity**: Full suite passes without error. No tests were skipped or broken.

---

## 3. P0-1: Current Scoring Architecture Audit

### 3.1 End-to-End Scoring Dataflow Table

The scoring path traverses from raw multimodal input to final presentation:

| Pipeline Stage | Function Name | Source File | Line Range | AI / LLM Involved? | Deterministic Code Involved? | Input Received | Data Structure Passed Forward |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **1. Input & Intake** | `extract_audio_story`<br>`extract_license_data`<br>`extract_workshop_data`<br>`run_intake_parallel` | `extractors/audio_extractor.py`<br>`extractors/vision_extractor.py`<br>`extractors/workshop_extractor.py`<br>`agents/intake_orchestrator.py` | L48-L135<br>L40-L115<br>L41-L117<br>L20-L76 | **YES**<br>(Gemini vision & audio) | **YES**<br>(Byte validation, error trapping, thread orchestration) | Raw `.mp3`/`.webm` audio bytes, `.jpg`/`.png` license & workshop photos | `AudioTranscriptExtraction`<br>`LicenseExtraction`<br>`WorkshopExtraction` |
| **2. Structured Dossier Synthesis** | `generate_application_pack`<br>`_build_deterministic_pack` | `agents/mapper_agent.py` | L53-L157<br>L160-L244 | **YES** (LLM synthesis in `generate_application_pack`) | **YES** (`_build_deterministic_pack`, gap detection, provenance tagging) | Extraction schemas | `ApplicationPack`<br>(contains `ApplicationSchema`, `ImpactProtocol`, `gaps: List[Gap]`, `provenance: Dict[str, FieldProvenance]`) |
| **3. Eligibility Gate** | `run_eligibility_gate` | `agents/eligibility_agent.py` | L14-L63 | **NO**<br>(Zero AI) | **YES**<br>(Pure Python boolean checks on 15 declarations & 3 exclusion factors) | `ApplicationSchema` | `EligibilityGate`<br>(`is_eligible: bool`, `failed_declarations: List[str]`, `triggered_exclusions: List[ExclusionFactor]`) |
| **4. Grid Track Routing** | `route_to_grid_variant` | `agents/router_agent.py` | L35-L104 | **YES**<br>(Gemini semantic analysis) | **YES**<br>(Fallback heuristic: if female ownership $\ge 50\%$, route to `WOMEN_YOUTH_LED`) | `ApplicationSchema`, `ImpactProtocol` | `GridVariant`<br>(`GENERAL_SME`, `WOMEN_YOUTH_LED`, `INNOVATION_TECH`) |
| **5. Criteria Evaluation & Scoring** | `score_application` | `agents/scorer_agent.py` | L56-L155 | **YES**<br>(Gemini awards points via JSON response) | **PARTIAL**<br>(Pre-attaches eligibility gate; sums model points; fallback baseline in `_build_default_scores`) | `ApplicationPack`, `GridVariant` | `ScoringResult`<br>(`criteria_scores: List[CriterionScore]`, `total_score: int`, `eligibility_gate: EligibilityGate`, `reviewer_summary: str`) |
| **6. Total Score Calculation** | `score_application`<br>`validate_total_score_sum` | `agents/scorer_agent.py`<br>`schemas/scoring_schema.py` | L121-L124<br>L119-L127 | **NO** | **YES**<br>(`sum(c.awarded_points for c in res.criteria_scores)`) | `criteria_scores` | `total_score: int` (0–100) |
| **7. Sensitivity & Potential Analysis** | `score_sensitivity` | `agents/scorer_agent.py` | L235-L295 | **NO** | **YES**<br>(Deterministic field mapping to recoverable gap points) | `ApplicationPack`, `ScoringResult` | `dict` (`current_score`, `potential_total`, `sensitivities`) |
| **8. Ranking & Portfolio Presentation** | `get_reviewer_data`<br>`rank_batch` | `app/review_logic.py`<br>`agents/batch_ranker_agent.py` | L103-L315<br>L20-L115 | **NO at render time** (`get_reviewer_data`);<br>**YES** in offline `rank_batch` for justifications | **YES**<br>(Deterministic sort by `(is_eligible, total_score)` descending; zero AI at UI render) | Portfolio list of scored dossiers / session state | `EnrichedShortlist`<br>(rendered in `app/templates/reviewer.html`) |

---

### 3.2 Model Ownership & Decision Inventory

Every location where an LLM (`call_gemini_with_fallback`) is invoked across the codebase:

| Source Location | Function Name | Input to Model | Output from Model | Direct Effect on Criteria Points? | Direct Effect on Total Score? | Direct Effect on Eligibility? | Direct Effect on Ranking? | Classification |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `agents/scorer_agent.py:92, 128` | `score_application` | JSON serialized application dossier, impact protocol, identified gaps, eligibility gate result, designated track | JSON matching `ScoringResult` with 9 `CriterionScore` objects containing `awarded_points` and `reasoning` | **YES**<br>(Model directly picks awarded points) | **YES**<br>(Total score is mathematical sum of model points) | **NO**<br>(Eligibility gate is computed in code and attached) | **YES**<br>(Ranking is sorted by total score) | **NUMERICAL DECISION** |
| `agents/router_agent.py:102` | `route_to_grid_variant` | `ApplicationSchema` and `ImpactProtocol` | JSON with `grid_variant` enum and `routing_rationale` | **INDIRECT**<br>(Determines max points distribution across criteria) | **INDIRECT**<br>(Alters available weight ceilings) | **NO** | **INDIRECT** | **INTERPRETATION** |
| `agents/batch_ranker_agent.py:107` | `rank_batch` | List of scored companies | JSON with executive rank justifications and 3 site-visit questions per applicant | **NO**<br>(Scores are pre-calculated) | **NO** | **NO** | **NO**<br>(Sorting is executed in Python code) | **EXPLANATION** |
| `agents/declaration_explainer_agent.py:81` | `generate_consent_package` | Declaration keys, descriptions, target language | JSON with local language translations, plain-language explanations, audio questions | **NO** | **NO** | **NO**<br>(Consent records require human verbal/manual affirmation) | **NO** | **EXPLANATION** |
| `agents/contradiction_agent.py:136` | `detect_contradictions` | Application claims, license claims, workshop observations | JSON list of semantic contradictions | **NO** | **NO** | **NO** | **INDIRECT**<br>(Feeds blockers list in submission readiness) | **INTERPRETATION** |
| `extractors/audio_extractor.py:95, 116` | `extract_audio_story` | Raw audio bytes / audio transcript prompt | JSON matching `AudioTranscriptExtraction` | **NO** | **NO** | **NO** | **NO** | **EXTRACTION** |
| `extractors/vision_extractor.py:71, 96` | `extract_license_data` | License image bytes | JSON matching `LicenseExtraction` | **NO** | **NO** | **NO** | **NO** | **EXTRACTION** |
| `extractors/workshop_extractor.py:72, 98` | `extract_workshop_data` | Workshop image bytes | JSON matching `WorkshopExtraction` | **NO** | **NO** | **NO** | **NO** | **EXTRACTION** |
| `agents/interview_agent.py:134, 157` | `extract_answer` | Interview transcript + targeted question | JSON with extracted field and confidence | **NO** | **NO** | **NO** | **NO** | **EXTRACTION** |
| `agents/mapper_agent.py:612` | `generate_application_pack` | Multimodal extraction outputs | JSON synthesized `ApplicationSchema` | **NO** | **NO** | **NO** | **NO** | **EXTRACTION / INTERPRETATION** |

---

### 3.3 Deterministic Code Inventory

The repository already possesses substantial deterministic Python modules:
1. **Eligibility Gate** (`agents/eligibility_agent.py:run_eligibility_gate`):
   - Evaluates all 15 declarations in `MandatoryDeclarations` (e.g., `declaration_01_legal_compliance` through `declaration_15_repayment_on_misuse`).
   - Evaluates all 3 exclusion factors in `ExclusionFactors` (`bankruptcy_or_insolvency`, `sanctions_or_criminal_convictions`, `prohibited_activities`).
   - Returns `is_eligible = True` strictly if 15 declarations are confirmed AND 0 exclusions are triggered.
   - Zero LLM involvement.
2. **Headcount & Demographic Sum Validation** (`agents/contradiction_agent.py` & `schemas/application_schema.py`):
   - Verifies `gender_split.male + gender_split.female + gender_split.other == total_staff`.
   - Verifies `age_split.youth_18_29 + age_split.adults_30_50 + age_split.seniors_above_50 == total_staff`.
   - Flags `CRITICAL` contradiction deterministically on mismatch.
3. **Score Sensitivity Engine** (`agents/scorer_agent.py:score_sensitivity`):
   - Pure Python mapping of missing `Gap` fields to recoverable points.
4. **Submission Readiness Calculator** (`agents/scorer_agent.py:submission_readiness`):
   - Computes readiness percentage $(0\%-100\%)$ from deterministic boolean gates, critical contradiction counts, and high-priority gap resolution status.
5. **Portfolio Sorting Engine** (`app/review_logic.py`):
   - Ranks applicant entries strictly using Python `sorted(entries, key=lambda x: (x[1].eligibility_gate.is_eligible, x[1].total_score), reverse=True)`.
   - Guaranteed zero AI calls at web render time.

---

### 3.4 Current Scoring Grid Definitions & Weights

- **Schema Definition**: `schemas/scoring_schema.py`
  - Enum `GridVariant`: `GENERAL_SME`, `WOMEN_YOUTH_LED`, `INNOVATION_TECH` (lines 45–49)
  - Enum `CriterionName`: 9 standardized criteria (lines 52–63)
  - Model `CriterionScore`: `criterion`, `max_points`, `awarded_points`, `reasoning` (lines 65–86)
  - Model `ScoringResult`: `grid_variant`, `total_score`, `criteria_scores`, `eligibility_gate`, `reviewer_summary` (lines 88–128)
- **Weight Matrix Defined in `agents/scorer_agent.py`** (`SCORER_SYSTEM_PROMPT` lines 29–44):

| Criterion Number & Name | GENERAL_SME Max Pts | WOMEN_YOUTH_LED Max Pts | INNOVATION_TECH Max Pts |
| :--- | :---: | :---: | :---: |
| 1. Job Creation | 20 | 20 | 20 |
| 2. Gender & Youth Inclusion | 15 | **30** *(Doubled)* | 5 |
| 3. Innovation & Unique Feature | 15 | 5 | **30** *(Doubled)* |
| 4. Financial Viability | 15 | 10 | 10 |
| 5. Local Supply Chain | 10 | 10 | 10 |
| 6. SDG & Environmental Impact | 10 | 10 | 10 |
| 7. Management & Organogram | 5 | 5 | 5 |
| 8. Community Impact | 5 | 5 | 5 |
| 9. Scalability | 5 | 5 | 5 |
| **TOTAL MAXIMUM** | **100** | **100** | **100** |

- **Framework Naming / Versioning in Code**:
  - Code references: "100-Point Scoring Grid", "100-Point Adaptive Scoring Matrix", "TeraGrant 100-point evaluation matrix".
  - Semantic versioning: None (no `v1.0` or official donor release tag exists).
- **Transparency in README and UI**:
  - `README.md` lines 220 and 407 cite the official GIZ/sequa application sections (1.1 to 2.6) for the *intake structure*, but do not state that the 9-criteria 100-point scoring matrix is an ALPHAX internal prototype.
  - The UI (`step3.html`, `step4.html`, `step6.html`, `reviewer.html`) displays "Provisional Application Score", "Rubric Score", and "Evaluation Track Comparison" without clarifying that the scoring grid is an internal ALPHAX development rubric.

---

## 4. P0-2: Official SEQUA Scoring Grid Evidence Verification

### 4.1 Exhaustive Evidence Search
An exhaustive search was conducted across:
1. All repository files (`README.md`, `project details.md`, `project_details.md`, `interrogation questions answer.md`, `schemas/`, `agents/`, `app/`, `data/`).
2. Hackathon assessment dossiers (`md 1.md`, `md 2.md`, `md 3.md`).
3. Local disk storage and PDF artifacts.

### 4.2 Key Findings from Authoritative Evidence
1. **Explicit Author Admission in Repository Documentation**:
   In `interrogation questions answer.md`, Section 12.2 ("Challenge PDF vs. Product Decision Audit", lines 481–487), the system designer documented:
   > *"1. Are the numerical weights officially specified in the Challenge PDF?*  
   > ***NO***. *The Challenge 1 brief states that applications must be evaluated on job creation, gender inclusion, innovation, and financial viability, but the exact 100-point numerical distribution (e.g., Job Creation = 20, Financials = 15) and double-weight multipliers are **product engineering decisions**, not official GIZ mandates.*  
   > *2. Are routing thresholds officially specified?*  
   > ***NO***. *The rule that $\ge 50\%$ female ownership routes to WOMEN_YOUTH_LED is a standard donor development metric implemented as a product heuristic."*

2. **Official Hackathon Code Audit Finding**:
   In `md 1.md`, Section 19–21 (lines 740–818), the evaluation report explicitly noted:
   > *"contains a nine-criterion scoring grid... But: **it isn't sequa's official grid**... your scores look comparable to a real review and are not... Nothing about the engineering needs to change; the grid does... Clearly label yours as a **stand-in / prototype scoring framework**. They specifically say **one line in the README** could fix the transparency issue."*

3. **Absence of Official SEQUA Matrix Artifact**:
   No document in the repository or supplied files contains an official SEQUA evaluation grid detailing official point allocations, rubric bands, or scoring guidelines.

### 4.3 Official Grid Status Verdict
**OFFICIAL GRID: NOT ESTABLISHED**

- **Evidence Summary**: Available evidence confirms the current 9-criterion, 3-track 100-point scoring matrix is an **ALPHAX-created internal engineering prototype**.
- **Trust-Preserving Mandate**: The current grid must be explicitly labeled as the **ALPHAX Internal Prototype Scoring Grid** in all schemas, UI displays, and documentation, unless and until an authoritative official SEQUA scoring specification is provided.

---

## 5. Current Scoring Behavior Baseline

### 5.1 Test Fixture Execution Analysis
A deterministic execution test was performed using `data/mock_application.json` and `data/mock_impact.json`:
- **Fixture Used**: Validated `ApplicationSchema` and `ImpactProtocol` (clean intake with 0 gaps).
- **Execution Test**: Evaluated across both the live fallback engine and mocked test harnesses (`tests/test_scoring.py`).

### 5.2 Observed Scoring Results

#### A. Fallback Baseline Engine (`agents/scorer_agent.py:_build_default_scores`)
When external API calls are unavailable (or in offline mode), the engine deterministically yields:
- **`GENERAL_SME`**: 67 / 100 pts
  - Job Creation: 14/20
  - Gender & Youth Inclusion: 10/15
  - Innovation & Unique Feature: 10/15
  - Financial Viability: 10/15
  - Local Supply Chain: 7/10
  - SDG & Environmental Impact: 7/10
  - Management & Organogram: 3/5
  - Community Impact: 3/5
  - Scalability: 3/5
- **`WOMEN_YOUTH_LED`**: 64 / 100 pts
  - Job Creation: 12/20, Gender & Youth: 22/30, Innovation: 3/5, Financials: 6/10, Supply Chain: 6/10, SDG: 6/10, Management: 3/5, Community: 3/5, Scalability: 3/5
- **`INNOVATION_TECH`**: 73 / 100 pts
  - Job Creation: 14/20, Gender & Youth: 3/5, Innovation: 24/30, Financials: 7/10, Supply Chain: 7/10, SDG: 7/10, Management: 4/5, Community: 3/5, Scalability: 4/5

#### B. Mocked Gemini Test Harness (`tests/test_scoring.py:test_100_point_scorer_innovation_tech_variant`)
- Input: `Sheba CleanTech PLC` with 1 gap (`financials.sales_history`)
- Selected Track: `INNOVATION_TECH`
- Total Score: 81 / 100 pts
- Subscores: Job Creation: 16/20, Gender/Youth: 4/5, Innovation: 26/30, Financials: 5/10 (penalized), Supply Chain: 8/10, SDG: 9/10, Management: 4/5, Community: 5/5, Scalability: 4/5.

### 5.3 Determinism and Model Dependency Verdict
- **Model Dependency**: **HIGH**. In live operation, `score_application()` passes the dossier to Gemini and expects the LLM to invent the individual `awarded_points`.
- **Code Reproducibility**: **LOW under live API**. Repeated execution under live Gemini can vary because the numbers are generated via generative completion rather than computed deterministically in Python.
- **Rule Principle Violation**: Currently violates **"CODE OWNS THE NUMBERS. AI OWNS THE SENTENCES."**

---

## 6. Audit Findings & Architectural Weaknesses

1. **Model Generates Consequential Numbers**:
   In `agents/scorer_agent.py`, Gemini outputs the numerical points. If an applicant asks "Why did I get 6 out of 10 points on Financial Viability?", there is no underlying mathematical function or explicit point-band rubric to reproduce that 6.
2. **Ambiguous Provenance of the Scoring Matrix**:
   The 9 criteria and 3 variants are plausible and comprehensive, but presenting them without disclosing that they are internal ALPHAX heuristics creates a false impression of donor-mandated scoring.
3. **Session Volatility**:
   The current application state is stored in memory (`app.server.SESSION`). Restarts wipe processed applications unless pre-loaded from fixtures.

---

## 7. Recommended Next Steps (Remediation Roadmap)

1. **Label Scoring Grid as Internal Prototype**:
   - Explicitly document in `README.md`, `schemas/scoring_schema.py`, and UI templates that the current scoring matrix is the **ALPHAX Internal Prototype Scoring Grid (v1.0-prototype)**.
2. **Enforce "Code Owns the Numbers"**:
   - Refactor `agents/scorer_agent.py` so that **deterministic Python functions calculate all numerical scores** based on extracted facts, provenance tags, and explicit point bands.
   - Restrict the LLM to generating the **qualitative explanations, gap justifications, and executive summaries**.
3. **Formalize Scoring Rule Bands**:
   - Define transparent, deterministic rule bands in Python (e.g., Job Creation points determined strictly by headcount thresholds; Financial Viability points determined strictly by verified turnover and gap absence).

---
*Audit completed with zero source code or test modifications.*
