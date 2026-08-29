"""
Deterministic Eligibility Gate Agent.
Pure Python business logic for validating mandatory declarations and instant-kill exclusion factors.
Zero LLM dependencies.
"""

from typing import Optional
from schemas.application_schema import ApplicationSchema
from schemas.scoring_schema import EligibilityGate, ExclusionFactor


def run_eligibility_gate(application: Optional[ApplicationSchema]) -> EligibilityGate:
    """
    Deterministically evaluates grant eligibility based on the 15 mandatory declarations
    and 3 instant-kill exclusion criteria.

    Args:
        application: The populated ApplicationSchema model.

    Returns:
        EligibilityGate: Deterministic pass/fail verdict with lists of failed declarations
                         and triggered exclusions.
    """
    if application is None:
        return EligibilityGate(
            is_eligible=False,
            failed_declarations=["application_schema_missing"],
            triggered_exclusions=[],
            gate_reasoning="Application data is missing or incomplete, preventing eligibility evaluation."
        )

    failed_declarations: list[str] = []
    triggered_exclusions: list[ExclusionFactor] = []

    # 1. Evaluate the 15 mandatory declarations
    declarations_dump = application.declarations.model_dump()
    for field_name, value in declarations_dump.items():
        if value is not True:
            failed_declarations.append(field_name)

    # 2. Evaluate the 3 instant-kill exclusion criteria
    exclusions = application.exclusion_factors
    if exclusions.bankruptcy_or_insolvency:
        triggered_exclusions.append(ExclusionFactor.BANKRUPTCY_INSOLVENCY)
    if exclusions.sanctions_or_criminal_convictions:
        triggered_exclusions.append(ExclusionFactor.SANCTIONS_CRIMINAL)
    if exclusions.prohibited_activities:
        triggered_exclusions.append(ExclusionFactor.PROHIBITED_ACTIVITIES)

    # 3. Formulate deterministic verdict and reasoning
    is_eligible = (len(failed_declarations) == 0) and (len(triggered_exclusions) == 0)

    if is_eligible:
        gate_reasoning = "All 15 mandatory declarations confirmed and zero instant-kill exclusion criteria triggered."
    else:
        reasons = []
        if triggered_exclusions:
            exclusion_names = ", ".join(e.value for e in triggered_exclusions)
            reasons.append(f"triggered {len(triggered_exclusions)} instant-kill exclusion(s) [{exclusion_names}]")
        if failed_declarations:
            reasons.append(f"failed {len(failed_declarations)} of 15 mandatory declaration(s)")
        gate_reasoning = f"Eligibility failed: Enterprise {' and '.join(reasons)}."

    return EligibilityGate(
        is_eligible=is_eligible,
        failed_declarations=failed_declarations,
        triggered_exclusions=triggered_exclusions,
        gate_reasoning=gate_reasoning,
    )
