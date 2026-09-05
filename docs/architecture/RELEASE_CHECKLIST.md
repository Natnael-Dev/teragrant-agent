# 🚀 TeraGrant V2 — Release Readiness & Architectural Checklist

This document summarizes the verified V2 production state of the TeraGrant Agent following remediation Batches A through K.

---

## 1. Core Architectural Principle
> **"Code owns the numbers. AI owns the sentences."**
- **Strict Role Boundary**: Quantitative evaluations, eligibility thresholds, and numerical point awards are exclusively executed by deterministic Python code.
- **LLM Restriction**: Gemini 2.0 Flash is restricted exclusively to multilingual voice transcription, optical fact extraction, semantic contradiction detection, and qualitative reviewer narrative synthesis.
- **Zero Hallucination Mandate**: The AI is prohibited from calculating, assigning, or adjusting numerical scores.

---

## 2. Deterministic Scoring Engine
- **ALPHAX Internal Prototype Grid (v1.0-prototype)**: Explicitly labeled prototype heuristic across 9 weighted criteria and 3 specialized SME tracks (`GENERAL_SME`, `WOMEN_AND_YOUTH_LED_SME`, `INNOVATION_AND_TECH_SME`).
- **Mathematical Step-Functions**: Implemented in isolated, zero-dependency `agents/rule_engine.py`.
- **Reproducibility**: 100% identical integer points and criterion breakdowns on repeated evaluations of identical inputs.
- **Full Derivability**: Every criterion score retains an audit trail containing `rule_applied`, `evidence_value`, `provenance_state`, and `provenance_cap_applied`.

---

## 3. Epistemic Provenance Ledger
- **6 Verification States**:
  - `DOCUMENT_VERIFIED` (1.0 cap / 100% points)
  - `APPLICANT_STATED` (0.7 cap / 70% points)
  - `AI_INFERRED` (0.5 cap / 50% points)
  - `NEEDS_CONFIRMATION` (0.4 cap / 40% points)
  - `CONTRADICTED` (0.0 cap / 0 points - requires committee review)
  - `MISSING` (0 points - zero silent defaults)
- **Unverified Traversal Integrity**: Missing fields strictly instantiate as `None` with `FieldStatus.MISSING` without injecting default values (`0`, `"Unknown Company"`).
- **Contradiction Preservation**: When independent sources disagree (e.g. 20 audio workers vs 5 photo workers), both conflicting claims are logged and preserved. Neither is silently adjudicated or averaged.

---

## 4. Persistence & Review Audit Engine
- **SQLite Database**: Live persistence via SQLAlchemy ORM models (`app/models.py`) writing to `teragrant.db`.
- **Automatic Intake Storage**: Applications, evidence files, extracted field paths, and individual criterion scores are persisted upon processing.
- **Reviewer State Persistence**: Dedicated `/api/review` endpoint stores committee decisions (`RECOMMENDED_FOR_APPROVAL`, `REQUEST_FIELD_AUDIT`, `REJECTED`), reviewer identity, and defense notes.
- **Restart Survival**: Data survives complete server restarts, accessible via `GET /api/applications` and `/reviewer`.

---

## 5. Shippability & Keyless Evaluation
- **Offline Keyless Replay**: Strangers and auditors can execute `python scripts/run_keyless_demo.py` without requiring Google Gemini API keys or external network connectivity.
- **Pre-recorded Fixture**: `data/fixtures/demo_extraction.json` provides an authentic, audit-grade `ApplicationPack` with 12 verified provenance records.
- **Automated Release Gate**: `python scripts/final_release_gate.py` runs full regression tests, keyless replay validation, hygiene checks, and credential scanning.

---

## 6. Verification Status Matrix

| Audit Check | Status | Verification Mechanism |
| :--- | :---: | :--- |
| **Deterministic Rule Engine** | PASS | `tests/test_rule_engine.py` (37 tests) |
| **Scorer Agent Migration** | PASS | `tests/test_scoring.py` (22 tests) |
| **Score Audit Trail** | PASS | `tests/test_score_audit.py` (8 tests) |
| **SQLite Persistence** | PASS | `tests/test_persistence.py` (14 tests) |
| **Epistemic Traversal** | PASS | `tests/test_unverified_traversal.py` (4 tests) |
| **Adversarial Resilience** | PASS | `tests/test_adversarial.py` (4 tests) |
| **Shippable Hygiene** | PASS | `tests/test_shippable.py` (3 tests) |
| **Full Regression Suite** | PASS | `pytest -q` (161 passing tests) |
| **Automated Release Gate** | PASS | `python scripts/final_release_gate.py` |
