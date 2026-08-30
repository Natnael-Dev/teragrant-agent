"""
Unit tests for Truth Layer Backend (Batch 22).
Covers Mapper Resilience, Provenance Ledger, Contradiction Taxonomy,
Consent Audit Records, Impact Builder, Transparency Engines, and Parallel Intake Orchestration.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction, WorkshopExtraction
from schemas.gap_schema import ApplicationPack, GapPriority
from schemas.provenance_schema import FieldStatus, FieldProvenance
from schemas.reviewer_schema import ContradictionKind, ContradictionSeverity, Contradiction
from schemas.consent_schema import ConsentVerdict, ConsentStatus, ConsentRecord
from schemas.scoring_schema import GridVariant, CriterionName, CriterionScore, ScoringResult, EligibilityGate
from schemas.impact_schema import SDGIndicator

from agents.mapper_agent import generate_application_pack, _build_deterministic_pack
from agents.consent_agent import (
    evaluate_verdict,
    record_consent,
    revoke_consent,
    sync_declarations_from_consent_records,
)
from agents.impact_builder import build_impact_protocol, IMPACT_QUESTIONS
from agents.scorer_agent import (
    score_application,
    compare_grid_variants,
    score_sensitivity,
    submission_readiness,
    reproducibility_check,
)
from agents.contradiction_agent import detect_contradictions
from agents.intake_orchestrator import run_intake_parallel


# =============================================================================
# 1. MAPPER RESILIENCE TESTS (FIX 1 & FIX 2)
# =============================================================================

def test_mapper_audio_only_produces_populated_app_with_license_gaps():
    """Test 1a: Audio-only intake produces populated ApplicationSchema with license fields as Gaps."""
    audio = AudioTranscriptExtraction(
        transcript="My business is Selam Weaving in Hawassa. We have 10 workers and earn 300,000 Birr yearly.",
        detected_language="English",
        business_name="Selam Weaving",
        employee_count=10,
        product_type="Handloom Textiles",
        location="Hawassa",
        financial_figures=["300,000 Birr"],
        impact_summary="Textile manufacturing.",
    )
    # License is None or unreadable
    license_data = LicenseExtraction(is_legible=False, extraction_notes="No license file provided")

    pack = _build_deterministic_pack(license_data, audio, None)

    assert pack.application is not None
    assert pack.application.business_info.business_name == "Selam Weaving"
    assert pack.application.employment.total_staff == 10
    assert pack.application.financials.sales_history[0].revenue_etb == 300000.0

    # License fields are tracked as Gaps
    tin_gap = next((g for g in pack.gaps if "tin_number" in g.field_name), None)
    assert tin_gap is not None
    assert tin_gap.priority == GapPriority.HIGH

    # Provenance ledger checks
    assert "business_info.company_name" in pack.provenance
    assert pack.provenance["business_info.company_name"].status == FieldStatus.APPLICANT_STATED
    assert pack.provenance["business_info.tin_number"].status == FieldStatus.MISSING


def test_mapper_green_square_license_plus_audio_yields_audio_facts():
    """Test 1b: Green-square unreadable license + good audio still yields business name and staff."""
    license_data = LicenseExtraction(
        is_legible=False,
        business_name=None,
        tin_number=None,
        extraction_notes="Uploaded image is a solid green square",
    )
    audio = AudioTranscriptExtraction(
        transcript="Hello I am Almaz Bekele from Almaz Spice Mill with 8 workers in Bahir Dar.",
        detected_language="English",
        business_name="Almaz Spice Mill",
        employee_count=8,
        product_type="Spices",
        location="Bahir Dar",
        financial_figures=["450,000 Birr"],
    )

    pack = generate_application_pack(license_data=license_data, audio_data=audio, client=MagicMock())

    assert pack.application is not None
    assert pack.application.business_info.business_name == "Almaz Spice Mill"
    assert pack.application.employment.total_staff == 8
    assert pack.impact is not None
    assert len(pack.gaps) >= 1


# =============================================================================
# 2. CONTRADICTION TAXONOMY TESTS (FIX 3)
# =============================================================================

def test_contradiction_taxonomy_assignment():
    """Test 2: Verifies math errors get CONTRADICTION kind and photo headcount gets DISCREPANCY kind."""
    audio = AudioTranscriptExtraction(
        transcript="We have 10 workers.",
        detected_language="English",
        employee_count=10,
    )
    workshop = WorkshopExtraction(
        estimated_people_present=2,  # Discrepancy: 10 vs 2
        visible_machinery=["Looms"],
        is_legible=True,
    )
    license_data = LicenseExtraction(is_legible=True, business_name="Tana Weavers", tin_number="1234567890")

    pack = _build_deterministic_pack(license_data, audio, workshop)
    # Artificially create headcount math mismatch in gender split
    pack.application.employment.gender_split.male = 4
    pack.application.employment.gender_split.female = 4  # Sum = 8, total = 10

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"contradictions": []})
    mock_client.models.generate_content.return_value = mock_resp

    contras = detect_contradictions(pack=pack, workshop_data=workshop, client=mock_client)

    math_c = next((c for c in contras if "Mathematical contradiction" in c.explanation), None)
    assert math_c is not None
    assert math_c.kind == ContradictionKind.CONTRADICTION
    assert math_c.severity == ContradictionSeverity.CRITICAL

    photo_c = next((c for c in contras if "Visual evidence discrepancy" in c.explanation), None)
    assert photo_c is not None
    assert photo_c.kind == ContradictionKind.DISCREPANCY
    assert photo_c.severity == ContradictionSeverity.WARNING


# =============================================================================
# 3. CONSENT AUDIT & ISOLATION TESTS (FIX 4)
# =============================================================================

def test_consent_multilingual_verdict_parsing():
    """Test 3a: Multilingual verbal affirmation/rejection parsing."""
    assert evaluate_verdict("Yes, I fully agree") == ConsentVerdict.YES
    assert evaluate_verdict("አዎ እስማማለሁ") == ConsentVerdict.YES
    assert evaluate_verdict("Eeyyee nan walii gala") == ConsentVerdict.YES

    assert evaluate_verdict("No, I refuse") == ConsentVerdict.NO
    assert evaluate_verdict("አይ አልስማማም") == ConsentVerdict.NO
    assert evaluate_verdict("Lakki") == ConsentVerdict.NO

    assert evaluate_verdict("Maybe next month") == ConsentVerdict.UNCLEAR


def test_consent_record_and_isolation():
    """Test 3b: One YES consent record does NOT mark other declarations."""
    rec = record_consent(
        declaration_id="declaration_05_anti_bribery_corruption",
        language="Amharic",
        explanation_delivered=True,
        response_transcript="አዎ እስማማለሁ",
    )
    assert rec.status == ConsentStatus.ACTIVE
    assert rec.response_verdict == ConsentVerdict.YES

    # Project to Declarations
    synced = sync_declarations_from_consent_records([rec])
    assert synced.declaration_05_anti_bribery_corruption is True
    # Crucial: all other declarations remain False!
    assert synced.declaration_01_legal_compliance is False
    assert synced.declaration_08_child_labor_prevention is False
    assert synced.declaration_02_truthful_information is False

    # Revoke consent
    revoked = revoke_consent(rec, reason="Applicant withdrew statement")
    assert revoked.status == ConsentStatus.REVOKED

    synced_after = sync_declarations_from_consent_records([revoked])
    assert synced_after.declaration_05_anti_bribery_corruption is False


# =============================================================================
# 4. IMPACT BUILDER TESTS (FIX 5)
# =============================================================================

def test_impact_builder_milestones_and_sdgs():
    """Test 4: Impact builder creates evidence-based milestones and maps SDGs."""
    answers = {
        "business_name": "Bahir Dar Agro Mill",
        "impact.target_beneficiaries": 250,
        "requested_etb": 600000.0,
        "sector": "Grain Processing",
        "impact.procurement_items": "Electric Milling Machinery",
        "impact.verification_milestones": "Commercial sales invoices and warranty cards",
    }
    audio_facts = {
        "location": "Bahir Dar",
        "product_type": "Grain Flour & Spices",
    }

    protocol = build_impact_protocol(answers_dict=answers, audio_facts=audio_facts)

    assert protocol.target_beneficiaries == 250
    assert protocol.etb_financial_target == 600000.0
    assert len(protocol.milestones) == 3
    assert SDGIndicator.SDG_02_ZERO_HUNGER in protocol.sdgs or SDGIndicator.SDG_08_DECENT_WORK in protocol.sdgs
    assert protocol.milestones[0].verification_evidence == "Commercial sales invoices and warranty cards"


# =============================================================================
# 5. TRANSPARENCY ENGINES TESTS (FIX 6)
# =============================================================================

def test_transparency_score_sensitivity_and_readiness():
    """Test 5: Sensitivity analysis calculates recoverable points; readiness identifies blockers."""
    # Build dummy pack with 2 gaps
    audio = AudioTranscriptExtraction(transcript="Test transcript", detected_language="English")
    pack = _build_deterministic_pack(None, audio, None)

    scores = [
        CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=12, reasoning="Job creation potential verified."),
        CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=8, reasoning="Gender and youth participation noted."),
        CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=10, reasoning="Technical innovation verified."),
        CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=6, reasoning="Financial records penalized due to gap."),
        CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=6, reasoning="Domestic supply integration noted."),
        CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=6, reasoning="Environmental SDG alignment verified."),
        CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=3, reasoning="Management structure noted."),
        CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=3, reasoning="Community benefits observed."),
        CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=3, reasoning="Scalability prospects evaluated."),
    ]
    scoring_res = ScoringResult(
        grid_variant=GridVariant.GENERAL_SME,
        total_score=sum(c.awarded_points for c in scores),
        criteria_scores=scores,
        eligibility_gate=EligibilityGate(is_eligible=False, gate_reasoning="Missing declarations and unconfirmed permits."),
        reviewer_summary="Reviewer technical evaluation summary across all nine criteria.",
    )

    # 1. Sensitivity
    sensitivity = score_sensitivity(pack, scoring_res)
    assert sensitivity["current_score"] == 57
    assert sensitivity["potential_total"] > 57
    assert len(sensitivity["sensitivities"]) > 0

    # 2. Readiness
    readiness = submission_readiness(pack, scoring_res.eligibility_gate, contradictions=[])
    assert readiness["is_ready"] is False
    assert len(readiness["blockers"]) > 0

    # 3. Reproducibility
    with patch("agents.scorer_agent.score_application", return_value=scoring_res):
        repro = reproducibility_check(pack, GridVariant.GENERAL_SME, iterations=2)
        assert repro["is_identical"] is True


# =============================================================================
# 6. PARALLEL INTAKE ORCHESTRATOR TESTS (FIX 7)
# =============================================================================

def test_intake_orchestrator_parallel_timing_and_graceful_degradation():
    """Test 6: Parallel intake runs concurrently and degrades gracefully when files are missing."""
    with patch("agents.intake_orchestrator.extract_audio_story", return_value=AudioTranscriptExtraction(transcript="Test voice", detected_language="English")), \
         patch("agents.intake_orchestrator.extract_license_data", side_effect=RuntimeError("Corrupted license file")), \
         patch("agents.intake_orchestrator.extract_workshop_data", return_value=WorkshopExtraction(is_legible=True)):

        audio, lic, work, timings, gaps = run_intake_parallel(
            voice_path="mock_voice.mp3",
            license_path="corrupt_license.jpg",
            workshop_path="valid_workshop.jpg",
        )

        assert audio is not None
        assert lic is None  # Degraded gracefully
        assert work is not None
        assert len(gaps) == 1
        assert "trade_license_document" in gaps[0].field_name
        assert "total_parallel_seconds" in timings
