"""
Truthfulness and Unverified Traversal Tests (Batch I / P1-4, P1-5, P1-6).
Verifies:
1. Missing evidence stays MISSING (no silent defaults like 0, 'Unknown Company', or 'Addis Ababa').
2. Contradictions preserve both claims (no silent adjudication or averaging).
3. AI fallbacks are explicitly flagged and reported in export and UI.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.server import app, SESSION
from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction, WorkshopExtraction
from schemas.provenance_schema import FieldStatus
from schemas.reviewer_schema import ContradictionKind
from agents.mapper_agent import _build_deterministic_pack, generate_application_pack
from agents.contradiction_agent import detect_contradictions
from agents.scorer_agent import score_application
from schemas.scoring_schema import GridVariant


INITIAL_SESSION_STATE = {
    "applicant_name": "New Applicant",
    "transcript": "",
    "chips": [],
    "audio_data": None,
    "license_data": None,
    "workshop_data": None,
    "pack_res": None,
    "scoring_res": None,
    "readiness_res": None,
    "consent_records": [],
    "consents": {},
    "resolved_gaps": [],
    "interview_data": {},
    "interview_transcripts": [],
    "processed": False,
    "digital_twin_data": {},
    "contradictions": [],
    "current_application_id": None,
    "ai_fallback_used": False,
}


@pytest.fixture(autouse=True)
def clean_session():
    """Ensure session is clean before and after every traversal test."""
    SESSION.clear()
    SESSION.update(INITIAL_SESSION_STATE)
    yield
    SESSION.clear()
    SESSION.update(INITIAL_SESSION_STATE)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# =============================================================================
# 1. TRAVERSAL TEST & MISSING DATA (P1-4)
# =============================================================================

def test_traversal_missing_evidence_stays_missing():
    """
    Feed an empty audio file and an unreadable/blank license image to the pipeline.
    Assert that total_staff, annual_turnover, and business_name have provenance state MISSING.
    Assert that NO default values (like 0, 'Unknown Company', or 'Addis Ababa') are injected.
    The fields must be None.
    """
    empty_license = LicenseExtraction(
        is_legible=False,
        business_name=None,
        tin_number=None,
        location=None,
        extraction_notes="Empty/unreadable document image",
    )
    empty_audio = AudioTranscriptExtraction(
        transcript="",
        detected_language="English",
        business_name=None,
        employee_count=None,
        location=None,
        financial_figures=[],
    )

    pack = _build_deterministic_pack(
        license_data=empty_license,
        audio_data=empty_audio,
        workshop_data=None,
    )

    # 1. ApplicationSchema must not be None, but its fields must be None (no defaults)
    assert pack.application is not None, "ApplicationSchema should be instantiated even when facts are missing"
    info = pack.application.business_info
    assert info is not None
    assert info.business_name is None, f"Expected None for business_name, got {info.business_name}"
    assert info.tin_number is None, f"Expected None for tin_number, got {info.tin_number}"
    assert info.location is None, f"Expected None for location, got {info.location}"
    assert info.sector is None, f"Expected None for sector, got {info.sector}"
    assert info.years_in_operation is None, f"Expected None for years_in_operation, got {info.years_in_operation}"
    assert info.ownership_structure is None, f"Expected None for ownership_structure, got {info.ownership_structure}"

    # Employment must be None or have None total_staff (not 0)
    assert pack.application.employment is None, "Expected employment to be None when no headcount is provided"

    # Financials sales history must be empty (not fake 0 turnover)
    assert pack.application.financials.sales_history == []

    # 2. Provenance ledger must track every missing field as MISSING
    assert "business_info.company_name" in pack.provenance
    assert pack.provenance["business_info.company_name"].status == FieldStatus.MISSING
    assert pack.provenance["business_info.company_name"].value is None

    assert "business_info.tin_number" in pack.provenance
    assert pack.provenance["business_info.tin_number"].status == FieldStatus.MISSING
    assert pack.provenance["business_info.tin_number"].value is None

    assert "employment.total_staff" in pack.provenance
    assert pack.provenance["employment.total_staff"].status == FieldStatus.MISSING
    assert pack.provenance["employment.total_staff"].value is None

    assert "financials.annual_turnover_etb" in pack.provenance
    assert pack.provenance["financials.annual_turnover_etb"].status == FieldStatus.MISSING
    assert pack.provenance["financials.annual_turnover_etb"].value is None

    # 3. Deterministic scoring with missing evidence must award 0 points while preserving MISSING
    scoring_res = score_application(pack=pack, variant=GridVariant.GENERAL_SME)
    assert scoring_res.total_score == 0
    for cs in scoring_res.criteria_scores:
        assert cs.awarded_points == 0
        assert cs.provenance_state in [FieldStatus.MISSING.value, "MISSING", None]


# =============================================================================
# 2. CONTRADICTION PRESERVATION (P1-5)
# =============================================================================

def test_traversal_contradiction_preserves_both_claims():
    """
    Mock audio claims 20 employees but workshop photo shows 5 workers.
    Assert that the resulting provenance for employment.total_staff is CONTRADICTED.
    Assert that the contradiction record retains BOTH values (20 and 5).
    """
    audio = AudioTranscriptExtraction(
        transcript="We have twenty employees actively operating in our workshop.",
        detected_language="English",
        business_name="Abyssinia Craft PLC",
        employee_count=20,
    )
    workshop = WorkshopExtraction(
        is_legible=True,
        estimated_people_present=5,
        visible_machinery=["Looms", "Sewing machine"],
        extraction_notes="Photo shows exactly 5 workers present on site",
    )

    pack = _build_deterministic_pack(
        license_data=None,
        audio_data=audio,
        workshop_data=workshop,
    )

    # Provenance for total_staff must be CONTRADICTED
    assert "employment.total_staff" in pack.provenance
    assert pack.provenance["employment.total_staff"].status == FieldStatus.CONTRADICTED

    # Gaps must capture the disagreement with both numbers
    staff_gap = next((g for g in pack.gaps if g.field_name == "employment.total_staff"), None)
    assert staff_gap is not None
    assert "20" in staff_gap.reason_missing
    assert "5" in staff_gap.reason_missing

    # Contradiction detector must identify the visual discrepancy preserving both claims
    contradictions = detect_contradictions(pack=pack, workshop_data=workshop)
    discrepancy = next(
        (c for c in contradictions if c.kind == ContradictionKind.DISCREPANCY and "photo" in c.claim_b.lower()),
        None,
    )
    assert discrepancy is not None, f"Expected visual discrepancy contradiction, got {contradictions}"
    assert "20" in discrepancy.claim_a, f"Expected 20 in claim_a, got '{discrepancy.claim_a}'"
    assert "5" in discrepancy.claim_b, f"Expected 5 in claim_b, got '{discrepancy.claim_b}'"


# =============================================================================
# 3. FALLBACK HONESTY (P1-6)
# =============================================================================

def test_fallback_honesty_flags_offline_mode(client):
    """
    Mock Gemini to raise an exception during /api/process.
    Assert that SESSION['ai_fallback_used'] is True.
    Assert that GET /api/export injects 'system_status' with OFFLINE_FALLBACK_USED.
    """
    with patch(
        "agents.scorer_agent.call_gemini_with_fallback",
        side_effect=RuntimeError("Google Gemini API Quota Exhausted (HTTP 429)"),
    ), patch(
        "agents.contradiction_agent.call_gemini_with_fallback",
        side_effect=RuntimeError("Google Gemini API Quota Exhausted (HTTP 429)"),
    ), patch(
        "extractors.vision_extractor.call_gemini_with_fallback",
        side_effect=RuntimeError("Google Gemini API Quota Exhausted (HTTP 429)"),
    ), patch(
        "extractors.workshop_extractor.call_gemini_with_fallback",
        side_effect=RuntimeError("Google Gemini API Quota Exhausted (HTTP 429)"),
    ), patch(
        "extractors.config.call_gemini_with_fallback",
        side_effect=RuntimeError("Google Gemini API Quota Exhausted (HTTP 429)"),
    ):
        resp = client.post("/api/process", files={})
        assert resp.status_code == 200

    # Flag must be explicitly recorded in SESSION
    assert SESSION.get("ai_fallback_used") is True

    # Export payload must explicitly declare offline fallback
    export_resp = client.get("/api/export")
    assert export_resp.status_code == 200
    export_data = export_resp.json()

    assert "system_status" in export_data
    assert "OFFLINE_FALLBACK_USED" in export_data["system_status"]
    assert "deterministic" in export_data["system_status"].lower()


# =============================================================================
# 4. TEMPLATE RENDERING VERIFICATION
# =============================================================================

def test_step3_renders_not_established_and_fallback_banner(client):
    """
    Verify that Step 3 template renders 'Not Established' for missing fields
    and displays the amber fallback banner when offline fallback mode is active.
    """
    SESSION["processed"] = True
    SESSION["digital_twin_data"] = {}
    SESSION["pack_res"] = None
    SESSION["ai_fallback_used"] = True

    resp = client.get("/wizard/3")
    assert resp.status_code == 200
    # Must render Not Established
    assert "Not Established" in resp.text
    assert "null (Missing)" in resp.text
    # Must render the offline fallback banner
    assert "System operated in offline fallback mode" in resp.text
