"""
Integration tests for TeraGrant live persistence wiring and review audit trail (Batch H).
Verifies:
1. Startup table initialization via FastAPI lifespan.
2. /api/process persistence of ApplicationRecord, ExtractedFieldRecord, and CriterionScoreRecord.
3. /api/review endpoint persistence and HTTP 404 handling.
4. /api/applications listing proving data survival.
5. Foreign-key cascade deletion through SQLite.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.server import app, SESSION
from app.database import engine, SessionLocal, init_db
from app.models import (
    ApplicationRecord,
    EvidenceRecord,
    ExtractedFieldRecord,
    CriterionScoreRecord,
    ReviewRecord,
)
from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction
from agents.mapper_agent import _build_deterministic_pack
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
}


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure tables exist, clear applications table, and preserve SESSION state."""
    init_db()
    db = SessionLocal()
    try:
        db.query(ApplicationRecord).delete()
        db.commit()
    finally:
        db.close()

    SESSION.clear()
    SESSION.update(INITIAL_SESSION_STATE)
    yield
    SESSION.clear()
    SESSION.update(INITIAL_SESSION_STATE)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def make_test_pack_and_score(
    name: str = "Tana Agro Processing PLC",
    tin: str = "1234567890",
    staff: int = 15,
    location: str = "Bahir Dar",
    revenue: float = 650000.0,
):
    """Helper to construct a deterministic pack and valid 9-criterion score."""
    lic = LicenseExtraction(
        business_name=name,
        tin_number=tin,
        location=location,
        is_legible=True,
    )
    aud = AudioTranscriptExtraction(
        transcript=f"We are {name} operating in {location} with {staff} full-time workers and {revenue} Birr sales.",
        detected_language="English",
        business_name=name,
        employee_count=staff,
        location=location,
        financial_figures=[f"{revenue} Birr"],
    )
    pack = _build_deterministic_pack(license_data=lic, audio_data=aud, workshop_data=None)
    scoring = score_application(pack=pack, variant=GridVariant.GENERAL_SME)
    return pack, scoring, lic, aud


# =============================================================================
# 1. STARTUP INITIALIZATION TEST
# =============================================================================

def test_startup_initializes_db():
    """Verify that importing the server and triggering startup creates all tables."""
    with TestClient(app):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {
            "applications",
            "evidence_records",
            "extracted_fields",
            "criterion_scores",
            "review_records",
        }
        assert expected.issubset(tables), f"Missing tables in DB: {expected - tables}"


# =============================================================================
# 2. PERSISTENCE IN /api/process TEST
# =============================================================================

def test_process_persists_application_and_scores(client):
    """
    Mock the extraction/scoring pipeline to return a known pack and scoring result.
    POST to /api/process.
    Query the DB directly to assert that 1 ApplicationRecord, multiple ExtractedFieldRecords,
    and 9 CriterionScoreRecords were created.
    Assert that the CriterionScoreRecord contains the rule_applied and provenance_cap_applied audit trail.
    """
    pack, scoring, lic, aud = make_test_pack_and_score(
        name="Abyssinia Spice Mill PLC",
        tin="0098765432",
        staff=15,
        location="Hawassa",
    )

    with patch("app.server.generate_application_pack", return_value=pack), \
         patch("app.server.score_application", return_value=scoring), \
         patch("app.server.run_intake_parallel", return_value=(None, lic, None, {}, [])):

        resp = client.post("/api/process", files={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        app_id = data.get("application_id")
        assert app_id is not None
        assert SESSION.get("current_application_id") == app_id

    # Query the DB directly
    db = SessionLocal()
    try:
        # 1 ApplicationRecord
        app_rec = db.query(ApplicationRecord).filter_by(id=app_id).first()
        assert app_rec is not None
        assert app_rec.applicant_name == "Abyssinia Spice Mill PLC"
        assert app_rec.grid_variant == "GENERAL_SME"
        assert app_rec.total_score == scoring.total_score
        assert app_rec.status == "EVALUATED"

        # Multiple ExtractedFieldRecords
        fields = db.query(ExtractedFieldRecord).filter_by(application_id=app_id).all()
        assert len(fields) >= 3
        field_names = {f.field_name for f in fields}
        assert "business_info.company_name" in field_names
        assert "employment.total_staff" in field_names

        # Exactly 9 CriterionScoreRecords
        criteria_scores = db.query(CriterionScoreRecord).filter_by(application_id=app_id).all()
        assert len(criteria_scores) == 9

        # Audit trail assertions
        job_score = next(cs for cs in criteria_scores if cs.criterion == "JOB_CREATION")
        assert job_score.rule_applied is not None
        assert "EMPLOYEE_BAND" in job_score.rule_applied
        assert job_score.provenance_cap_applied is not None
        assert job_score.evidence_value == "15"
        assert job_score.awarded_points > 0
        assert job_score.max_points == 20
    finally:
        db.close()


# =============================================================================
# 3. REVIEW ENDPOINT TEST
# =============================================================================

def test_review_endpoint_persists_decision(client):
    """
    Create an application via /api/process.
    POST to /api/review with a decision and notes.
    Query the DB to assert the ReviewRecord exists and is linked to the correct application.
    """
    pack, scoring, lic, aud = make_test_pack_and_score(
        name="Awash Agro Export PLC",
        tin="1122334455",
        staff=12,
    )

    with patch("app.server.generate_application_pack", return_value=pack), \
         patch("app.server.score_application", return_value=scoring), \
         patch("app.server.run_intake_parallel", return_value=(None, lic, None, {}, [])):

        resp = client.post("/api/process", files={})
        assert resp.status_code == 200
        app_id = resp.json()["application_id"]

    # POST to /api/review
    review_payload = {
        "application_id": app_id,
        "decision": "APPROVED",
        "notes": "Verified export license and audited payroll records.",
    }
    rev_resp = client.post("/api/review", json=review_payload)
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["status"] == "success"
    review_id = rev_data["review_id"]

    # Query DB directly
    db = SessionLocal()
    try:
        rev_rec = db.query(ReviewRecord).filter_by(id=review_id).first()
        assert rev_rec is not None
        assert rev_rec.application_id == app_id
        assert rev_rec.reviewer_decision == "APPROVED"
        assert rev_rec.notes == "Verified export license and audited payroll records."
        assert rev_rec.timestamp is not None

        # Verify relationship from ApplicationRecord
        app_rec = db.query(ApplicationRecord).filter_by(id=app_id).first()
        assert len(app_rec.reviews) == 1
        assert app_rec.reviews[0].id == review_id
    finally:
        db.close()


def test_review_endpoint_returns_404_for_nonexistent_application(client):
    """POST /api/review with an invalid or non-existent application_id returns HTTP 404."""
    resp = client.post(
        "/api/review",
        json={
            "application_id": "00000000-0000-0000-0000-000000000000",
            "decision": "APPROVED",
            "notes": "Nonexistent app",
        },
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# =============================================================================
# 4. APPLICATIONS LIST ENDPOINT TEST
# =============================================================================

def test_applications_list_endpoint(client):
    """
    Process two applications.
    GET /api/applications and assert it returns a list of length >= 2 with the correct names and scores.
    """
    pack1, scoring1, lic1, _ = make_test_pack_and_score(name="Enterprise Alpha", staff=10)
    pack2, scoring2, lic2, _ = make_test_pack_and_score(name="Enterprise Beta", staff=20)

    with patch("app.server.generate_application_pack", side_effect=[pack1, pack2]), \
         patch("app.server.score_application", side_effect=[scoring1, scoring2]), \
         patch("app.server.run_intake_parallel", side_effect=[(None, lic1, None, {}, []), (None, lic2, None, {}, [])]):

        resp1 = client.post("/api/process", files={})
        assert resp1.status_code == 200

        resp2 = client.post("/api/process", files={})
        assert resp2.status_code == 200

    # GET /api/applications
    list_resp = client.get("/api/applications")
    assert list_resp.status_code == 200
    apps_list = list_resp.json()

    assert len(apps_list) >= 2
    names = [a["applicant_name"] for a in apps_list]
    assert "Enterprise Alpha" in names
    assert "Enterprise Beta" in names

    # Assert dictionary structure
    for item in apps_list:
        assert "id" in item
        assert "applicant_name" in item
        assert "total_score" in item
        assert "status" in item
        assert "created_at" in item


# =============================================================================
# 5. CASCADE DELETION TEST
# =============================================================================

def test_cascade_delete_application(client):
    """
    Create an application, then delete the ApplicationRecord directly via DB session.
    Assert that all associated ExtractedFieldRecords and CriterionScoreRecords are automatically deleted
    (verifying the ON DELETE CASCADE pragma).
    """
    pack, scoring, lic, _ = make_test_pack_and_score(name="Cascade Target Enterprise", staff=8)

    with patch("app.server.generate_application_pack", return_value=pack), \
         patch("app.server.score_application", return_value=scoring), \
         patch("app.server.run_intake_parallel", return_value=(None, lic, None, {}, [])):

        resp = client.post("/api/process", files={})
        assert resp.status_code == 200
        app_id = resp.json()["application_id"]

    # Also record a review decision
    client.post(
        "/api/review",
        json={"application_id": app_id, "decision": "REJECTED", "notes": "Cascade verification test."},
    )

    db = SessionLocal()
    try:
        # Verify records exist before delete
        assert db.query(ApplicationRecord).filter_by(id=app_id).count() == 1
        assert db.query(ExtractedFieldRecord).filter_by(application_id=app_id).count() > 0
        assert db.query(CriterionScoreRecord).filter_by(application_id=app_id).count() == 9
        assert db.query(ReviewRecord).filter_by(application_id=app_id).count() == 1

        # Delete parent ApplicationRecord
        app_to_del = db.query(ApplicationRecord).filter_by(id=app_id).first()
        db.delete(app_to_del)
        db.commit()

        # Assert cascade deletion purged all children
        assert db.query(ApplicationRecord).filter_by(id=app_id).count() == 0
        assert db.query(ExtractedFieldRecord).filter_by(application_id=app_id).count() == 0
        assert db.query(CriterionScoreRecord).filter_by(application_id=app_id).count() == 0
        assert db.query(ReviewRecord).filter_by(application_id=app_id).count() == 0
    finally:
        db.close()
