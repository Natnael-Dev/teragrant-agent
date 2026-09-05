# Data Protection Boundary & Persistence Architecture
**Version**: 1.0 (Remediation Batch G)  
**System**: ALPHAX / TeraGrant Agent  
**Standard Reference**: SEQUA / GIZ SME Support Scheme Data Governance & Epistemic Trust Policy  

---

## 1. Executive Summary & Objective

The hackathon architecture evaluation praised ALPHAX for its honest epistemic provenance ledger, deterministic contradiction checks, and multilingual voice-to-form intake. However, reviewers noted:
> *"No database — everything is session and file based... adding persistence introduces data-protection questions regarding applicant documents, audio, and extracted facts."*

This document defines the formal **Data Protection Boundary** governing the persistence layer. It establishes strict rules regarding:
1. What data is persisted permanently versus kept strictly temporary.
2. Separation of biometric voice recordings from permanent applicant records (Data Minimization).
3. Role-Based Access Control (RBAC) boundaries between Applicants, Reviewers, and Auditors.
4. Retention schedules and secure purge policies.
5. Cascade deletion guarantees ensuring complete erasure upon applicant request.

---

## 2. Core Governance Principle: Epistemic Minimization

> **"PERSIST DERIVABLE PROOF, NOT RAW BIOMETRICS. KEEP CODE AUDITABLE, KEEP PERSONAL DATA TRANSIENT."**

The TeraGrant system separates raw multimodal intake media from structured, verifiable application facts:
- **Audio & Imagery** are transient sensory intake streams used to substantiate facts.
- **Extracted Facts & Provenance States** are auditable legal claims submitted to the evaluation pipeline.
- **Audit Trails & Scoring Rules** are immutable institutional evaluation records.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        INGESTION BOUNDARY                              │
│  [Voice Audio Bytes]     [Trade License PDF]     [Workshop Photo]      │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
              Transient Processing & Feature Extraction
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   PERMANENT PERSISTENCE BOUNDARY                       │
│  ┌───────────────────────┐             ┌────────────────────────────┐  │
│  │  ApplicationRecord    │             │  CriterionScoreRecord      │  │
│  │  - Metadata & Track   │─────────────│  - Deterministic Points    │  │
│  │  - Business TIN & Name│             │  - Rule & Evidence Audit   │  │
│  └──────────┬────────────┘             └────────────────────────────┘  │
│             │                                                          │
│             ├──────────────────────────┐                               │
│             ▼                          ▼                               │
│  ┌───────────────────────┐  ┌────────────────────────────┐             │
│  │  ExtractedFieldRecord │  │  EvidenceRecord            │             │
│  │  - Normalized Value   │  │  - SHA-256 Checksum        │             │
│  │  - Epistemic Status   │  │  - Metadata / Source Type  │             │
│  │  - Confidence Score   │  │  - Redacted Document Path  │             │
│  └───────────────────────┘  └────────────────────────────┘             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Classification & Lifecycle

| Data Category | Examples | Storage Target | Retention Period | Deletion Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Transient Ingestion Bytes** | Raw `.wav` / `.mp3` voice recordings, temporary multipart uploads | In-memory RAM / OS `/tmp` buffer | Session lifetime (max 1 hour) | Session completion or user disconnect |
| **Derived Audio Transcripts** | Verbatim Amharic/Tigrinya/English transcripts, answer extractions | `transcripts` table in SQLite | Active Evaluation Cycle (30 days) | Cascade deletion on application purge |
| **Evidence Metadata** | File SHA-256 hash, document issue date, issuing bureau, page count | `evidence_records` table | Evaluation Cycle + 1 Year Audit Hold | Application deletion or applicant GDPR/DP request |
| **Normalized Extracted Facts** | Employee headcount, turnover ETB, female ownership %, sector | `extracted_fields` table | Evaluation Cycle + 1 Year Audit Hold | Application deletion or applicant GDPR/DP request |
| **Epistemic Provenance** | `DOCUMENT_VERIFIED`, `APPLICANT_STATED`, confidence level, citation snippet | `extracted_fields` table | Indefinite (anonymized after program close) | Cascade deletion on application purge |
| **Deterministic Scoring Audit** | `rule_applied`, `evidence_value`, `provenance_cap_applied`, `awarded_points` | `criterion_scores` table | Indefinite (Immutable Audit Trail) | Cascade deletion on application purge |
| **Committee Reviews & Decisions** | Approval status, site-visit inspection orders, reviewer notes | `review_records` table | 5 Years (Donor Regulatory Mandate) | Administrative purge after statute of limitations |

---

## 4. Role-Based Access Control (RBAC) Boundaries

### 4.1. Applicant Boundary
- **Permissions**:
  - Can upload multimodal evidence (license scans, audio notes).
  - Can view and edit their own digital twin form prior to final submission.
  - Can view real-time epistemic validation chips (`DOCUMENT_VERIFIED`, `NEEDS_CONFIRMATION`, `MISSING`).
  - Can download their complete application dossier pack (`GET /api/export`).
- **Restrictions**:
  - **CANNOT** view internal Investment Committee scoring weights, private reviewer notes, or cross-applicant rankings.
  - **CANNOT** mutate or overwrite historical application snapshots once submitted for committee evaluation.

### 4.2. Reviewer Boundary
- **Permissions**:
  - Can view normalized application dossiers, trade license OCR records, and synthesized transcripts.
  - Can inspect full criterion-level audit trails (`rule_applied`, `evidence_value`, `provenance_cap_applied`).
  - Can record committee verdicts (`APPROVED`, `REJECTED`, `SITE_VISIT_REQUIRED`) and qualitative observations in `ReviewRecord`.
  - Can export anonymized shortlist rankings (`GET /api/reviewer/export`).
- **Restrictions**:
  - **CANNOT** manually override deterministic mathematical scoring points directly in the database (Points are strictly governed by `rule_engine.py`).
  - **CANNOT** download raw voice biometric files unless granted certified forensics authorization.

### 4.3. Donor / Auditor Boundary (SEQUA / GIZ Independent Audit)
- **Permissions**:
  - Read-only access to complete provenance ledgers, contradiction logs, and deterministic scoring traces.
  - Verification that point allocations adhere strictly to the published scoring rubric without subjective human manipulation.
  - Inspection of cascade deletion logs to verify compliance with national data privacy regulations.

---

## 5. Retention & Purge Policy

1. **Voice Data Minimization**:
   - Spoken audio files contain biometric voiceprints. Raw audio buffers are processed in memory for speech-to-text transcription and atomic fact extraction, then immediately flushed from volatile memory.
   - Raw audio waveforms are **never** committed to permanent database tables (`teragrant.db`).
2. **Automated Document Purging**:
   - Temporary file uploads saved to staging disk directories are scanned and purged every 30 days via scheduled housekeeping.
   - Only document hashes and extracted text snippets relevant to audit verification remain in permanent storage.
3. **Right to Erasure (Cascade Deletion)**:
   - If an applicant requests deletion of their dossier, deleting the parent `ApplicationRecord` triggers database-level foreign key cascades (`PRAGMA foreign_keys=ON; ON DELETE CASCADE`).
   - Every associated child row in `evidence_records`, `extracted_fields`, `criterion_scores`, and `review_records` is deleted atomically within the same transaction.

---

## 6. Database Schema Design (SQLAlchemy ORM)

The relational schema implements these boundaries with strict foreign keys:

- **`applications`** (`ApplicationRecord`): Core entity storing metadata, applicant name, creation timestamp, evaluation status, and routed `GridVariant`.
- **`evidence_records`** (`EvidenceRecord`): Document verification metadata, source categorization (`license`, `interview`, `workshop`), and cryptographic content hashes.
- **`extracted_fields`** (`ExtractedFieldRecord`): Atomic facts extracted from evidence, tagged with epistemic status (`DOCUMENT_VERIFIED`, `APPLICANT_STATED`, etc.) and confidence scores.
- **`criterion_scores`** (`CriterionScoreRecord`): Deterministic scoring results per criterion, preserving the complete audit trail (`rule_applied`, `evidence_value`, `provenance_state`, `provenance_cap_applied`).
- **`review_records`** (`ReviewRecord`): Investment committee review outcomes, notes, and audit timestamps.
