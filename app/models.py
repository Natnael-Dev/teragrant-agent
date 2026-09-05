"""
SQLAlchemy ORM Models for TeraGrant Persistence Layer.
Maps domain schemas (applications, multimodal evidence, extracted facts,
deterministic scoring audit trails, and committee reviews) to relational tables.

Implements strict cascade deletion and foreign key integrity.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    """Generates a standard UUID string for primary keys."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Returns current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class ApplicationRecord(Base):
    """
    Core persistent entity representing an SME grant application intake.
    """
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    applicant_name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, EVALUATED, APPROVED, REJECTED
    grid_variant = Column(String(50), nullable=True)  # GENERAL_SME, WOMEN_YOUTH_LED, INNOVATION_TECH
    total_score = Column(Integer, nullable=True)

    # Relationships with strict cascade deletion
    evidence = relationship(
        "EvidenceRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    extracted_fields = relationship(
        "ExtractedFieldRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    criteria_scores = relationship(
        "CriterionScoreRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reviews = relationship(
        "ReviewRecord",
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<ApplicationRecord(id='{self.id}', name='{self.applicant_name}', status='{self.status}')>"


class EvidenceRecord(Base):
    """
    Metadata record for verified intake evidence (trade licenses, audio transcripts, site visits).
    Raw binary waveforms are not stored permanently.
    """
    __tablename__ = "evidence_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type = Column(String(50), nullable=False)  # license, audio, workshop, interview
    file_path_or_hash = Column(String(255), nullable=False)  # SHA-256 hash or storage path
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    application = relationship("ApplicationRecord", back_populates="evidence")
    extracted_fields = relationship(
        "ExtractedFieldRecord",
        back_populates="evidence",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<EvidenceRecord(id='{self.id}', source='{self.source_type}')>"


class ExtractedFieldRecord(Base):
    """
    Atomic factual observation extracted from evidence, tagged with epistemic provenance.
    """
    __tablename__ = "extracted_fields"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    provenance_state = Column(String(50), nullable=False)  # DOCUMENT_VERIFIED, APPLICANT_STATED, etc.
    confidence = Column(Float, default=1.0, nullable=False)
    evidence_id = Column(
        String(36),
        ForeignKey("evidence_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    application = relationship("ApplicationRecord", back_populates="extracted_fields")
    evidence = relationship("EvidenceRecord", back_populates="extracted_fields")

    def __repr__(self) -> str:
        return f"<ExtractedFieldRecord(field='{self.field_name}', status='{self.provenance_state}')>"


class CriterionScoreRecord(Base):
    """
    Persistent audit record of a single criterion's deterministic score.
    Captures complete derivation lineage: rule applied, raw evidence, provenance cap, and points.
    """
    __tablename__ = "criterion_scores"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    criterion = Column(String(100), nullable=False)  # CriterionName value
    awarded_points = Column(Integer, nullable=False)
    max_points = Column(Integer, nullable=False)
    rule_applied = Column(String(100), nullable=True)  # e.g., EMPLOYEE_BAND_10_TO_19
    evidence_value = Column(Text, nullable=True)  # Raw evidence used
    provenance_state = Column(String(50), nullable=True)  # DOCUMENT_VERIFIED, APPLICANT_STATED
    provenance_cap_applied = Column(Float, nullable=True)  # 1.0, 0.65, 0.50, 0.0

    # Relationship
    application = relationship("ApplicationRecord", back_populates="criteria_scores")

    def __repr__(self) -> str:
        return (
            f"<CriterionScoreRecord(criterion='{self.criterion}', "
            f"points={self.awarded_points}/{self.max_points}, rule='{self.rule_applied}')>"
        )


class ReviewRecord(Base):
    """
    Formal Investment Committee review decision and qualitative notes.
    """
    __tablename__ = "review_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(
        String(36),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_decision = Column(String(50), nullable=False)  # APPROVED, REJECTED, SITE_VISIT_REQUIRED
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship
    application = relationship("ApplicationRecord", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<ReviewRecord(decision='{self.reviewer_decision}', time='{self.timestamp}')>"
