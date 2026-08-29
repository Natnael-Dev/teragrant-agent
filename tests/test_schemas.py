"""
Unit tests for TeraGrant Pydantic schemas (ApplicationSchema and ImpactProtocol).
Validates schema instantiation, field constraints, headcount integrity, declarations, and exclusion rules.
"""

import pytest
from pydantic import ValidationError

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
from schemas.impact_schema import (
    ImpactProtocol,
    SDGIndicator,
    Milestone,
)


def get_valid_application_payload():
    """Helper to generate a valid ApplicationSchema dictionary."""
    return {
        "business_info": {
            "business_name": "Abyssinia Agro-Processing PLC",
            "tin_number": "0012345678",
            "location": "Bishoftu, Oromia Region, Ethiopia",
            "sector": "Agri-Processing & Food Manufacturing",
            "years_in_operation": 4,
            "ownership_structure": "Private Limited Company (PLC)",
            "female_ownership_percentage": 50.0,
        },
        "employment": {
            "total_staff": 25,
            "gender_split": {
                "male": 12,
                "female": 13,
                "other": 0,
            },
            "age_split": {
                "youth_18_29": 15,
                "adults_30_50": 8,
                "seniors_above_50": 2,
            },
        },
        "financials": {
            "sales_history": [
                {"year": 2022, "revenue_etb": 1500000.0, "gross_profit_etb": 450000.0, "net_profit_etb": 200000.0},
                {"year": 2023, "revenue_etb": 2800000.0, "gross_profit_etb": 890000.0, "net_profit_etb": 410000.0},
                {"year": 2024, "revenue_etb": 4200000.0, "gross_profit_etb": 1300000.0, "net_profit_etb": 650000.0},
            ],
            "machinery_list": [
                {
                    "name": "Industrial Grain De-huller & Milling Line",
                    "quantity": 2,
                    "estimated_value_etb": 1200000.0,
                    "condition": "Operational",
                    "acquisition_year": 2022,
                }
            ],
        },
        "organogram": [
            {
                "role_title": "Managing Director",
                "holder_name": "Tigist Alemu",
                "reports_to": None,
                "department": "Executive",
                "responsibilities": ["Overall strategic direction", "Grant oversight"],
            },
            {
                "role_title": "Operations Manager",
                "holder_name": "Dawit Bekele",
                "reports_to": "Managing Director",
                "department": "Production",
                "responsibilities": ["Plant operations", "Supply chain management"],
            },
        ],
        "declarations": {},
        "exclusion_factors": {},
    }


def get_valid_impact_payload():
    """Helper to generate a valid ImpactProtocol dictionary."""
    return {
        "project_title": "Solar-Powered Cold Chain Logistics for Smallholder Horticulturalists",
        "location": "Hawassa and Sidama Region, Ethiopia",
        "target_beneficiaries": 1500,
        "etb_financial_target": 3500000.0,
        "sector": "Agri-Tech & Clean Energy",
        "sdgs": [
            SDGIndicator.SDG_02_ZERO_HUNGER,
            SDGIndicator.SDG_07_AFFORDABLE_ENERGY,
            SDGIndicator.SDG_08_DECENT_WORK,
            SDGIndicator.SDG_13_CLIMATE_ACTION,
        ],
        "milestones": [
            Milestone(
                milestone_id="M1",
                title="Procurement of 5 Solar Cool Hub Units",
                description="Procure and clear customs for high-efficiency solar cooling equipment.",
                target_month=3,
                verification_evidence="Customs clearance certificate and supplier invoice matching bill of quantities.",
            ),
            "Commissioning and training of 300 women cooperative farmers in cold-chain handling.",
        ],
    }


# =========================================================================
# APPLICATION SCHEMA TESTS
# =========================================================================

def test_valid_application_schema_instantiation():
    """Test successful instantiation of ApplicationSchema with full nested models."""
    payload = get_valid_application_payload()
    app = ApplicationSchema(**payload)

    assert app.business_info.business_name == "Abyssinia Agro-Processing PLC"
    assert app.business_info.years_in_operation == 4
    assert app.employment.total_staff == 25
    assert app.employment.gender_split.female == 13
    assert len(app.financials.sales_history) == 3
    assert len(app.financials.machinery_list) == 1
    assert len(app.organogram) == 2


def test_declarations_must_default_to_false_never_auto_tick():
    """
    CRITICAL TEST: Verify that all 15 mandatory declarations default to False
    and are NEVER automatically checked.
    """
    declarations = MandatoryDeclarations()
    dumped = declarations.model_dump()

    assert len(dumped) == 15, f"Expected exactly 15 declarations, got {len(dumped)}"
    for decl_name, val in dumped.items():
        assert val is False, f"Declaration {decl_name} must default to False, but was {val}"

    assert declarations.all_confirmed is False
    assert declarations.unconfirmed_count == 15


def test_exclusion_factors_must_default_to_false():
    """Test that all 3 exclusion criteria default to False (not triggered)."""
    exclusions = ExclusionFactors()
    dumped = exclusions.model_dump()

    assert len(dumped) == 3, f"Expected exactly 3 exclusion factors, got {len(dumped)}"
    assert exclusions.bankruptcy_or_insolvency is False
    assert exclusions.sanctions_or_criminal_convictions is False
    assert exclusions.prohibited_activities is False
    assert exclusions.is_disqualified is False


def test_exclusion_factors_trigger_instant_kill():
    """Test that triggering ANY exclusion factor marks applicant as disqualified."""
    # 1. Bankruptcy instant kill
    ex1 = ExclusionFactors(bankruptcy_or_insolvency=True)
    assert ex1.is_disqualified is True

    # 2. Sanctions / fraud instant kill
    ex2 = ExclusionFactors(sanctions_or_criminal_convictions=True)
    assert ex2.is_disqualified is True

    # 3. Prohibited activities instant kill
    ex3 = ExclusionFactors(prohibited_activities=True)
    assert ex3.is_disqualified is True


def test_eligibility_requires_all_declarations_and_zero_exclusions():
    """Test the complete eligibility lifecycle."""
    payload = get_valid_application_payload()
    app = ApplicationSchema(**payload)

    # Initial state: unconfirmed declarations -> Not eligible
    assert app.is_eligible_for_review is False

    # Confirm all 15 declarations
    all_true_declarations = {f"declaration_{i:02d}": True for i in range(1, 16)}
    # Update with actual field names
    for key in app.declarations.model_dump().keys():
        setattr(app.declarations, key, True)

    assert app.declarations.all_confirmed is True
    assert app.is_eligible_for_review is True

    # If an exclusion occurs, eligibility is revoked
    app.exclusion_factors.sanctions_or_criminal_convictions = True
    assert app.is_eligible_for_review is False


def test_invalid_application_gender_headcount_mismatch():
    """Test that Pydantic rejects gender breakdown whose sum != total_staff."""
    payload = get_valid_application_payload()
    # total_staff is 25, but gender sum is 10 + 10 = 20
    payload["employment"]["gender_split"]["male"] = 10
    payload["employment"]["gender_split"]["female"] = 10

    with pytest.raises(ValidationError) as exc_info:
        ApplicationSchema(**payload)

    assert "Gender split total (20) does not match total_staff (25)" in str(exc_info.value)


def test_invalid_application_age_band_mismatch():
    """Test that Pydantic rejects age band breakdown whose sum != total_staff."""
    payload = get_valid_application_payload()
    # total_staff is 25, but age sum is 5 + 5 + 0 = 10
    payload["employment"]["age_split"]["youth_18_29"] = 5
    payload["employment"]["age_split"]["adults_30_50"] = 5
    payload["employment"]["age_split"]["seniors_above_50"] = 0

    with pytest.raises(ValidationError) as exc_info:
        ApplicationSchema(**payload)

    assert "Age band split total (10) does not match total_staff (25)" in str(exc_info.value)


def test_invalid_application_negative_staff_or_revenue():
    """Test rejection of negative values for numeric fields."""
    payload = get_valid_application_payload()
    payload["employment"]["total_staff"] = -5

    with pytest.raises(ValidationError):
        ApplicationSchema(**payload)

    # Test negative revenue in sales history
    payload2 = get_valid_application_payload()
    payload2["financials"]["sales_history"][0]["revenue_etb"] = -100.0

    with pytest.raises(ValidationError):
        ApplicationSchema(**payload2)


# =========================================================================
# IMPACT PROTOCOL SCHEMA TESTS
# =========================================================================

def test_valid_impact_schema_instantiation():
    """Test successful instantiation of ImpactProtocol."""
    payload = get_valid_impact_payload()
    impact = ImpactProtocol(**payload)

    assert impact.project_title.startswith("Solar-Powered Cold Chain")
    assert impact.target_beneficiaries == 1500
    assert impact.etb_financial_target == 3500000.0
    assert len(impact.sdgs) == 4
    assert SDGIndicator.SDG_02_ZERO_HUNGER in impact.sdgs
    assert len(impact.milestones) == 2


def test_impact_schema_sdg_deduplication():
    """Test that duplicate selected SDGs are automatically deduplicated."""
    payload = get_valid_impact_payload()
    payload["sdgs"] = [
        SDGIndicator.SDG_01_NO_POVERTY,
        SDGIndicator.SDG_01_NO_POVERTY,
        SDGIndicator.SDG_05_GENDER_EQUALITY,
    ]
    impact = ImpactProtocol(**payload)
    assert len(impact.sdgs) == 2
    assert impact.sdgs == [SDGIndicator.SDG_01_NO_POVERTY, SDGIndicator.SDG_05_GENDER_EQUALITY]


def test_invalid_impact_schema_empty_sdgs():
    """Test rejection when no SDGs are selected."""
    payload = get_valid_impact_payload()
    payload["sdgs"] = []

    with pytest.raises(ValidationError):
        ImpactProtocol(**payload)


def test_invalid_impact_schema_invalid_sdg_string():
    """Test rejection of non-existent SDG string."""
    payload = get_valid_impact_payload()
    payload["sdgs"] = ["SDG 99: Invalid SDG"]

    with pytest.raises(ValidationError):
        ImpactProtocol(**payload)


def test_invalid_impact_schema_negative_beneficiaries():
    """Test rejection of non-positive target beneficiaries."""
    payload = get_valid_impact_payload()
    payload["target_beneficiaries"] = 0

    with pytest.raises(ValidationError):
        ImpactProtocol(**payload)


def test_invalid_impact_schema_blank_milestones():
    """Test rejection of empty milestone list or whitespace milestone strings."""
    payload = get_valid_impact_payload()
    payload["milestones"] = []

    with pytest.raises(ValidationError):
        ImpactProtocol(**payload)

    payload2 = get_valid_impact_payload()
    payload2["milestones"] = ["  "]

    with pytest.raises(ValidationError):
        ImpactProtocol(**payload2)


def test_load_mock_data_files():
    """Verify that the mock data files in data/ parse cleanly into Pydantic models."""
    import json
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent

    # Test mock_application.json
    app_path = base_dir / "data" / "mock_application.json"
    with open(app_path, "r", encoding="utf-8") as f:
        app_data = json.load(f)
    app = ApplicationSchema(**app_data)
    assert app.business_info.business_name == "Abyssinia Agro-Processing PLC"

    # Test mock_impact.json
    impact_path = base_dir / "data" / "mock_impact.json"
    with open(impact_path, "r", encoding="utf-8") as f:
        impact_data = json.load(f)
    impact = ImpactProtocol(**impact_data)
    assert impact.target_beneficiaries == 1500

