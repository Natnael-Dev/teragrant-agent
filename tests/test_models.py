"""
Unit tests for TeraGrant SQLite persistence layer and SQLAlchemy ORM models (Batch G).
Verifies table creation, CRUD operations, foreign key enforcement, and cascade deletion.
"""

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.database import Base, init_db, get_db
from app.models import (
    ApplicationRecord,
    EvidenceRecord,
    ExtractedFieldRecord,
    CriterionScoreRecord,
    ReviewRecord,
)


@pytest.fixture
def test_engine():
    """Creates an isolated in-memory SQLite engine with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    init_db(target_engine=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Provides a transactional database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# 1. TABLE CREATION TESTS
# =============================================================================

def test_init_db_creates_all_tables(test_engine):
    """Verify that init_db() creates all 5 domain tables."""
    inspector = inspect(test_engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "applications",
        "evidence_records",
        "extracted_fields",
        "criterion_scores",
        "review_records",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


# =============================================================================
# 2. CRUD TESTS
# =============================================================================

def test_create_and_query_application(db_session):
    """Verify that an ApplicationRecord can be persisted and retrieved."""
    app = ApplicationRecord(
        applicant_name="Sheba CleanTech PLC",
        grid_variant="INNOVATION_TECH",
        total_score=85,
        status="EVALUATED",
    )
    db_session.add(app)
    db_session.commit()

    queried = db_session.query(ApplicationRecord).filter_by(applicant_name="Sheba CleanTech PLC").first()
    assert queried is not None
    assert queried.id == app.id
    assert queried.grid_variant == "INNOVATION_TECH"
    assert queried.total_score == 85
    assert queried.status == "EVALUATED"
    assert queried.created_at is not None


def test_create_complete_hierarchy_with_relationships(db_session):
    """Verify linking evidence, extracted fields, scores, and review records."""
    app = ApplicationRecord(
        applicant_name="Almaz Agro Processing",
        grid_variant="WOMEN_YOUTH_LED",
        total_score=78,
    )
    db_session.add(app)
    db_session.commit()

    evidence = EvidenceRecord(
        application_id=app.id,
        source_type="license",
        file_path_or_hash="sha256:abc123456789",
    )
    db_session.add(evidence)
    db_session.commit()

    field = ExtractedFieldRecord(
        application_id=app.id,
        field_name="employment.total_staff",
        value="12",
        provenance_state="DOCUMENT_VERIFIED",
        confidence=0.98,
        evidence_id=evidence.id,
    )
    db_session.add(field)

    score = CriterionScoreRecord(
        application_id=app.id,
        criterion="JOB_CREATION",
        awarded_points=14,
        max_points=20,
        rule_applied="EMPLOYEE_BAND_10_TO_19",
        evidence_value="12",
        provenance_state="DOCUMENT_VERIFIED",
        provenance_cap_applied=1.0,
    )
    db_session.add(score)

    review = ReviewRecord(
        application_id=app.id,
        reviewer_decision="APPROVED",
        notes="High-impact agro-processing enterprise with strong youth engagement.",
    )
    db_session.add(review)
    db_session.commit()

    # Query via relationships
    retrieved_app = db_session.query(ApplicationRecord).filter_by(id=app.id).first()
    assert len(retrieved_app.evidence) == 1
    assert retrieved_app.evidence[0].source_type == "license"

    assert len(retrieved_app.extracted_fields) == 1
    assert retrieved_app.extracted_fields[0].field_name == "employment.total_staff"
    assert retrieved_app.extracted_fields[0].evidence.id == evidence.id

    assert len(retrieved_app.criteria_scores) == 1
    assert retrieved_app.criteria_scores[0].rule_applied == "EMPLOYEE_BAND_10_TO_19"

    assert len(retrieved_app.reviews) == 1
    assert retrieved_app.reviews[0].reviewer_decision == "APPROVED"


# =============================================================================
# 3. CASCADE DELETION TESTS
# =============================================================================

def test_cascade_deletion_purges_all_child_records(db_session):
    """
    Verify that deleting an ApplicationRecord systematically cascades and deletes
    all associated evidence, extracted fields, criterion scores, and review records.
    """
    app = ApplicationRecord(applicant_name="Ephemeral SME PLC")
    db_session.add(app)
    db_session.commit()

    evidence = EvidenceRecord(
        application_id=app.id,
        source_type="audio",
        file_path_or_hash="sha256:temp_hash",
    )
    db_session.add(evidence)
    db_session.commit()

    field = ExtractedFieldRecord(
        application_id=app.id,
        field_name="location",
        value="Hawassa",
        provenance_state="APPLICANT_STATED",
        confidence=0.85,
        evidence_id=evidence.id,
    )
    score = CriterionScoreRecord(
        application_id=app.id,
        criterion="LOCAL_SUPPLY_CHAIN",
        awarded_points=7,
        max_points=10,
        rule_applied="LOCAL_SUPPLY_CHAIN_SUBSTANTIAL_SOURCING",
        evidence_value="55%",
        provenance_state="APPLICANT_STATED",
        provenance_cap_applied=0.65,
    )
    review = ReviewRecord(
        application_id=app.id,
        reviewer_decision="SITE_VISIT_REQUIRED",
        notes="Inspect processing facility in Hawassa.",
    )
    db_session.add_all([field, score, review])
    db_session.commit()

    # Confirm all child records exist
    app_id = app.id
    assert db_session.query(EvidenceRecord).filter_by(application_id=app_id).count() == 1
    assert db_session.query(ExtractedFieldRecord).filter_by(application_id=app_id).count() == 1
    assert db_session.query(CriterionScoreRecord).filter_by(application_id=app_id).count() == 1
    assert db_session.query(ReviewRecord).filter_by(application_id=app_id).count() == 1

    # Delete parent ApplicationRecord
    db_session.delete(app)
    db_session.commit()

    # Assert complete cascade erasure
    assert db_session.query(ApplicationRecord).filter_by(id=app_id).count() == 0
    assert db_session.query(EvidenceRecord).filter_by(application_id=app_id).count() == 0
    assert db_session.query(ExtractedFieldRecord).filter_by(application_id=app_id).count() == 0
    assert db_session.query(CriterionScoreRecord).filter_by(application_id=app_id).count() == 0
    assert db_session.query(ReviewRecord).filter_by(application_id=app_id).count() == 0


# =============================================================================
# 4. FOREIGN KEY INTEGRITY CONSTRAINT TESTS
# =============================================================================

def test_foreign_key_violation_raises_error(db_session):
    """Verify that inserting a record referencing a non-existent application_id fails."""
    orphan_evidence = EvidenceRecord(
        application_id="non-existent-uuid-12345",
        source_type="license",
        file_path_or_hash="sha256:fake",
    )
    db_session.add(orphan_evidence)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# =============================================================================
# 5. FASTAPI DEPENDENCY GENERATOR TEST
# =============================================================================

def test_get_db_generator():
    """Verify get_db() yields a functional session and closes without error."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        # Check session is active
        assert session.is_active is True
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
