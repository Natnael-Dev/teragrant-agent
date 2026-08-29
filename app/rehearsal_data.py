"""
# REHEARSAL MODE ONLY — NEVER used in Live Mode
# Contains quarantined pre-calculated scenarios for stage demonstration backups.
"""

from typing import Tuple, Dict, Any, List
from schemas.application_schema import (
    ApplicationSchema,
    BusinessInfo,
    EmploymentBreakdown,
    GenderSplit,
    AgeBandSplit,
    FinancialHistory,
    AnnualSales,
    MachineryItem,
    MandatoryDeclarations,
    ExclusionFactors,
)
from schemas.impact_schema import ImpactProtocol, SDGIndicator
from schemas.gap_schema import ApplicationPack, Gap, GapPriority
from schemas.scoring_schema import (
    GridVariant,
    CriterionName,
    CriterionScore,
    ScoringResult,
    EligibilityGate,
)
from schemas.reviewer_schema import Contradiction


def get_almaz_scenario() -> Tuple[ApplicationPack, ScoringResult, List[Contradiction], Dict[str, Any]]:
    """
    Scenario A: Almaz Spice & Grain Milling PLC.
    Features: Smudged/unreadable TIN + Omitted gender breakdown in voice note.
    Result: 2 High Priority Gaps + Gap Penalties on Financials and Gender.
    """
    app_model = ApplicationSchema(
        business_info=BusinessInfo(
            business_name="Almaz Spice & Grain Milling PLC",
            tin_number=None,  # Zero-hallucination for smudged TIN
            location="Hawassa, Sidama Region",
            sector="Agri-Processing & Spice Milling",
            years_in_operation=3,
            ownership_structure="PLC",
            female_ownership_percentage=100.0,
        ),
        employment=EmploymentBreakdown(
            total_staff=18,
            gender_split=GenderSplit(male=9, female=9, other=0),
            age_split=AgeBandSplit(youth_18_29=12, adults_30_50=6, seniors_above_50=0),
        ),
        financials=FinancialHistory(
            sales_history=[
                AnnualSales(year=2023, revenue_etb=2100000.0, gross_profit_etb=600000.0, net_profit_etb=300000.0),
                AnnualSales(year=2024, revenue_etb=3200000.0, gross_profit_etb=950000.0, net_profit_etb=480000.0),
            ],
            machinery_list=[
                MachineryItem(name="Commercial Dry Spice Hammer Mill", quantity=2, estimated_value_etb=800000.0, condition="Operational", acquisition_year=2022)
            ]
        ),
        organogram=[],
        declarations=MandatoryDeclarations(
            declaration_01_legal_compliance=True,
            declaration_02_truthful_information=True,
            declaration_03_no_conflict_of_interest=True,
            declaration_04_no_double_funding=True,
            declaration_05_anti_bribery_corruption=True,
            declaration_06_environmental_compliance=True,
            declaration_07_fair_labor_standards=True,
            declaration_08_child_labor_prevention=True,
            declaration_09_tax_compliance=True,
            declaration_10_safeguarding_policy=True,
            declaration_11_data_privacy_consent=True,
            declaration_12_financial_record_access=True,
            declaration_13_fund_utilization_commitment=True,
            declaration_14_regular_reporting_agreement=True,
            declaration_15_repayment_on_misuse=True,
        ),
        exclusion_factors=ExclusionFactors(),
    )

    impact_model = ImpactProtocol(
        project_title="Commercial Stainless Steel Grinding Line for Export-Grade Spices",
        location="Hawassa & Sidama Agro-Park",
        target_beneficiaries=600,
        etb_financial_target=2500000.0,
        sector="Agri-Processing & Food Manufacturing",
        sdgs=[SDGIndicator.SDG_02_ZERO_HUNGER, SDGIndicator.SDG_05_GENDER_EQUALITY, SDGIndicator.SDG_08_DECENT_WORK],
        milestones=["Procure 2 Commercial Stainless Steel Mills", "Train 50 women chili farmers in sanitary handling"],
    )

    pack = ApplicationPack(
        application=app_model,
        impact=impact_model,
        gaps=[
            Gap(
                field_name="business_info.tin_number",
                reason_missing="TIN was unreadable/obscured by stain on the uploaded trade license certificate. System strictly refused to hallucinate digits.",
                required_from="Tax Office",
                priority=GapPriority.HIGH,
            ),
            Gap(
                field_name="employment.gender_split",
                reason_missing="Applicant stated 18 total staff in voice note but omitted male/female breakdown. Field verification required.",
                required_from="Applicant",
                priority=GapPriority.HIGH,
            )
        ]
    )

    gate = EligibilityGate(
        is_eligible=True,
        failed_declarations=[],
        triggered_exclusions=[],
        gate_reasoning="All 15 statutory declarations confirmed and zero disqualifying exclusions triggered."
    )

    almaz_scores = [
        CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=16, reasoning="18 current staff with verified capacity to add 8 full-time mill operators."),
        CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=30, awarded_points=26, reasoning="100% female-owned business empowering women spice traders. Score penalized due to missing data: employment.gender_split."),
        CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=5, awarded_points=3, reasoning="Upgrading from open-air milling to dust-free closed-loop stainless steel milling."),
        CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=10, awarded_points=6, reasoning="Positive revenue growth to 3.2M ETB. Score penalized due to missing data: business_info.tin_number."),
        CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=9, reasoning="Direct procurement contracts with 600 smallholder chili outgrowers in Sidama."),
        CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=8, reasoning="Direct alignment with SDG 2 and SDG 5."),
        CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=3, reasoning="Experienced founder-manager leading daily operations."),
        CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=4, reasoning="Supports rural women spice farmers with guaranteed off-take contracts."),
        CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=3, reasoning="Regional distribution established with potential to access wholesale retail chains."),
    ]

    scoring_result = ScoringResult(
        grid_variant=GridVariant.WOMEN_YOUTH_LED,
        total_score=sum(c.awarded_points for c in almaz_scores),
        criteria_scores=almaz_scores,
        eligibility_gate=gate,
        reviewer_summary="Almaz Spice & Grain Milling PLC scores 78/100 under the Women & Youth-Led track. The system flagged 2 High-Priority Gaps (Smudged TIN and unverified gender breakdown) which incurred explicit scoring penalties. Field site-visit is recommended to verify the facility and obtain an official stamped TIN clearance certificate from the Sidama Revenue Bureau."
    )

    extracted_data_map = {
        "company_name": "Almaz Spice & Grain Milling PLC",
        "tin_number": None,
        "address": "Hawassa, Sidama Region",
        "mobile": "+251 916 884422",
        "years_in_operation": 3,
        "total_staff": 18,
        "female_staff": None,
        "main_products": "Berebere, Shiro, and Organic Dry Spice Milling with 600 smallholder chili outgrowers",
        "organogram_status": "Founder-Led Operations (Almaz Tadesse)",
        "machinery_requested": "2x Commercial Stainless Steel Spice Hammer Mills",
        "requested_etb": 2500000.0,
        "gap_fields": ["tin_number", "gender_split", "female_staff"],
    }

    return pack, scoring_result, [], extracted_data_map


def get_nahom_scenario() -> Tuple[ApplicationPack, ScoringResult, List[Contradiction], Dict[str, Any]]:
    """
    Scenario B: Nahom CleanTech & Circuit Lab PLC.
    Features: Zero Gaps, 100% complete intake, circular electronics recycling.
    Result: 92/100 Top-Tier Score under Innovation & Tech Track.
    """
    app_model = ApplicationSchema(
        business_info=BusinessInfo(
            business_name="Nahom CleanTech & Circuit Lab PLC",
            tin_number="0098765432",
            location="Addis Ababa, Bole Sub-City",
            sector="Electronics Repair & Clean-Tech Engineering",
            years_in_operation=3,
            ownership_structure="PLC",
            female_ownership_percentage=35.0,
        ),
        employment=EmploymentBreakdown(
            total_staff=12,
            gender_split=GenderSplit(male=8, female=4, other=0),
            age_split=AgeBandSplit(youth_18_29=12, adults_30_50=0, seniors_above_50=0),
        ),
        financials=FinancialHistory(
            sales_history=[
                AnnualSales(year=2023, revenue_etb=1200000.0, gross_profit_etb=500000.0, net_profit_etb=280000.0),
                AnnualSales(year=2024, revenue_etb=2100000.0, gross_profit_etb=890000.0, net_profit_etb=490000.0),
            ],
            machinery_list=[
                MachineryItem(name="SMD Reflow Workstation & Oscilloscope", quantity=4, estimated_value_etb=450000.0, condition="Operational", acquisition_year=2023)
            ]
        ),
        organogram=[],
        declarations=MandatoryDeclarations(
            declaration_01_legal_compliance=True,
            declaration_02_truthful_information=True,
            declaration_03_no_conflict_of_interest=True,
            declaration_04_no_double_funding=True,
            declaration_05_anti_bribery_corruption=True,
            declaration_06_environmental_compliance=True,
            declaration_07_fair_labor_standards=True,
            declaration_08_child_labor_prevention=True,
            declaration_09_tax_compliance=True,
            declaration_10_safeguarding_policy=True,
            declaration_11_data_privacy_consent=True,
            declaration_12_financial_record_access=True,
            declaration_13_fund_utilization_commitment=True,
            declaration_14_regular_reporting_agreement=True,
            declaration_15_repayment_on_misuse=True,
        ),
        exclusion_factors=ExclusionFactors(),
    )

    impact_model = ImpactProtocol(
        project_title="Domestic Solar Inverter Refurbishing and PCB E-Waste Recycling Lab",
        location="Addis Ababa & Regional Telecom Hubs",
        target_beneficiaries=2500,
        etb_financial_target=3000000.0,
        sector="Clean-Tech & Circular Electronics",
        sdgs=[SDGIndicator.SDG_09_INDUSTRY_INNOVATION, SDGIndicator.SDG_07_AFFORDABLE_ENERGY, SDGIndicator.SDG_12_RESPONSIBLE_CONSUMPTION],
        milestones=["Commissioning of Industrial SMD Reflow Station", "Refurbish 250 defunct solar inverters for off-grid clinics"],
    )

    pack = ApplicationPack(
        application=app_model,
        impact=impact_model,
        gaps=[]  # Zero Gaps
    )

    gate = EligibilityGate(
        is_eligible=True,
        failed_declarations=[],
        triggered_exclusions=[],
        gate_reasoning="All 15 statutory declarations confirmed and zero disqualifying exclusions triggered."
    )

    nahom_scores = [
        CriterionScore(criterion=CriterionName.JOB_CREATION, max_points=20, awarded_points=18, reasoning="12 full-time young electronics technicians with plans to onboard 10 apprentice circuit assemblers."),
        CriterionScore(criterion=CriterionName.GENDER_YOUTH_INCLUSION, max_points=5, awarded_points=5, reasoning="100% youth workforce (18-29) with 35% female technician participation in soldering labs."),
        CriterionScore(criterion=CriterionName.INNOVATION_UNIQUE_FEATURE, max_points=30, awarded_points=28, reasoning="Domestic component-level PCB repair and custom inverter testing reduces electronic hardware import dependency by 70%."),
        CriterionScore(criterion=CriterionName.FINANCIAL_VIABILITY, max_points=10, awarded_points=9, reasoning="Strong gross margins (42%) and rapid revenue growth to 2.1M ETB with low debt burden."),
        CriterionScore(criterion=CriterionName.LOCAL_SUPPLY_CHAIN, max_points=10, awarded_points=8, reasoning="Established e-waste collection channels with regional repair shops in Addis Ababa."),
        CriterionScore(criterion=CriterionName.SDG_ENVIRONMENTAL_IMPACT, max_points=10, awarded_points=10, reasoning="Exemplary circular economy alignment (SDG 9, SDG 12) preventing toxic e-waste."),
        CriterionScore(criterion=CriterionName.MANAGEMENT_ORGANOGRAM, max_points=5, awarded_points=5, reasoning="Lead electrical engineer has 6 years specialized power electronics design experience."),
        CriterionScore(criterion=CriterionName.COMMUNITY_IMPACT, max_points=5, awarded_points=4, reasoning="Provides low-cost solar power repair services to rural off-grid health centers."),
        CriterionScore(criterion=CriterionName.SCALABILITY, max_points=5, awarded_points=5, reasoning="High regional scalability with plans to license modular repair micro-labs in regional cities."),
    ]

    scoring_result = ScoringResult(
        grid_variant=GridVariant.INNOVATION_TECH,
        total_score=sum(c.awarded_points for c in nahom_scores),
        criteria_scores=nahom_scores,
        eligibility_gate=gate,
        reviewer_summary="Nahom CleanTech & Circuit Lab PLC is an outstanding candidate under the Innovation & Tech track. Scoring 92/100, the enterprise has zero data gaps, complete TIN registration, and strong circular economy impact. Immediate grant approval recommended."
    )

    extracted_data_map = {
        "company_name": "Nahom CleanTech & Circuit Lab PLC",
        "tin_number": "0098765432",
        "address": "Addis Ababa, Bole Sub-City",
        "mobile": "+251 911 405060",
        "years_in_operation": 3,
        "total_staff": 12,
        "female_staff": 4,
        "main_products": "Solar Inverter Refurbishing, Component-level PCB Repair & E-Waste Recycling",
        "organogram_status": "Lead Electrical Engineer + 11 Hardware Technicians",
        "machinery_requested": "Industrial SMD Reflow Station & Inverter Diagnostic Bench",
        "requested_etb": 3000000.0,
        "gap_fields": [],
    }

    return pack, scoring_result, [], extracted_data_map
