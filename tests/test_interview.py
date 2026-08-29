"""
Unit tests for Guided Conversational Intake (Interview State Machine).
Verifies step extraction, fact merging, headcount parsing, skipping behavior,
audio synthesis, and full-loop integration with the scoring engine.
"""

import json
from unittest.mock import MagicMock
import pytest

from schemas.interview_schema import InterviewStep, AnswerExtraction
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
from schemas.scoring_schema import GridVariant, ScoringResult
from agents.interview_agent import (
    INTERVIEW_STEPS,
    extract_answer,
    merge_answer,
    synthesize_audio_extraction,
    _parse_staff_counts,
)
from agents.scorer_agent import score_application


def test_interview_steps_count_and_definitions():
    """Verify exactly 7 steps are defined with trilingual question texts."""
    assert len(INTERVIEW_STEPS) == 7
    step_ids = [s.step_id for s in INTERVIEW_STEPS]
    assert step_ids == ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]

    for step in INTERVIEW_STEPS:
        assert step.field_path
        assert step.question_en
        assert step.question_am
        assert step.question_or
        assert step.example_answer


def test_extract_answer_valid_mock():
    """Verify extract_answer correctly parses JSON response from Gemini."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "field_id": "business_info.business_name",
        "value": "Almaz Spice Mill PLC",
        "confidence": 0.95,
        "notes": "Explicitly stated by owner",
    })
    mock_client.models.generate_content.return_value = mock_response

    step = INTERVIEW_STEPS[0]
    extraction = extract_answer(
        step=step,
        transcript="My name is Almaz and my business is Almaz Spice Mill PLC.",
        client=mock_client,
    )

    assert isinstance(extraction, AnswerExtraction)
    assert extraction.field_id == "business_info.business_name"
    assert extraction.value == "Almaz Spice Mill PLC"
    assert extraction.confidence == 0.95


def test_extract_answer_irrelevant_transcript_and_empty():
    """Verify extract_answer returns null value and 0 confidence for irrelevant/empty input."""
    # 1. Empty transcript fast-path
    step = INTERVIEW_STEPS[0]
    empty_ext = extract_answer(step=step, transcript="", client=MagicMock())
    assert empty_ext.value is None
    assert empty_ext.confidence == 0.0

    # 2. Irrelevant spoken content (mocked LLM output)
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "field_id": "business_info.business_name",
        "value": None,
        "confidence": 0.0,
        "notes": "Applicant only talked about the weather.",
    })
    mock_client.models.generate_content.return_value = mock_response

    irrelevant_ext = extract_answer(
        step=step,
        transcript="The weather in Bahir Dar was very rainy today.",
        client=mock_client,
    )
    assert irrelevant_ext.value is None
    assert irrelevant_ext.confidence == 0.0


def test_staff_counts_parser():
    """Verify regex/heuristic parser correctly extracts total and female staff."""
    total, female = _parse_staff_counts("8 workers, 6 women")
    assert total == 8
    assert female == 6

    total, female = _parse_staff_counts("We have 15 staff members including 10 female employees")
    assert total == 15
    assert female == 10

    total, female = _parse_staff_counts("5 employees")
    assert total == 5
    assert female is None

    total, female = _parse_staff_counts("12 and 7")
    assert total == 12
    assert female == 7


def test_merge_answer_sets_business_name_and_staff():
    """Verify merge_answer updates interview_data dictionary with extracted facts."""
    int_data = {}

    # Step 1: Business name
    s1 = INTERVIEW_STEPS[0]
    ext1 = AnswerExtraction(field_id=s1.field_path, value="Almaz Spice Mill", confidence=0.92)
    int_data = merge_answer(int_data, s1, ext1)
    assert int_data["company_name"] == "Almaz Spice Mill"
    assert int_data["business_name"] == "Almaz Spice Mill"

    # Step 4: Staff
    s4 = INTERVIEW_STEPS[3]
    ext4 = AnswerExtraction(field_id=s4.field_path, value="8 workers, 6 women", confidence=0.88)
    int_data = merge_answer(int_data, s4, ext4)
    assert int_data["total_staff"] == 8
    assert int_data["female_staff"] == 6


def test_skip_and_low_confidence_leaves_field_none():
    """Verify skipping or low-confidence extraction leaves the interview data unmodified."""
    int_data = {"company_name": "Existing Co"}

    # Low confidence (< 0.5)
    s2 = INTERVIEW_STEPS[1]
    low_conf_ext = AnswerExtraction(field_id=s2.field_path, value="Somewhere in Amhara", confidence=0.3)
    updated = merge_answer(int_data, s2, low_conf_ext)
    assert "address" not in updated
    assert "location" not in updated

    # Null value
    s3 = INTERVIEW_STEPS[2]
    null_ext = AnswerExtraction(field_id=s3.field_path, value=None, confidence=0.0)
    updated2 = merge_answer(updated, s3, null_ext)
    assert "main_products" not in updated2
    assert "sector" not in updated2


def test_synthesize_audio_extraction_structure():
    """Verify synthesize_audio_extraction builds valid AudioTranscriptExtraction."""
    interview_data = {
        "company_name": "Almaz Spice Mill",
        "address": "Bahir Dar, Amhara",
        "main_products": "Ground spices and berbere",
        "total_staff": 8,
        "female_staff": 6,
        "requested_etb": "450,000 ETB",
        "machinery_requested": "Commercial pulverizer mill",
        "market_target": "Household consumers and local restaurants",
    }
    transcripts = [
        "Q: Name? | A: Almaz Spice Mill",
        "Q: Location? | A: Bahir Dar, Amhara",
        "Q: Staff? | A: 8 workers, 6 women",
    ]

    synth = synthesize_audio_extraction(interview_data, transcripts)

    assert synth.business_name == "Almaz Spice Mill"
    assert synth.location == "Bahir Dar, Amhara"
    assert synth.product_type == "Ground spices and berbere"
    assert synth.employee_count == 8
    assert "450,000 ETB" in synth.financial_figures
    assert "Almaz Spice Mill" in synth.transcript
    assert "Need: Commercial pulverizer mill" in synth.impact_summary


def test_full_7_step_loop_and_scoring_flow():
    """Verify full 7-step guided intake synthesizes data that scores cleanly in the scoring engine."""
    interview_data = {}
    transcripts = []

    mock_answers = [
        ("S1", "Almaz Spice Mill", 0.95, "Almaz Spice Mill"),
        ("S2", "Bahir Dar, Amhara", 0.90, "Bahir Dar"),
        ("S3", "Food Processing and Spices", 0.90, "Food Processing"),
        ("S4", "8 workers, 6 women", 0.88, "8 workers, 6 women"),
        ("S5", "3 years", 0.85, "3 years"),
        ("S6", "Commercial spice pulverizer, 450000 Birr", 0.90, "Commercial pulverizer"),
        ("S7", "Regional restaurant cooperatives", 0.85, "Restaurant coops"),
    ]

    for step, (s_id, ans_val, conf, spoken) in zip(INTERVIEW_STEPS, mock_answers):
        assert step.step_id == s_id
        ext = AnswerExtraction(field_id=step.field_path, value=ans_val, confidence=conf)
        interview_data = merge_answer(interview_data, step, ext)
        transcripts.append(f"Q: {step.question_en} | A: {spoken}")

    assert interview_data["total_staff"] == 8
    assert interview_data["female_staff"] == 6
    assert interview_data["years_in_operation"] == 3

    synth_audio = synthesize_audio_extraction(interview_data, transcripts)
    assert synth_audio.employee_count == 8

    # Create a mapped ApplicationPack from synthesized data
    app = ApplicationSchema(
        business_info=BusinessInfo(
            business_name=synth_audio.business_name,
            tin_number="0099887766",
            location=synth_audio.location,
            sector=synth_audio.product_type,
            years_in_operation=3,
            ownership_structure="Sole Proprietorship",
            female_ownership_percentage=100.0,
        ),
        employment=EmploymentBreakdown(
            total_staff=synth_audio.employee_count or 8,
            gender_split=GenderSplit(male=2, female=6, other=0),
            age_split=AgeBandSplit(youth_18_29=5, adults_30_50=3, seniors_above_50=0),
        ),
        financials=FinancialHistory(),
        organogram=[],
        declarations=MandatoryDeclarations(),
        exclusion_factors=ExclusionFactors(),
    )

    impact = ImpactProtocol(
        project_title="Almaz Spice Mill Modernization",
        location=synth_audio.location,
        target_beneficiaries=50,
        etb_financial_target=450000.0,
        sector=synth_audio.product_type,
        sdgs=[SDGIndicator.SDG_05_GENDER_EQUALITY, SDGIndicator.SDG_08_DECENT_WORK],
        milestones=["Install pulverizer", "Train 6 female staff", "Scale distribution"],
    )

    pack = ApplicationPack(application=app, impact=impact, gaps=[])
    score_res = score_application(pack=pack, variant=GridVariant.WOMEN_YOUTH_LED)

    assert isinstance(score_res, ScoringResult)
    assert score_res.total_score > 0.0
    assert score_res.grid_variant == GridVariant.WOMEN_YOUTH_LED
