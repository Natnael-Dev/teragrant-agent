"""
TeraGrant Application Schema (Sections 1.1 to 2.6)
Defines Pydantic models for grant applications mapping to hackathon challenge brief constraints.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict


class GenderSplit(BaseModel):
    """Staff breakdown by gender."""
    model_config = ConfigDict(extra="forbid")

    male: int = Field(..., ge=0, description="Count of male staff")
    female: int = Field(..., ge=0, description="Count of female staff")
    other: int = Field(default=0, ge=0, description="Count of non-binary/other gender staff")

    @property
    def total(self) -> int:
        return self.male + self.female + self.other


class AgeBandSplit(BaseModel):
    """Staff breakdown by demographic age bands."""
    model_config = ConfigDict(extra="forbid")

    youth_18_29: int = Field(..., ge=0, description="Staff aged 18 to 29 (Youth)")
    adults_30_50: int = Field(..., ge=0, description="Staff aged 30 to 50")
    seniors_above_50: int = Field(default=0, ge=0, description="Staff aged above 50")

    @property
    def total(self) -> int:
        return self.youth_18_29 + self.adults_30_50 + self.seniors_above_50


class EmploymentBreakdown(BaseModel):
    """Section 1.2: Employment and demographic distribution."""
    model_config = ConfigDict(extra="forbid")

    total_staff: int = Field(..., ge=0, description="Total headcount of full-time & regular staff")
    gender_split: GenderSplit = Field(..., description="Breakdown of workforce by gender")
    age_split: AgeBandSplit = Field(..., description="Breakdown of workforce by age band")

    @model_validator(mode="after")
    def validate_headcount_consistency(self) -> "EmploymentBreakdown":
        if self.gender_split.total != self.total_staff:
            raise ValueError(
                f"Gender split total ({self.gender_split.total}) does not match total_staff ({self.total_staff})"
            )
        if self.age_split.total != self.total_staff:
            raise ValueError(
                f"Age band split total ({self.age_split.total}) does not match total_staff ({self.total_staff})"
            )
        return self


class BusinessInfo(BaseModel):
    """Section 1.1: Business Information & Legal Profile."""
    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(..., min_length=2, max_length=255, description="Registered legal business name")
    tin_number: Optional[str] = Field(None, min_length=9, max_length=15, description="Tax Identification Number (TIN)")
    location: str = Field(..., min_length=2, description="Physical location/region/woreda/city")
    sector: str = Field(..., min_length=2, description="Industry sector (e.g., Agri-tech, Manufacturing, Renewable Energy)")
    years_in_operation: int = Field(..., ge=0, description="Years the enterprise has been actively operating")
    ownership_structure: str = Field(
        ...,
        min_length=2,
        description="Legal ownership structure (e.g., Sole Proprietorship, PLC, Share Company, Cooperative)",
    )
    female_ownership_percentage: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Percentage of equity held by women"
    )


class AnnualSales(BaseModel):
    """Single year financial record."""
    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., ge=2000, le=2100, description="Fiscal year (Gregorian / GC)")
    revenue_etb: float = Field(..., ge=0.0, description="Gross revenue / annual sales in Ethiopian Birr (ETB)")
    gross_profit_etb: Optional[float] = Field(default=None, description="Gross profit in ETB")
    net_profit_etb: Optional[float] = Field(default=None, description="Net profit after tax in ETB")


class MachineryItem(BaseModel):
    """Capital asset & machinery item."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=2, description="Machinery name or equipment model")
    quantity: int = Field(..., ge=1, description="Quantity owned/leased")
    estimated_value_etb: float = Field(..., ge=0.0, description="Estimated current asset value in ETB")
    condition: str = Field(
        ...,
        description="Condition status (e.g., 'Operational', 'Needs Repair', 'Decommissioned')"
    )
    acquisition_year: Optional[int] = Field(None, ge=1970, le=2100, description="Year acquired")


class FinancialHistory(BaseModel):
    """Section 2.1 - 2.3: Financial records and capital assets."""
    model_config = ConfigDict(extra="forbid")

    sales_history: List[AnnualSales] = Field(
        default_factory=list,
        max_length=5,
        description="Up to 5-year historical sales records in ETB"
    )
    machinery_list: List[MachineryItem] = Field(
        default_factory=list,
        description="Inventory of key machinery and productive equipment"
    )


class OrganogramNode(BaseModel):
    """Section 2.4: Management hierarchy and organogram placeholder."""
    model_config = ConfigDict(extra="forbid")

    role_title: str = Field(..., min_length=2, description="Position or title in management")
    holder_name: Optional[str] = Field(None, description="Name of the person currently holding the role")
    reports_to: Optional[str] = Field(None, description="Role title of the direct supervisor/line manager")
    department: Optional[str] = Field(None, description="Department or functional division")
    responsibilities: List[str] = Field(default_factory=list, description="Key operational responsibilities")


class MandatoryDeclarations(BaseModel):
    """
    Section 2.5: 15 Mandatory Declarations.
    STRICT CONSTRAINT: Must default to False (or None). NEVER auto-tick True.
    """
    model_config = ConfigDict(extra="forbid")

    declaration_01_legal_compliance: bool = Field(
        default=False,
        description="1. Valid business license and compliance with local laws."
    )
    declaration_02_truthful_information: bool = Field(
        default=False,
        description="2. All information in the application is true, complete, and accurate."
    )
    declaration_03_no_conflict_of_interest: bool = Field(
        default=False,
        description="3. No conflict of interest with grant committee, reviewers, or sponsors."
    )
    declaration_04_no_double_funding: bool = Field(
        default=False,
        description="4. No duplicate funding requested/received from other donors for the same budget lines."
    )
    declaration_05_anti_bribery_corruption: bool = Field(
        default=False,
        description="5. Zero tolerance policy towards bribery, corruption, and fraud."
    )
    declaration_06_environmental_compliance: bool = Field(
        default=False,
        description="6. Adherence to environmental regulations and waste management standards."
    )
    declaration_07_fair_labor_standards: bool = Field(
        default=False,
        description="7. Fair wages, non-discriminatory hiring, and compliance with labor codes."
    )
    declaration_08_child_labor_prevention: bool = Field(
        default=False,
        description="8. Strict prohibition of child labor and forced labor across operations."
    )
    declaration_09_tax_compliance: bool = Field(
        default=False,
        description="9. Active tax registration and good standing with revenue authorities."
    )
    declaration_10_safeguarding_policy: bool = Field(
        default=False,
        description="10. Commitment to workplace safety, gender protection, and anti-harassment."
    )
    declaration_11_data_privacy_consent: bool = Field(
        default=False,
        description="11. Consent to data collection, background vetting, and audit verification."
    )
    declaration_12_financial_record_access: bool = Field(
        default=False,
        description="12. Agreement to provide unhindered access to books of accounts and audit records."
    )
    declaration_13_fund_utilization_commitment: bool = Field(
        default=False,
        description="13. Commitment to spend grant proceeds solely on approved project milestones."
    )
    declaration_14_regular_reporting_agreement: bool = Field(
        default=False,
        description="14. Agreement to submit quarterly milestone and financial tracking reports."
    )
    declaration_15_repayment_on_misuse: bool = Field(
        default=False,
        description="15. Agreement to immediately refund any grant funds misallocated or misused."
    )

    @property
    def all_confirmed(self) -> bool:
        """Returns True if and only if all 15 declarations are explicitly confirmed (True)."""
        declarations = [
            self.declaration_01_legal_compliance,
            self.declaration_02_truthful_information,
            self.declaration_03_no_conflict_of_interest,
            self.declaration_04_no_double_funding,
            self.declaration_05_anti_bribery_corruption,
            self.declaration_06_environmental_compliance,
            self.declaration_07_fair_labor_standards,
            self.declaration_08_child_labor_prevention,
            self.declaration_09_tax_compliance,
            self.declaration_10_safeguarding_policy,
            self.declaration_11_data_privacy_consent,
            self.declaration_12_financial_record_access,
            self.declaration_13_fund_utilization_commitment,
            self.declaration_14_regular_reporting_agreement,
            self.declaration_15_repayment_on_misuse,
        ]
        return all(declarations)

    @property
    def unconfirmed_count(self) -> int:
        """Returns the count of unconfirmed declarations out of 15."""
        return 15 - sum(1 for v in self.model_dump().values() if v is True)


class ExclusionFactors(BaseModel):
    """
    Section 2.6: Exclusion Factors (Instant-Kill Criteria).
    If ANY of these 3 flags is True, the application is instantly disqualified.
    """
    model_config = ConfigDict(extra="forbid")

    bankruptcy_or_insolvency: bool = Field(
        default=False,
        description="True if business is in bankruptcy, receivership, or liquidation proceedings (Instant Kill)"
    )
    sanctions_or_criminal_convictions: bool = Field(
        default=False,
        description="True if company or founders are under sanctions or convicted of fraud/financial crimes (Instant Kill)"
    )
    prohibited_activities: bool = Field(
        default=False,
        description="True if business operates in banned/restricted sectors: weapons, tobacco, gambling, illegal logging (Instant Kill)"
    )

    @property
    def is_disqualified(self) -> bool:
        """Returns True if any instant-kill criterion is triggered."""
        return (
            self.bankruptcy_or_insolvency
            or self.sanctions_or_criminal_convictions
            or self.prohibited_activities
        )


class ApplicationSchema(BaseModel):
    """
    Root Application Schema for TeraGrant (Sections 1.1 to 2.6).
    Complete structured payload for grant eligibility and evaluation.
    """
    model_config = ConfigDict(extra="forbid")

    business_info: BusinessInfo = Field(..., description="Section 1.1: Business Information")
    employment: EmploymentBreakdown = Field(..., description="Section 1.2: Employment Breakdown")
    financials: FinancialHistory = Field(
        default_factory=FinancialHistory,
        description="Sections 2.1 - 2.3: Financial History & Machinery"
    )
    organogram: List[OrganogramNode] = Field(
        default_factory=list,
        description="Section 2.4: Management hierarchy"
    )
    declarations: MandatoryDeclarations = Field(
        default_factory=MandatoryDeclarations,
        description="Section 2.5: 15 Mandatory Declarations (must default to False)"
    )
    exclusion_factors: ExclusionFactors = Field(
        default_factory=ExclusionFactors,
        description="Section 2.6: 3 Instant-Kill Exclusion Factors"
    )

    @property
    def is_eligible_for_review(self) -> bool:
        """Application is eligible if all declarations are checked and zero exclusion factors are triggered."""
        return self.declarations.all_confirmed and not self.exclusion_factors.is_disqualified
