"""
Unit tests for Eligibility Gate, Grid Router, and 100-Point Evaluation Scorer.
Verifies pure-Python deterministic gate logic, router logic, variant point allocations,
deterministic rule engine scoring, and gap penalty enforcement.
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
from schemas.provenance_schema import FieldStatus, FieldProvenance
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
from agents.rule_engine import evaluate_criterion, calculate_total_score


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
# 3. 100-POINT SCORER TESTS (DETERMINISTIC ENGINE + MOCKED LLM SUMMARY)
# =========================================================================

def test_100_point_scorer_innovation_tech_variant():
    """
    Test 3: Evaluates INNOVATION_TECH variant.
    Numerical points are produced deterministically by the rule engine.
    Gemini is mocked to return exclusively the reviewer_summary narrative text.
    Asserts:
    1. Result parsed cleanly into ScoringResult.
    2. Exactly 9 criteria scores present.
    3. INNOVATION_UNIQUE_FEATURE has max_points=30 and FINANCIAL_VIABILITY has max_points=10.
    4. total_score <= 100 and matches the mathematical sum of awarded points.
    5. EligibilityGate is attached.
    6. Gap penalty notes are appended to criterion reasoning.
    """
    app = get_sample_application()
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

    mock_summary_json = json.dumps({
        "reviewer_summary": "Sheba CleanTech PLC presents an exceptional technology-driven grant proposal with robust female ownership and transformative rural electrification impact. The domestic assembly of solar hardware provides strong import substitution, while historical financial records require field audit."
    })

    mock_response = MagicMock()
    mock_response.text = mock_summary_json

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    result = score_application(pack=pack, variant=GridVariant.INNOVATION_TECH, client=mock_client)

    assert isinstance(result, ScoringResult)
    assert result.grid_variant == GridVariant.INNOVATION_TECH
    assert result.total_score <= 100
    assert result.total_score == sum(c.awarded_points for c in result.criteria_scores)
    assert len(result.criteria_scores) == 9

    # Check Innovation Tech variant max points
    innov_score = next(c for c in result.criteria_scores if c.criterion == CriterionName.INNOVATION_UNIQUE_FEATURE)
    assert innov_score.max_points == 30

    fin_score = next(c for c in result.criteria_scores if c.criterion == CriterionName.FINANCIAL_VIABILITY)
    assert fin_score.max_points == 10
    assert "Score penalized due to missing data: financials.sales_history" in fin_score.reasoning

    # Check sum of all max points equals exactly 100
    total_possible = sum(c.max_points for c in result.criteria_scores)
    assert total_possible == 100, f"Total maximum points must equal 100, got {total_possible}"

    # Check Eligibility Gate is intact and attached
    assert result.eligibility_gate.is_eligible is True
    assert "Sheba CleanTech PLC" in result.reviewer_summary


def test_scoring_uses_deterministic_rule_engine():
    """
    Verifies that score_application() delegates numerical scoring to rule_engine.
    Asserts:
    1. Job creation score exactly matches evaluate_criterion() output for 15 employees.
    2. Total score is the exact sum of the deterministic points.
    """
    app = get_sample_application()
    app.employment.total_staff = 15
    app.employment.gender_split = GenderSplit(male=7, female=8, other=0)
    app.employment.age_split = AgeBandSplit(youth_18_29=10, adults_30_50=5, seniors_above_50=0)

    impact = get_sample_impact()
    prov = {
        "employment.total_staff": FieldProvenance(
            field_path="employment.total_staff",
            value=15,
            status=FieldStatus.DOCUMENT_VERIFIED,
            confidence=0.95,
            source_type="license",
            evidence_snippet="Payroll register verifies 15 full-time employees.",
        )
    }
    pack = ApplicationPack(application=app, impact=impact, gaps=[], provenance=prov)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = json.dumps({
        "reviewer_summary": "Enterprise demonstrates solid workforce deployment and viable operations."
    })

    result = score_application(pack=pack, variant=GridVariant.GENERAL_SME, client=mock_client)

    # Check Job Creation against rule_engine evaluate_criterion
    facts = {"total_staff": 15, "employment.total_staff": 15}
    expected_job_score = evaluate_criterion(
        CriterionName.JOB_CREATION,
        GridVariant.GENERAL_SME,
        facts=facts,
        provenance=prov,
    )

    actual_job_score = next(c for c in result.criteria_scores if c.criterion == CriterionName.JOB_CREATION)
    assert actual_job_score.awarded_points == expected_job_score.awarded_points
    assert actual_job_score.awarded_points == 14  # 10-19 employee band under DOCUMENT_VERIFIED
    assert result.total_score == sum(c.awarded_points for c in result.criteria_scores)
    assert result.total_score == calculate_total_score(result.criteria_scores)


def test_scoring_reproducibility():
    """
    Verifies that calling score_application() twice with the same input and mocked LLM summary
    yields identical integer numerical scores every time.
    """
    app = get_sample_application()
    impact = get_sample_impact()
    pack = ApplicationPack(application=app, impact=impact, gaps=[])

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = json.dumps({
        "reviewer_summary": "Consistent deterministic evaluation summary across multiple runs."
    })

    res1 = score_application(pack=pack, variant=GridVariant.GENERAL_SME, client=mock_client)
    res2 = score_application(pack=pack, variant=GridVariant.GENERAL_SME, client=mock_client)

    assert res1.total_score == res2.total_score
    assert isinstance(res1.total_score, int)
    assert len(res1.criteria_scores) == len(res2.criteria_scores) == 9
    for c1, c2 in zip(res1.criteria_scores, res2.criteria_scores):
        assert c1.criterion == c2.criterion
        assert c1.awarded_points == c2.awarded_points
        assert isinstance(c1.awarded_points, int)


def test_scoring_llm_failure_fallback():
    """
    Verifies that if Gemini fails or raises an error, deterministic scores are still
    awarded accurately and a default narrative summary is provided without crashing.
    """
    app = get_sample_application()
    impact = get_sample_impact()
    pack = ApplicationPack(application=app, impact=impact, gaps=[])

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Gemini API connection error")

    result = score_application(pack=pack, variant=GridVariant.GENERAL_SME, client=mock_client)

    assert isinstance(result, ScoringResult)
    assert result.total_score == sum(c.awarded_points for c in result.criteria_scores)
    assert result.reviewer_summary == "Scoring completed; narrative summary unavailable."
    assert len(result.criteria_scores) == 9


def test_scoring_empty_pack_graceful_handling():
    """
    Verifies that passing an empty pack awards 0 points gracefully across all criteria.
    """
    empty_pack = ApplicationPack(application=None, impact=None, gaps=[])
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = json.dumps({
        "reviewer_summary": "Incomplete application dossier with zero verified metrics."
    })

    result = score_application(pack=empty_pack, variant=GridVariant.GENERAL_SME, client=mock_client)
    assert result.total_score == 0
    for cs in result.criteria_scores:
        assert cs.awarded_points == 0


def test_export_endpoint_includes_scoring_audit_trail():
    """
    Verifies that GET /api/export returns a JSON payload containing the criteria_scores
    list with all criterion-level audit trail fields (rule_applied, evidence_value,
    provenance_state, provenance_cap_applied) fully serialized.
    """
    from fastapi.testclient import TestClient
    from app.server import app as server_app, SESSION

    app_schema = get_sample_application()
    app_schema.employment.total_staff = 15
    impact_schema = get_sample_impact()
    prov = {
        "employment.total_staff": FieldProvenance(
            field_path="employment.total_staff",
            value=15,
            status=FieldStatus.DOCUMENT_VERIFIED,
            confidence=0.95,
            source_type="license",
            evidence_snippet="Official register verifies 15 employees.",
        )
    }
    pack = ApplicationPack(application=app_schema, impact=impact_schema, gaps=[], provenance=prov)

    # Score application using the deterministic rule engine
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = json.dumps({
        "reviewer_summary": "Enterprise exhibits robust operational capability and high alignment."
    })
    scoring_result = score_application(pack=pack, variant=GridVariant.GENERAL_SME, client=mock_client)

    # Place in SESSION state as server.py would do
    SESSION["scoring_res"] = scoring_result
    SESSION["applicant_name"] = "Sheba CleanTech PLC"

    client = TestClient(server_app)
    response = client.get("/api/export")

    assert response.status_code == 200
    data = response.json()

    assert "criteria_scores" in data
    assert len(data["criteria_scores"]) == 9

    job_score = next(c for c in data["criteria_scores"] if c["criterion"] == "JOB_CREATION")
    assert job_score["rule_applied"] == "EMPLOYEE_BAND_10_TO_19"
    assert job_score["evidence_value"] == 15
    assert job_score["provenance_state"] == "DOCUMENT_VERIFIED"
    assert job_score["provenance_cap_applied"] == 1.0
    assert job_score["awarded_points"] == 14

    assert "scoring_result" in data
    assert data["scoring_result"]["total_score"] == scoring_result.total_score

