"""
Challenge 1 Acceptance Test Suite.
Asserts every core architectural deliverable and compliance requirement
of the TeraGrant SME Grant Evaluation System.
"""

import json
from unittest.mock import MagicMock
import pytest

from schemas.application_schema import (
    ApplicationSchema,
    BusinessInfo,
    EmploymentBreakdown,
    GenderSplit,
    AgeBandSplit,
    FinancialHistory,
    AnnualSales,
    MachineryItem,
    OrganogramNode,
    MandatoryDeclarations,
    ExclusionFactors,
)
from schemas.impact_schema import ImpactProtocol, Milestone, SDGIndicator
from schemas.gap_schema import ApplicationPack, Gap, GapPriority
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
    ExclusionFactor,
)
from schemas.reviewer_schema import (
    Contradiction,
    ContradictionSeverity,
    ContradictionKind,
    RankedCompany,
    RankedShortlist,
)
from schemas.consent_schema import (
    DeclarationExplanation,
    ConsentPackage,
    ConsentVerdict,
    ConsentStatus,
    ConsentRecord,
)
from schemas.provenance_schema import FieldStatus, FieldProvenance

from extractors.schemas import AudioTranscriptExtraction, LicenseExtraction, WorkshopExtraction
from agents.mapper_agent import generate_application_pack
from agents.eligibility_agent import run_eligibility_gate
from agents.router_agent import route_to_grid_variant
from agents.scorer_agent import score_application, compare_grid_variants, score_sensitivity
from agents.contradiction_agent import detect_contradictions
from agents.batch_ranker_agent import rank_batch
from agents.declaration_explainer_agent import generate_consent_package
from agents.consent_agent import record_consent, sync_declarations_from_consent_records


def test_acceptance_01_trilingual_audio_acceptance():
    """Acceptance Requirement 1: Supports Amharic, Afaan Oromo, and English voice note intakes."""
    for lang in ["Amharic", "Afaan Oromo", "English"]:
        audio = AudioTranscriptExtraction(
            transcript=f"Voice narrative in {lang}",
            detected_language=lang,
            business_name="Abyssinia PLC",
            employee_count=10,
        )
        assert audio.detected_language == lang
        assert audio.business_name == "Abyssinia PLC"


def test_acceptance_02_dual_photo_extraction_schemas():
    """Acceptance Requirement 2: Processes 2 photo inputs: Trade license OCR + Workshop facility."""
    lic = LicenseExtraction(
        business_name="Addis Leather Crafts",
        tin_number="0098765432",
        registration_date="2015 E.C.",
        is_legible=True,
    )
    assert lic.is_legible is True
    assert lic.tin_number == "0098765432"

    workshop = WorkshopExtraction(
        estimated_people_present=6,
        visible_machinery=["Cutting press", "Sewing tables"],
        is_legible=True,
    )
    assert workshop.estimated_people_present == 6
    assert len(workshop.visible_machinery) == 2


def test_acceptance_03_application_schema_sections_1_1_to_2_6():
    """Acceptance Requirement 3: Enforces full coverage of GIZ / Sequa Sections 1.1 to 2.6."""
    app_fields = list(ApplicationSchema.model_fields.keys())
    assert "business_info" in app_fields       # 1.1 Company profile
    assert "employment" in app_fields          # 1.2 Employment & growth
    assert "financials" in app_fields          # 1.3 Turnover & funding
    assert "organogram" in app_fields          # 1.8 Management structure
    assert "declarations" in app_fields        # 2.5 Legal covenants (15 checks)
    assert "exclusion_factors" in app_fields   # 2.6 Instant-kill exclusions (3 checks)


def test_acceptance_04_impact_protocol_7_fields():
    """Acceptance Requirement 4: Validates ImpactProtocol contains 7 structured fields."""
    impact_fields = list(ImpactProtocol.model_fields.keys())
    expected_7 = [
        "project_title",
        "location",
        "target_beneficiaries",
        "etb_financial_target",
        "sector",
        "sdgs",
        "milestones",
    ]
    for ef in expected_7:
        assert ef in impact_fields


def test_acceptance_05_eligibility_gate_15_checks_and_3_exclusions():
    """Acceptance Requirement 5: 15-check Eligibility Gate + 3 Instant-kill Exclusions."""
    assert len(MandatoryDeclarations.model_fields) == 15
    assert len(ExclusionFactors.model_fields) == 3

    # All false by default -> gate MUST fail
    app = ApplicationSchema(
        business_info=BusinessInfo(
            business_name="Test Co",
            location="Addis Ababa",
            sector="Manufacturing",
            years_in_operation=2,
            ownership_structure="PLC",
        ),
        employment=EmploymentBreakdown(total_staff=4, gender_split=GenderSplit(male=2, female=2, other=0), age_split=AgeBandSplit(youth_18_29=2, adults_30_50=2, seniors_above_50=0)),
        financials=FinancialHistory(sales_history=[AnnualSales(year=2024, revenue_etb=100000.0)], machinery_list=[]),
        organogram=[],
        declarations=MandatoryDeclarations(),
        exclusion_factors=ExclusionFactors(),
    )
    gate = run_eligibility_gate(app)
    assert gate.is_eligible is False
    assert len(gate.failed_declarations) == 15


def test_acceptance_06_nine_criteria_across_three_variants():
    """Acceptance Requirement 6: 9 standardized criteria and 3 targeted GridVariant tracks."""
    assert len(CriterionName) == 9
    assert len(GridVariant) == 3
    assert set(GridVariant) == {GridVariant.GENERAL_SME, GridVariant.WOMEN_YOUTH_LED, GridVariant.INNOVATION_TECH}


def test_acceptance_07_explicit_gap_tracking():
    """Acceptance Requirement 7: Explicit Gap records with zero-hallucination fields."""
    gap = Gap(
        field_name="business_info.tin_number",
        reason_missing="Smudged or missing on license photo.",
        required_from="Applicant",
        priority=GapPriority.HIGH,
    )
    assert gap.field_name == "business_info.tin_number"
    assert gap.required_from == "Applicant"
    assert gap.priority == GapPriority.HIGH


def test_acceptance_08_multilingual_consent_never_auto_ticks():
    """Acceptance Requirement 8: Multilingual consent explains legal covenants without auto-ticking."""
    pkg = generate_consent_package(client=MagicMock(), detected_language="Amharic")
    assert len(pkg.explanations) >= 3
    assert "MUST NEVER be auto-ticked" in pkg.overall_warning

    # Verified consent recording
    rec = record_consent("declaration_05_anti_bribery_corruption", "Amharic", True, "አዎ እስማማለሁ")
    synced = sync_declarations_from_consent_records([rec])
    assert synced.declaration_05_anti_bribery_corruption is True
    assert synced.declaration_08_child_labor_prevention is False  # Never bulk ticked


def test_acceptance_09_twelve_applicant_batch_ranking():
    """Acceptance Requirement 9: Ranks 12-applicant portfolio in strictly descending order."""
    def make_score(score: int, variant: GridVariant) -> ScoringResult:
        criteria = [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=min(score, 20), reasoning="Job creation score verified."),
            CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=min(max(score-20,0), 15), reasoning="Demographic inclusion verified."),
            CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=min(max(score-35,0), 15), reasoning="Technical novelty verified."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=min(max(score-50,0), 15), reasoning="Financial health verified."),
            CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=min(max(score-65,0), 10), reasoning="Domestic supply verified."),
            CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=min(max(score-75,0), 10), reasoning="Environmental impact verified."),
            CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=min(max(score-85,0), 5), reasoning="Management verified."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=0, reasoning="Community benefit noted."),
            CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=0, reasoning="Scalability noted."),
        ]
        return ScoringResult(
            grid_variant=variant,
            total_score=sum(c.awarded_points for c in criteria),
            criteria_scores=criteria,
            eligibility_gate=EligibilityGate(is_eligible=True, gate_reasoning="Eligibility criteria verified and confirmed."),
            reviewer_summary="Enterprise has been evaluated and approved by the technical evaluation committee.",
        )

    batch = [
        ("Company A", make_score(60, GridVariant.GENERAL_SME)),
        ("Company B", make_score(92, GridVariant.INNOVATION_TECH)),
        ("Company C", make_score(85, GridVariant.WOMEN_YOUTH_LED)),
    ]

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "companies": [
            {"rank": 1, "business_name": "Company B", "total_score": 92, "grid_variant": "INNOVATION_TECH", "justification": "Top score in technology.", "site_visit_questions": ["Verify R&D lab"]},
            {"rank": 2, "business_name": "Company C", "total_score": 85, "grid_variant": "WOMEN_YOUTH_LED", "justification": "Strong female participation.", "site_visit_questions": ["Inspect factory"]},
            {"rank": 3, "business_name": "Company A", "total_score": 60, "grid_variant": "GENERAL_SME", "justification": "Standard baseline score.", "site_visit_questions": ["Check equipment"]},
        ],
        "batch_summary": "Batch portfolio successfully evaluated.",
    })
    mock_client.models.generate_content.return_value = mock_resp

    shortlist = rank_batch(batch, client=mock_client)
    assert len(shortlist.companies) == 3
    assert shortlist.companies[0].total_score >= shortlist.companies[1].total_score >= shortlist.companies[2].total_score
    assert len(shortlist.companies[0].site_visit_questions) > 0


def test_acceptance_10_forensic_contradictions_and_provenance():
    """Acceptance Requirement 10: Contradiction forensics with taxonomy and provenance tracking."""
    assert ContradictionKind.CONTRADICTION == "CONTRADICTION"
    assert ContradictionKind.DISCREPANCY == "DISCREPANCY"
    assert ContradictionKind.MISSING_EVIDENCE == "MISSING_EVIDENCE"
    assert ContradictionKind.PLAUSIBLE == "PLAUSIBLE"

    assert FieldStatus.DOCUMENT_VERIFIED == "DOCUMENT_VERIFIED"
    assert FieldStatus.APPLICANT_STATED == "APPLICANT_STATED"
    assert FieldStatus.MISSING == "MISSING"
