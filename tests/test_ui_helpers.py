"""
Unit tests for deterministic UI Helpers (Batch 24).
"""

from app.ui_helpers import evidence_pct, row_status, kpi_stats
from schemas.provenance_schema import FieldStatus, FieldProvenance


def test_evidence_pct_empty_and_populated():
    assert evidence_pct({}) == 0

    prov = {
        "f1": {"status": "DOCUMENT_VERIFIED"},
        "f2": {"status": "APPLICANT_STATED"},
        "f3": {"status": "MISSING"},
        "f4": {"status": "AI_INFERRED"},
    }
    # Non-missing: 3 (f1, f2, f4). Verified: 1 (f1) -> 1/3 = 33%
    assert evidence_pct(prov) == 33

    prov_all_verified = {
        "f1": FieldProvenance(field_path="p1", status=FieldStatus.DOCUMENT_VERIFIED, confidence=0.95, source_type="license", evidence_snippet="test"),
        "f2": FieldProvenance(field_path="p2", status=FieldStatus.DOCUMENT_VERIFIED, confidence=0.95, source_type="license", evidence_snippet="test"),
    }
    assert evidence_pct(prov_all_verified) == 100


def test_row_status_classification():
    assert row_status(True, 85) == "Shortlisted"
    assert row_status(True, 70) == "Shortlisted"
    assert row_status(True, 65) == "Reviewed"
    assert row_status(True, 55) == "Reviewed"
    assert row_status(True, 54) == "Pending"
    assert row_status(False, 90) == "Pending"


def test_kpi_stats_calculation():
    batch = [
        {"is_eligible": True, "total_score": 80, "contradictions": []},
        {"is_eligible": True, "total_score": 60, "contradictions": [{"explanation": "err"}]},
        {"is_eligible": False, "total_score": 40, "contradictions": [{"explanation": "crit"}]},
    ]
    stats = kpi_stats(batch)
    assert stats["total_applications"] == 3
    assert stats["eligible"] == 1
    assert stats["needs_review"] == 1
    assert stats["ineligible"] == 1
    assert stats["average_score"] == 60
    assert stats["contradictions"] == 2
