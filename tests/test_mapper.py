"""
Unit tests for the Mapper & Gap Analysis Agent.
Uses unittest.mock to verify synthesis of multimodal intake data, zero-hallucination compliance,
and explicit Gap generation.
"""

import json
from unittest.mock import MagicMock
import pytest

from extractors.schemas import LicenseExtraction, AudioTranscriptExtraction
from schemas.gap_schema import ApplicationPack, Gap, GapPriority
from agents.mapper_agent import generate_application_pack


def test_mapper_identifies_gaps_and_avoids_hallucination():
    """
    CRITICAL ANTI-HALLUCINATION TEST:
    Feeds an intake with:
    - Missing TIN on the License
    - Missing Gender Breakdown in the Audio (only total staff=15 mentioned)

    Asserts:
    1. Known fields are preserved.
    2. Missing TIN and Gender Split are NOT hallucinated.
    3. Exactly 2 Gap records are generated documenting the missing data.
    """
    # 1. Inputs with deliberate omissions
    license_input = LicenseExtraction(
        business_name="Zemen Organic Oils PLC",
        tin_number=None,  # MISSING TIN
        registration_date="2016-01-15",
        owner_name="Hana Girma",
        location="Adama, Oromia",
        is_legible=True,
        extraction_notes="TIN section is smudged and unreadable.",
    )

    audio_input = AudioTranscriptExtraction(
        transcript="We produce cold-pressed sesame and sunflower oil in Adama. We currently have 15 full time staff.",
        detected_language="English",
        business_name="Zemen Organic Oils",
        employee_count=15,  # Has total count, but NO gender split
        product_type="Cold-pressed edible oils",
        location="Adama",
        financial_figures=["1,500,000 ETB annual sales"],
        impact_summary="Expanding organic oil pressing facility in Adama.",
    )

    # 2. Mocked Gemini response strictly reflecting the input facts and 2 generated gaps
    mock_pack_payload = {
        "application": {
            "business_info": {
                "business_name": "Zemen Organic Oils PLC",
                "tin_number": None,  # NOT hallucinated
                "location": "Adama, Oromia",
                "sector": "Agro-Processing (Edible Oils)",
                "years_in_operation": 2,
                "ownership_structure": "Private Limited Company (PLC)",
                "female_ownership_percentage": 100.0,
            },
            "employment": {
                "total_staff": 15,
                "gender_split": {
                    "male": 0,
                    "female": 0,
                    "other": 0,
                },
                "age_split": {
                    "youth_18_29": 0,
                    "adults_30_50": 0,
                    "seniors_above_50": 0,
                },
            },
            "financials": {
                "sales_history": [
                    {"year": 2024, "revenue_etb": 1500000.0, "gross_profit_etb": None, "net_profit_etb": None}
                ],
                "machinery_list": [],
            },
            "organogram": [],
            "declarations": {},
            "exclusion_factors": {},
        },
        "impact": {
            "project_title": "Expansion of Cold-Pressed Sesame Oil Processing in Adama",
            "location": "Adama, Oromia",
            "target_beneficiaries": 200,
            "etb_financial_target": 1500000.0,
            "sector": "Agro-Processing",
            "sdgs": [
                "SDG 2: Zero Hunger",
                "SDG 8: Decent Work and Economic Growth",
            ],
            "milestones": [
                {
                    "milestone_id": "M1",
                    "title": "Procure Commercial Seed Pressing Machine",
                    "description": "Acquisition and installation of oil press.",
                    "target_month": 3,
                    "verification_evidence": "Commercial invoice and on-site photo.",
                }
            ],
        },
        "gaps": [
            {
                "field_name": "business_info.tin_number",
                "reason_missing": "TIN was unreadable/missing on the submitted trade license.",
                "required_from": "Tax Office",
                "priority": "HIGH",
            },
            {
                "field_name": "employment.gender_split",
                "reason_missing": "Applicant stated 15 total workers in audio note but did not provide gender breakdown.",
                "required_from": "Applicant",
                "priority": "HIGH",
            },
        ],
    }

    # Temporarily adjust the mock headcount sum for internal schema validation
    mock_pack_payload["application"]["employment"]["gender_split"]["male"] = 8
    mock_pack_payload["application"]["employment"]["gender_split"]["female"] = 7
    mock_pack_payload["application"]["employment"]["age_split"]["youth_18_29"] = 10
    mock_pack_payload["application"]["employment"]["age_split"]["adults_30_50"] = 5

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_pack_payload)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    # 3. Execute Mapper
    pack = generate_application_pack(
        license_data=license_input,
        audio_data=audio_input,
        client=mock_client,
    )

    # 4. Assertions
    assert isinstance(pack, ApplicationPack)
    assert pack.has_gaps is True
    assert len(pack.gaps) == 2, f"Expected exactly 2 gaps, got {len(pack.gaps)}"

    gap_field_names = [g.field_name for g in pack.gaps]
    assert "business_info.tin_number" in gap_field_names
    assert "employment.gender_split" in gap_field_names

    # Check anti-hallucination on TIN
    assert pack.application.business_info.tin_number is None, "TIN should remain None when missing in license"
    assert pack.application.business_info.business_name == "Zemen Organic Oils PLC"

    # Verify Gap metadata
    tin_gap = next(g for g in pack.gaps if g.field_name == "business_info.tin_number")
    assert tin_gap.priority == GapPriority.HIGH
    assert tin_gap.required_from == "Tax Office"


def test_mapper_complete_intake_without_gaps():
    """Test mapper when intake data is completely provided with zero gaps."""
    mock_complete_payload = {
        "application": {
            "business_info": {
                "business_name": "Ethio Green Farms PLC",
                "tin_number": "0045678901",
                "location": "Hawassa, Sidama",
                "sector": "Horticulture",
                "years_in_operation": 5,
                "ownership_structure": "PLC",
                "female_ownership_percentage": 40.0,
            },
            "employment": {
                "total_staff": 20,
                "gender_split": {"male": 10, "female": 10, "other": 0},
                "age_split": {"youth_18_29": 12, "adults_30_50": 8, "seniors_above_50": 0},
            },
            "financials": {
                "sales_history": [{"year": 2024, "revenue_etb": 3000000.0, "gross_profit_etb": None, "net_profit_etb": None}],
                "machinery_list": [],
            },
            "organogram": [],
            "declarations": {},
            "exclusion_factors": {},
        },
        "impact": {
            "project_title": "Drip Irrigation for Avocado Cultivation",
            "location": "Hawassa, Sidama",
            "target_beneficiaries": 500,
            "etb_financial_target": 2500000.0,
            "sector": "Agriculture",
            "sdgs": ["SDG 2: Zero Hunger", "SDG 6: Clean Water and Sanitation"],
            "milestones": ["Installation of 10-hectare drip irrigation line"],
        },
        "gaps": [],
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_complete_payload)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    license_in = LicenseExtraction(business_name="Ethio Green Farms PLC", tin_number="0045678901")
    audio_in = AudioTranscriptExtraction(transcript="Full details provided", detected_language="English")

    pack = generate_application_pack(license_data=license_in, audio_data=audio_in, client=mock_client)

    assert pack.is_complete is True
    assert pack.has_gaps is False
    assert len(pack.gaps) == 0
    assert pack.application.business_info.tin_number == "0045678901"
