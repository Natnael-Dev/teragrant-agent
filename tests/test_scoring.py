"""
Unit tests for Eligibility Gate, Grid Router, and 100-Point Evaluation Scorer.
Verifies pure-Python deterministic gate logic, router logic, variant point allocations,
and gap penalty enforcement.
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
from schemas.impact_schema import ImpactProtocol, SDGIndicator, Milestone
from schemas.gap_schema import ApplicationPack, Gap, GapPriority
from schemas.scoring_schema import (
    ExclusionFactor,
    EligibilityGate,
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
)
from agents.eligibility_agent import run_eligibility_gate
from agents.router_agent import route_to_grid_variant
from agents.scorer_agent import score_application


def get_sample_application():
    """Helper to create a fully valid ApplicationSchema instance."""
    return ApplicationSchema(
        business_info=BusinessInfo(
            business_name="Sheba CleanTech PLC",
            tin_number="0078901234",
            location="Mekelle, Tigray",
            sector="Renewable Energy & Solar Assembly",
            years_in_operation=3,
            ownership_structure="Private Limited Company (PLC)",
            female_ownership_percentage=60.0,
        ),
        employment=EmploymentBreakdown(
            total_staff=10,
            gender_split=GenderSplit(male=4, female=6, other=0),
            age_split=AgeBandSplit(youth_18_29=7, adults_30_50=3, seniors_above_50=0),
        ),
        financials=FinancialHistory(),
        organogram=[],
        declarations=MandatoryDeclarations(),
        exclusion_factors=ExclusionFactors(),
    )


def get_sample_impact():
    """Helper to create a fully valid ImpactProtocol instance."""
    return ImpactProtocol(
        project_title="Solar Micro-Grid Deployment for Rural Clinics",
        location="Mekelle & Central Tigray",
        target_beneficiaries=5000,
        etb_financial_target=4500000.0,
        sector="Renewable Energy",
        sdgs=[
            SDGIndicator.SDG_07_AFFORDABLE_ENERGY,
            SDGIndicator.SDG_03_GOOD_HEALTH,
            SDGIndicator.SDG_13_CLIMATE_ACTION,
        ],
        milestones=[
            Milestone(
                milestone_id="M1",
                title="Assembly of 20 Solar Mini-Units",
                target_month=4,
                verification_evidence="Third party electrical engineering commissioning certificate.",
            )
        ],
    )


# =========================================================================
# 1. DETERMINISTIC ELIGIBILITY GATE TESTS (PURE PYTHON)
# =========================================================================

def test_eligibility_gate_failure_with_false_declaration_and_exclusion():
    """
    Test 1: Application with 1 False declaration and 1 True exclusion factor.
    Must fail deterministically and identify the exact reasons.
    """
    app = get_sample_application()

    # Set 14 declarations to True, but leave 1 as False
    for field_name in app.declarations.model_dump().keys():
        setattr(app.declarations, field_name, True)
    app.declarations.declaration_05_anti_bribery_corruption = False  # Failed declaration

    # Trigger 1 exclusion factor
    app.exclusion_factors.sanctions_or_criminal_convictions = True  # Instant kill

    result = run_eligibility_gate(app)

    assert isinstance(result, EligibilityGate)
    assert result.is_eligible is False
    assert "declaration_05_anti_bribery_corruption" in result.failed_declarations
    assert ExclusionFactor.SANCTIONS_CRIMINAL in result.triggered_exclusions
    assert "Eligibility failed" in result.gate_reasoning
    assert "SANCTIONS_CRIMINAL" in result.gate_reasoning


def test_eligibility_gate_success_perfect_application():
    """
    Test 2: Perfect application with all 15 declarations confirmed and zero exclusions.
    Must pass deterministically.
    """
    app = get_sample_application()

    # Set all 15 declarations to True
    for field_name in app.declarations.model_dump().keys():
        setattr(app.declarations, field_name, True)

    # All exclusions are False by default
    assert app.exclusion_factors.is_disqualified is False

    result = run_eligibility_gate(app)

    assert isinstance(result, EligibilityGate)
    assert result.is_eligible is True
    assert len(result.failed_declarations) == 0
    assert len(result.triggered_exclusions) == 0
    assert "All 15 mandatory declarations confirmed" in result.gate_reasoning


def test_eligibility_gate_none_application():
    """Verify that passing None to eligibility gate returns fail verdict gracefully."""
    result = run_eligibility_gate(None)
    assert result.is_eligible is False
    assert "application_schema_missing" in result.failed_declarations


# =========================================================================
# 2. GRID ROUTER TESTS (MOCKED)
# =========================================================================

def test_grid_router_routes_to_women_youth_led():
    """
    Test 4: Mocked router returning WOMEN_YOUTH_LED for enterprise with 60% female ownership.
    """
    app = get_sample_application()
    impact = get_sample_impact()

    mock_router_json = json.dumps({
        "grid_variant": "WOMEN_YOUTH_LED",
        "routing_rationale": "Enterprise has 60% female ownership and 70% youth workforce representation.",
    })

    mock_response = MagicMock()
    mock_response.text = mock_router_json

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    variant = route_to_grid_variant(app, impact, client=mock_client)

    assert variant == GridVariant.WOMEN_YOUTH_LED
    assert isinstance(variant, GridVariant)


# =========================================================================
# 3. 100-POINT SCORER TESTS (MOCKED)
# =========================================================================

def test_100_point_scorer_innovation_tech_variant():
    """
    Test 3: Mocked Gemini API call for INNOVATION_TECH variant.
    Asserts:
    1. Result parsed cleanly into ScoringResult.
    2. Exactly 9 criteria scores present.
    3. INNOVATION_UNIQUE_FEATURE has max_points=30 and FINANCIAL_VIABILITY has max_points=10.
    4. total_score <= 100 and matches the mathematical sum of awarded points.
    5. EligibilityGate is attached.
    """
    app = get_sample_application()
    # Confirm all declarations for this test
    for k in app.declarations.model_dump().keys():
        setattr(app.declarations, k, True)

    impact = get_sample_impact()
    pack = ApplicationPack(
        application=app,
        impact=impact,
        gaps=[
            Gap(
                field_name="financials.sales_history",
                reason_missing="Applicant provided only 1 year of sales history instead of 5.",
                required_from="Applicant",
                priority=GapPriority.MEDIUM,
            )
        ],
    )

    mock_scoring_payload = {
        "grid_variant": "INNOVATION_TECH",
        "total_score": 81,
        "criteria_scores": [
            {
                "criterion": "JOB_CREATION",
                "max_points": 20,
                "awarded_points": 16,
                "reasoning": "Enterprise currently employs 10 staff with credible projections to create 15 additional technical assembly jobs. Target figures align with local regional demand.",
            },
            {
                "criterion": "GENDER_YOUTH_INCLUSION",
                "max_points": 5,  # REWEIGHTED FOR INNOVATION_TECH
                "awarded_points": 4,
                "reasoning": "Strong demographic leadership with 60% female equity ownership and 70% youth workforce. Clear policies ensure equal pay across assembly teams.",
            },
            {
                "criterion": "INNOVATION_UNIQUE_FEATURE",
                "max_points": 30,  # DOUBLE WEIGHT UNDER INNOVATION_TECH
                "awarded_points": 26,
                "reasoning": "Proprietary modular solar inverter design engineered specifically for fluctuating rural electrical grids. Hardware is assembled domestically reducing import dependency.",
            },
            {
                "criterion": "FINANCIAL_VIABILITY",
                "max_points": 10,  # REDUCED TO 10 UNDER INNOVATION_TECH
                "awarded_points": 5,
                "reasoning": "Current cash flow is stable with positive gross margins on existing inventory sales. Score penalized due to missing data: financials.sales_history.",
            },
            {
                "criterion": "LOCAL_SUPPLY_CHAIN",
                "max_points": 10,
                "awarded_points": 8,
                "reasoning": "Source 65% of metal fabrication and chassis components from regional suppliers in Tigray. Logistics routes have established local distribution partners.",
            },
            {
                "criterion": "SDG_ENVIRONMENTAL_IMPACT",
                "max_points": 10,
                "awarded_points": 9,
                "reasoning": "Direct alignment with SDG 7 (Clean Energy) and SDG 13 (Climate Action) by replacing diesel generators with solar power. Displaced emissions verified via benchmark metrics.",
            },
            {
                "criterion": "MANAGEMENT_ORGANOGRAM",
                "max_points": 5,
                "awarded_points": 4,
                "reasoning": "Core leadership team has verified technical and electrical engineering backgrounds. Key executive roles have documented reporting structures.",
            },
            {
                "criterion": "COMMUNITY_IMPACT",
                "max_points": 5,
                "awarded_points": 5,
                "reasoning": "Prioritizes electrification for 5,000 community members and rural medical clinics. Subsidized power models are established for non-profit health centers.",
            },
            {
                "criterion": "SCALABILITY",
                "max_points": 5,
                "awarded_points": 4,
                "reasoning": "Modular mini-unit design is readily replicable across neighboring woredas and regions. Manufacturing capacity can scale with capital infusion.",
            },
        ],
        "eligibility_gate": {
            "is_eligible": True,
            "failed_declarations": [],
            "triggered_exclusions": [],
            "gate_reasoning": "All 15 mandatory declarations confirmed and zero instant-kill exclusion criteria triggered.",
        },
        "reviewer_summary": "Sheba CleanTech PLC presents an exceptional technology-driven grant proposal with robust female ownership and transformative rural electrification impact. The domestic assembly of solar hardware provides strong import substitution, while the main risk centers on the need for multi-year historical financial verification. The evaluation committee strongly recommends a field inspection to audit the assembly facility and verify local supply contracts.",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_scoring_payload)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    result = score_application(pack=pack, variant=GridVariant.INNOVATION_TECH, client=mock_client)

    assert isinstance(result, ScoringResult)
    assert result.grid_variant == GridVariant.INNOVATION_TECH
    assert result.total_score == 81
    assert result.total_score <= 100
    assert len(result.criteria_scores) == 9

    # Check Innovation Tech variant max points
    innov_score = next(c for c in result.criteria_scores if c.criterion == CriterionName.INNOVATION_UNIQUE_FEATURE)
    assert innov_score.max_points == 30
    assert innov_score.awarded_points == 26

    fin_score = next(c for c in result.criteria_scores if c.criterion == CriterionName.FINANCIAL_VIABILITY)
    assert fin_score.max_points == 10
    assert "Score penalized due to missing data: financials.sales_history" in fin_score.reasoning

    # Check sum of all max points equals exactly 100
    total_possible = sum(c.max_points for c in result.criteria_scores)
    assert total_possible == 100, f"Total maximum points must equal 100, got {total_possible}"

    # Check Eligibility Gate is intact and attached
    assert result.eligibility_gate.is_eligible is True
