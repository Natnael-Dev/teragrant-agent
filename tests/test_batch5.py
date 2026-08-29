"""
Unit tests for Batch 5: Contradiction Detection, Batch Ranking, and Multilingual Consent.
Verifies pure-Python mathematical contradiction detection, Gemini semantic contradiction parsing,
deterministic batch score ranking, and multilingual verbal consent packages.
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
    MandatoryDeclarations,
    ExclusionFactors,
)
from schemas.impact_schema import ImpactProtocol, SDGIndicator
from schemas.gap_schema import ApplicationPack
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from schemas.reviewer_schema import (
    Contradiction,
    ContradictionSeverity,
    RankedShortlist,
)
from schemas.consent_schema import ConsentPackage
from agents.contradiction_agent import detect_contradictions
from agents.batch_ranker_agent import rank_batch
from agents.declaration_explainer_agent import generate_consent_package


def get_base_application_pack():
    """Helper to build a valid base ApplicationPack."""
    app = ApplicationSchema(
        business_info=BusinessInfo(
            business_name="Bole Garment Factory PLC",
            tin_number="0011223344",
            location="Addis Ababa, Bole Sub-City",
            sector="Textiles & Apparel",
            years_in_operation=4,
            ownership_structure="PLC",
            female_ownership_percentage=55.0,
        ),
        employment=EmploymentBreakdown(
            total_staff=20,
            gender_split=GenderSplit(male=10, female=10, other=0),
            age_split=AgeBandSplit(youth_18_29=12, adults_30_50=8, seniors_above_50=0),
        ),
        financials=FinancialHistory(),
        organogram=[],
        declarations=MandatoryDeclarations(),
        exclusion_factors=ExclusionFactors(),
    )
    impact = ImpactProtocol(
        project_title="Industrial Sewing Machine Upgrades for Export Garments",
        location="Addis Ababa",
        target_beneficiaries=1000,
        etb_financial_target=2000000.0,
        sector="Textiles & Apparel",
        sdgs=[SDGIndicator.SDG_08_DECENT_WORK, SDGIndicator.SDG_05_GENDER_EQUALITY],
        milestones=["Installation of 10 automated sewing stations"],
    )
    return ApplicationPack(application=app, impact=impact, gaps=[])


# =========================================================================
# 1. CONTRADICTION DETECTION TESTS
# =========================================================================

def test_pure_python_math_contradiction_headcount_mismatch():
    """
    Test 1: Mathematical contradiction check in pure Python.
    Constructs an ApplicationPack where gender split sums to 15 (8 male + 7 female),
    but total_staff is 20.
    Asserts a CRITICAL Contradiction is generated without needing LLM reasoning.
    """
    pack = get_base_application_pack()

    # Artificially alter the internal model fields to simulate mismatch in payload
    pack.application.employment.gender_split.male = 8
    pack.application.employment.gender_split.female = 7
    pack.application.employment.total_staff = 20  # Mismatch: 15 vs 20

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({"contradictions": []})
    mock_client.models.generate_content.return_value = mock_response

    contradictions = detect_contradictions(pack=pack, client=mock_client)

    assert len(contradictions) >= 1
    math_contra = next(c for c in contradictions if "headcount" in c.explanation.lower())
    assert math_contra.severity == ContradictionSeverity.CRITICAL
    assert "20" in math_contra.claim_a
    assert "15" in math_contra.claim_b
    assert "Mathematical contradiction" in math_contra.explanation


def test_mocked_semantic_contradiction_license_vs_audio():
    """
    Test 2: Semantic contradiction detected via Gemini analysis.
    License says established in 2024, but audio narrative claims 10 years of operation.
    """
    pack = get_base_application_pack()

    mock_semantic_json = json.dumps({
        "contradictions": [
            {
                "claim_a": "Official Trade License registration date is March 2024 (2016 E.C.)",
                "claim_b": "Applicant stated in audio voice note: 'We have been operating this weaving mill for over 10 years.'",
                "severity": "WARNING",
                "explanation": "Significant narrative discrepancy: Official commercial license indicates enterprise is newly registered (2024), conflicting with 10-year historical operating claims.",
            }
        ]
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_semantic_json
    mock_client.models.generate_content.return_value = mock_response

    contradictions = detect_contradictions(pack=pack, client=mock_client)

    assert len(contradictions) == 1
    semantic_contra = contradictions[0]
    assert semantic_contra.severity == ContradictionSeverity.WARNING
    assert "2024" in semantic_contra.claim_a
    assert "10 years" in semantic_contra.claim_b
    assert "narrative discrepancy" in semantic_contra.explanation.lower()


# =========================================================================
# 2. BATCH RANKER TESTS
# =========================================================================

def test_batch_ranker_sorting_and_shortlist_generation():
    """
    Test 3: Pure Python sorting of 3 applications with scores 50, 90, and 75.
    Asserts:
    1. Shortlist output is sorted strictly descending by total_score: 90 -> 75 -> 50.
    2. Assigned ranks are strictly 1, 2, and 3.
    """
    def make_scoring_result(score: int, variant: GridVariant) -> ScoringResult:
        # Build 9 valid criteria scores summing to score
        scores = [
            CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=min(score, 20), reasoning="Valid score awarded for jobs."),
            CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=15, awarded_points=min(max(score - 20, 0), 15), reasoning="Valid score awarded for gender."),
            CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=15, awarded_points=min(max(score - 35, 0), 15), reasoning="Valid score awarded for innovation."),
            CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=15, awarded_points=min(max(score - 50, 0), 15), reasoning="Valid score awarded for finances."),
            CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=min(max(score - 65, 0), 10), reasoning="Valid score awarded for supply."),
            CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=min(max(score - 75, 0), 10), reasoning="Valid score awarded for SDG."),
            CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=min(max(score - 85, 0), 5), reasoning="Valid score awarded for management."),
            CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=0, reasoning="Valid score awarded for community."),
            CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=0, reasoning="Valid score awarded for scalability."),
        ]
        return ScoringResult(
            grid_variant=variant,
            total_score=sum(c.awarded_points for c in scores),
            criteria_scores=scores,
            eligibility_gate=EligibilityGate(is_eligible=True, failed_declarations=[], triggered_exclusions=[], gate_reasoning="Eligible"),
            reviewer_summary="Reviewer summary placeholder",
        )

    app_low = ("LowScore Enterprises", make_scoring_result(50, GridVariant.GENERAL_SME))
    app_high = ("HighScore CleanTech", make_scoring_result(90, GridVariant.INNOVATION_TECH))
    app_mid = ("MidScore Agro", make_scoring_result(75, GridVariant.WOMEN_YOUTH_LED))

    # Feed in arbitrary unsorted order: 50, 90, 75
    batch_input = [app_low, app_high, app_mid]

    mock_shortlist_json = json.dumps({
        "companies": [
            {
                "rank": 1,
                "business_name": "HighScore CleanTech",
                "total_score": 90,
                "grid_variant": "INNOVATION_TECH",
                "justification": "HighScore CleanTech secured the top rank with 90 points due to outstanding technical novelty and import substitution.",
                "site_visit_questions": ["Verify domestic assembly line", "Inspect clean-energy patents", "Review supplier contracts"],
                "contradictions": [],
            },
            {
                "rank": 2,
                "business_name": "MidScore Agro",
                "total_score": 75,
                "grid_variant": "WOMEN_YOUTH_LED",
                "justification": "MidScore Agro achieved rank 2 with 75 points, supported by robust female leadership and regional food processing.",
                "site_visit_questions": ["Audit cold chain storage", "Verify cooperative member roster", "Inspect sanitary permits"],
                "contradictions": [],
            },
            {
                "rank": 3,
                "business_name": "LowScore Enterprises",
                "total_score": 50,
                "grid_variant": "GENERAL_SME",
                "justification": "LowScore Enterprises scored 50 points, requiring substantial improvement in financial record-keeping.",
                "site_visit_questions": ["Review books of account", "Inspect old machinery status", "Check tax clearance history"],
                "contradictions": [],
            },
        ],
        "batch_summary": "Top 2 companies meet the investment committee threshold of >= 70 points for immediate grant disbursement.",
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_shortlist_json
    mock_client.models.generate_content.return_value = mock_response

    shortlist = rank_batch(scored_applications=batch_input, client=mock_client)

    assert isinstance(shortlist, RankedShortlist)
    assert len(shortlist.companies) == 3

    # Strictly verify descending score ordering
    assert shortlist.companies[0].total_score == 90
    assert shortlist.companies[0].rank == 1
    assert shortlist.companies[0].business_name == "HighScore CleanTech"

    assert shortlist.companies[1].total_score == 75
    assert shortlist.companies[1].rank == 2
    assert shortlist.companies[1].business_name == "MidScore Agro"

    assert shortlist.companies[2].total_score == 50
    assert shortlist.companies[2].rank == 3
    assert shortlist.companies[2].business_name == "LowScore Enterprises"


# =========================================================================
# 3. MULTILINGUAL CONSENT EXPLAINER TESTS
# =========================================================================

def test_multilingual_consent_explainer_oromo():
    """
    Test 4: Mocked Gemini returning 3 translated explanations in Afaan Oromo.
    Asserts:
    1. ConsentPackage parses correctly.
    2. Exactly 3 explanations are present.
    3. Contains the verbal_consent_question for voice reading.
    4. Prohibits automated checkbox ticking.
    """
    mock_consent_json = json.dumps({
        "explanations": [
            {
                "declaration_id": "declaration_05_anti_bribery_corruption",
                "original_legal_text": "The applicant strictly commits to zero tolerance towards bribery...",
                "translated_simple_explanation": "Waliigalteen kun maallaqa gargaarsaa kanaan mattaa kennuu ykn fudhachuu akka hin dandeenye mirkaneessa.",
                "target_language": "Afaan Oromo",
                "verbal_consent_question": "Qajeelfama mattaa ittisuu kana dhageessanii irratti walii galtuu?",
            },
            {
                "declaration_id": "declaration_08_child_labor_prevention",
                "original_legal_text": "The applicant certifies that no children under the legal minimum age are employed...",
                "translated_simple_explanation": "Daa'imman umriin isaanii hin geenye hojjechiisuun dhorkaadha.",
                "target_language": "Afaan Oromo",
                "verbal_consent_question": "Hojii keessan keessatti daa'imman akka hin hojjenne mirkaneessituu?",
            },
            {
                "declaration_id": "declaration_02_truthful_information",
                "original_legal_text": "The applicant solemnly confirms that all statements, financial figures...",
                "translated_simple_explanation": "Odeeffannoon galchitan hundi dhugaa ta'uu qaba.",
                "target_language": "Afaan Oromo",
                "verbal_consent_question": "Odeeffannoon kennitan hundi dhugaa ta'uu ni mirkaneessituu?",
            },
        ],
        "overall_warning": "CRITICAL CONSTRAINT: This package contains verbal explanation scripts for the voice agent only. Checkboxes MUST NEVER be auto-ticked. Consent must be explicitly and verifiably confirmed by the applicant.",
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_consent_json
    mock_client.models.generate_content.return_value = mock_response

    pkg = generate_consent_package(detected_language="Oromo", client=mock_client)

    assert isinstance(pkg, ConsentPackage)
    assert len(pkg.explanations) == 3

    bribery_exp = next(e for e in pkg.explanations if e.declaration_id == "declaration_05_anti_bribery_corruption")
    assert "mattaa" in bribery_exp.translated_simple_explanation.lower()
    assert len(bribery_exp.verbal_consent_question) > 5

    # Check anti-auto-tick mandate
    assert "NEVER" in pkg.overall_warning
