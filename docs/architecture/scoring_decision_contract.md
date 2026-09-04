# Scoring Decision Contract: Division of Responsibility
**Document**: `docs/architecture/scoring_decision_contract.md`  
**Version**: 1.0  
**Status**: Formal Architectural Standard  
**Governing Principle**:  
> **CODE OWNS THE NUMBERS. AI OWNS THE SENTENCES.**

---

## 1. Context & Purpose

The hackathon audit established that while ALPHAX / TeraGrant excelled in provenance tracking, deterministic contradiction checks, and reviewer committee defense, the scoring pipeline exhibited a fundamental architectural flaw:
In `agents/scorer_agent.py`, the generative LLM (`Gemini`) was directly tasked with awarding consequential numerical points (`awarded_points`) per criterion.

This violated the principle of auditability and deterministic reproducibility:
- An applicant or auditor asking *"Why did I get 6 out of 10 points on Financial Viability?"* could not receive a mathematically re-derivable answer because the number was produced by stochastic generative sampling rather than an explicit rule band.
- If executed repeatedly on identical evidence, model responses can drift or vary based on model version, temperature, or prompt structure.

This **Scoring Decision Contract** establishes an immutable boundary between generative AI operations and deterministic Python code. It serves as the formal specification for the deterministic rule engine (Batch D).

---

## 2. Architectural Boundary Matrix

| Capability / Function | Responsible Layer | Permitted Technology | Prohibited Behavior |
| :--- | :--- | :--- | :--- |
| **Multimodal Fact Extraction** | AI Extractor Layer | LLM / Vision / Audio (Gemini) | Inventing missing fields; converting silence into facts |
| **Epistemic Provenance Tagging** | Intake Orchestrator | Python Ledger + Extractor Confidence | Marking self-reported claims as `DOCUMENT_VERIFIED` |
| **Semantic Cross-Checking** | AI Auditor Layer | Gemini Reasoning | Resolving or forgiving detected discrepancies |
| **Mathematical Sum Auditing** | Deterministic Truth Layer | Pure Python arithmetic | Allowing floating-point or off-by-one headcount errors |
| **Eligibility Gatekeeping** | Deterministic Gatekeeper | Pure Python boolean logic | Calling an LLM to waive mandatory declarations |
| **Scoring Band Evaluation** | Deterministic Rule Engine | Pure Python step-functions & tables | LLM assigning points or picking point bands |
| **Point Calculation & Sums** | Deterministic Rule Engine | Pure Python arithmetic | AI altering max weights or computing subtotals |
| **Rank Ordering** | Presentation / Logic | Pure Python `sorted()` | AI reordering applicants based on qualitative preference |
| **Executive Explanations** | AI Explainer Layer | Gemini Generation | Mentioning hallucinated numbers not produced by code |

---

## 3. AI Allowed Responsibilities (What Gemini / LLM May Do)

Generative AI models are strictly confined to perception, transcription, linguistic translation, and qualitative explanation:

1. **Extract Facts from Unstructured Inputs**:
   - Transcribe spoken audio stories in Amharic, Afaan Oromo, and English into literal transcripts.
   - Extract raw entities (e.g., claimed employee counts, declared annual sales figures, business names, machinery descriptions) into typed extraction schemas.
2. **Identify Relevant Evidence for Criteria**:
   - Scan extracted text and OCR outputs to identify which phrases or data points relate to specific evaluation criteria (e.g., locating mentions of female ownership for the Gender & Youth criterion).
3. **Describe Ambiguity & Missing Information**:
   - Articulate why a specific field is unclear, smudged, unreadable, or omitted in plain language for human review.
4. **Explain Deterministic Scoring Results in Natural Language ("AI Owns the Sentences")**:
   - Take the exact numerical score, the matched rule band, the gap deductions, and the provenance status calculated by Python, and synthesize an executive narrative for the review committee.
   - Formulate contextual, localized site-visit due diligence questions based on the exact gaps identified by code.
5. **Identify Semantic Contradictions Between Sources**:
   - Detect contextual discrepancies between claims across modalities (e.g., narrative claims of 10 operating years vs. license issue date of 6 months ago) and categorize them for human committee review.

---

## 4. AI Forbidden Responsibilities (What Gemini / LLM MUST NOT Do)

Generative AI models are strictly forbidden from exercising consequential discretion over any numerical value or eligibility verdict:

1. **MUST NOT Assign Numerical Points**:
   - The LLM must never decide whether an applicant gets 4, 8, or 12 points for any criterion.
2. **MUST NOT Choose Scoring Bands**:
   - The LLM must never decide whether an applicant's metric (e.g., 15 employees, 450,000 ETB sales) qualifies as "Low", "Medium", "High", or "Exceptional". Point bands must be hardcoded in Python functions.
3. **MUST NOT Change Criterion Weights or Maximum Allocations**:
   - Weight ceilings (e.g., Job Creation = 20 pts, Innovation = 30 pts) are immutable policy constraints enforced by schemas and Python configuration, never prompt parameters.
4. **MUST NOT Calculate Total Scores, Subtotals, or Penalties**:
   - All addition, subtraction, gap penalties, and percentage calculations must be performed exclusively by Python.
5. **MUST NOT Silently Resolve Contradictions**:
   - If audio and documents disagree, the LLM must not guess which source is "correct". It must flag the contradiction with severity and submit both claims to the provenance ledger.
6. **MUST NOT Convert Missing or Unverified Evidence into Positive Signals**:
   - An unstated field must never be interpreted by the LLM as "assumed compliant" or "plausibly satisfactory". Absence of proof is proof of absence until verified.

---

## 5. Deterministic Code Responsibilities (What Python Must Do)

Pure Python code owns the complete numerical, compliance, and ranking pipeline:

1. **Evaluate Eligibility Gates**:
   - Pure boolean evaluation of all 15 mandatory declarations and 3 instant-kill exclusions in `agents/eligibility_agent.py`.
   - Zero LLM involvement in the disqualification verdict.
2. **Apply Explicit Rule Bands to Extracted Facts**:
   - Transform normalized facts into points using discrete, human-inspectable step-functions (e.g., `if staff >= 20: points = 20; elif staff >= 10: points = 14; ...`).
3. **Calculate Criterion Points Based on Provenance**:
   - Apply point discounts or caps when a fact is backed only by informal claims (`APPLICANT_STATED`) rather than official documentation (`DOCUMENT_VERIFIED`).
4. **Execute Deterministic Gap Deductions**:
   - Subtract explicit, predefined penalty points whenever a critical or medium gap exists in `pack.gaps`.
5. **Calculate Total Scores & Rank Shortlists**:
   - Compute `total_score = sum(criterion.awarded_points)`.
   - Execute strictly reproducible sorting: `sorted(batch, key=lambda x: (x.is_eligible, x.total_score), reverse=True)`.

---

## 6. Provenance Integration & Scoring Rules

The 6 epistemic states in `schemas/provenance_schema.py:FieldStatus` dictate the scoring ceiling of every criterion:

```
                  ┌─────────────────────────────────────────┐
                  │           EVIDENCE SOURCE               │
                  └────────────────────┬────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│ Official License │          │   Voice Note /   │          │ Discrepancy /    │
│    or Registry   │          │ Interview Claim  │          │ Missing File     │
└────────┬─────────┘          └────────┬─────────┘          └────────┬─────────┘
         │                             │                             │
         ▼                             ▼                             ▼
 ┌───────────────┐             ┌───────────────┐             ┌───────────────┐
 │DOCUMENT_      │             │APPLICANT_     │             │MISSING or     │
 │VERIFIED       │             │STATED         │             │CONTRADICTED   │
 └───────┬───────┘             └───────┬───────┘             └───────┬───────┘
         │                             │                             │
         ▼                             ▼                             ▼
  Full Points                   Capped Points                 Zero Points
  Eligible                      (e.g., max 60-70%)            Flagged Blocker
```

### Specific Provenance Rules:
1. **Rule P-1 (Document Requirement)**:
   - Criteria requiring official legal status (e.g., TIN verification, business registration) require `DOCUMENT_VERIFIED`. 
   - An `APPLICANT_STATED` or `AI_INFERRED` status for these fields cannot satisfy the requirement and results in 0 points for that component plus a high-priority `Gap`.
2. **Rule P-2 (Self-Reported Ceiling)**:
   - Where a criterion permits applicant-stated metrics (e.g., projected jobs, turnover without audited tax return), the awarded points are capped at a designated threshold (e.g., maximum 65% of available criterion points) until physical evidence is verified on-site.
3. **Rule P-3 (Inference Non-Equivalence)**:
   - An `AI_INFERRED` status (e.g., machinery inferred from workshop photo background) is treated as a tentative lead. It may never be scored as equivalent to `DOCUMENT_VERIFIED`.
4. **Rule P-4 (Zero Point Rule for Missing/Contradicted)**:
   - Any criterion whose underlying primary evidence has status `MISSING` or `CONTRADICTED` must receive **0 awarded points** (or the baseline floor). Missing evidence must NEVER silently collapse to a positive or default average score.

---

## 7. The Re-Derivability Guarantee

A scoring system is legally and ethically defensible only when any human reviewer or independent auditor can re-derive the exact numerical score from first principles without running an AI model.

### The Contract Guarantee:
```
Given:
  1. Extracted Fact Dictionary (ApplicationSchema & ImpactProtocol)
  2. Provenance Ledger (FieldProvenance for each field)
  3. Designated Scoring Track (GridVariant)
  4. Deterministic Python Rule Engine Code

Then:
  Auditor_Score == System_Score
  Variance == 0.0000 (Exact Integer Match)
```

No external API key, no stochastic sampling, and no temperature variations may alter the awarded points. If two runs on the same inputs produce different scores, the system is in breach of this contract.

---

## 8. Edge Case Handling Policy

| Edge Case Scenario | Permitted System Behavior | Prohibited System Behavior |
| :--- | :--- | :--- |
| **Evidence is MISSING** | The rule engine awards **0 points** for that criterion component, logs an explicit `Gap` with `required_from="Applicant"`, and sets a sensitivity target indicating points recoverable upon submission. | Guessing an average, imputing a median, or assuming good faith compliance. |
| **Evidence is CONTRADICTED** | The rule engine awards **0 points** for the disputed metric, logs a `Contradiction` record (`CRITICAL` or `WARNING`), attaches both conflicting claims to the dossier, and blocks submission readiness until reviewed. | Silently picking the higher or lower value, or asking the LLM to decide which claim sounds more believable. |
| **AI Extraction Fails or Times Out** | The system logs the failure, leaves affected fields as `None` with status `MISSING`, records a technical extraction gap, and evaluates remaining criteria with deterministic fallback baselines. | Fabricating default enterprise numbers, inventing a composite score, or returning a hallucinated JSON payload. |
| **Zero Declarations Confirmed** | `EligibilityGate` deterministically outputs `is_eligible=False` and enumerates all 15 failed declarations. Overall total score is calculated for audit transparency, but applicant is locked from recommendation. | Overriding eligibility because the applicant had high impact or strong job projections. |
| **Applicant Claims Exceed Rule Maximums** | Python clamp functions strictly enforce `min(calculated_points, max_points)`. | Allowing criterion points or total points to exceed their allocated ceiling. |

---

## 9. Implementation Roadmap (Batch D)

With this contract established:
1. **Module Creation**: Create `agents/rule_engine.py` encapsulating pure Python scoring functions for each of the 9 criteria.
2. **Scorer Refactoring**: Refactor `agents/scorer_agent.py` so that `score_application()` calls `agents/rule_engine.py` for all numerical computation, and restricts Gemini to generating the `reviewer_summary` and qualitative justifications.
3. **Verification Suite**: Write exhaustive unit tests verifying 100% deterministic re-derivability across edge cases, missing data, and varied provenance states.

---
*Contract ratified for ALPHAX / TeraGrant Remediation.*
