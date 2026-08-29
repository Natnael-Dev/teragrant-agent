"""
Batch Ranking and Shortlist Agent (Reviewer Path).
Ranks a portfolio of scored SME applications using deterministic score sorting
and Gemini portfolio-level justification synthesis.
"""

import json
from typing import List, Dict, Optional, Any, Union, Tuple
from google.genai import types

from extractors.config import get_gemini_client
from schemas.scoring_schema import ScoringResult
from schemas.reviewer_schema import RankedCompany, RankedShortlist, Contradiction


RANKER_SYSTEM_PROMPT = """You are the Lead Investment Committee Evaluator for the TeraGrant SME Portfolio.

Your task is to review a pre-sorted batch of scored SME grant applications and synthesize:
1. An Executive Justification (exactly 1 concise paragraph) for each enterprise explaining why its ranking position is warranted based on its score, grid variant, eligibility, and flagged contradictions.
2. Exactly 3 targeted, high-impact Due Diligence Questions for field site-visit verification for each enterprise.
3. An overarching Batch Portfolio Summary (1-2 paragraphs) detailing the batch distribution, cutoff recommendations, and sector diversity.

CRITICAL RULES:
- Respect the exact provided rank order (sorted descending by total score).
- Cite specific metrics (score, variant, contradictions, employment projections) in your justifications.
- For companies with contradictions or low scores, reflect those concerns in the site visit questions and justification.

Respond strictly in JSON matching the RankedShortlist schema."""


def rank_batch(
    scored_applications: List[Union[ScoringResult, Tuple[str, ScoringResult], Dict[str, Any]]],
    contradictions_map: Optional[Dict[str, List[Contradiction]]] = None,
    batch_name: str = "Batch Evaluation Portfolio",
    model: str = "gemini-2.0-flash",
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> RankedShortlist:
    """
    Ranks a batch of scored grant applications in descending score order and enriches them
    with executive justifications and site-visit inquiries.

    Args:
        scored_applications: List of ScoringResult objects, or (business_name, ScoringResult) tuples, or dicts.
        contradictions_map: Optional mapping of business_name -> List[Contradiction].
        batch_name: Optional batch description or cycle identifier.
        model: Gemini model identifier.
        api_key: Optional API key override.
        client: Optional pre-configured genai Client.

    Returns:
        RankedShortlist: Validated Pydantic model with strictly ordered RankedCompany records and batch summary.
    """
    contra_map = contradictions_map or {}

    # 1. Normalize entries into structured format
    normalized_list = []
    for idx, item in enumerate(scored_applications):
        if isinstance(item, tuple) and len(item) == 2:
            b_name, res = item
        elif isinstance(item, dict):
            b_name = item.get("business_name", f"Enterprise #{idx + 1}")
            res = item.get("scoring_result") or item
            if not isinstance(res, ScoringResult):
                res = ScoringResult.model_validate(res)
        elif isinstance(item, ScoringResult):
            b_name = f"Enterprise #{idx + 1}"
            res = item
        else:
            raise ValueError(f"Unsupported item format in scored_applications: {type(item)}")

        company_contradictions = contra_map.get(b_name, [])
        normalized_list.append({
            "business_name": b_name,
            "scoring_result": res,
            "contradictions": company_contradictions,
        })

    # =========================================================================
    # 2. PURE PYTHON DETERMINISTIC SORTING (Descending by total_score)
    # =========================================================================
    # Priority: Eligible applications first, then higher total_score
    sorted_items = sorted(
        normalized_list,
        key=lambda x: (x["scoring_result"].eligibility_gate.is_eligible, x["scoring_result"].total_score),
        reverse=True
    )

    # 3. LLM Synthesis for justifications & site visit questions
    ai_client = client or get_gemini_client(api_key=api_key)

    ranking_payload = {
        "batch_title": batch_name,
        "total_applicants": len(sorted_items),
        "sorted_candidates": [
            {
                "presorted_rank": rank_idx + 1,
                "business_name": entry["business_name"],
                "total_score": entry["scoring_result"].total_score,
                "grid_variant": entry["scoring_result"].grid_variant.value,
                "is_eligible": entry["scoring_result"].eligibility_gate.is_eligible,
                "reviewer_summary": entry["scoring_result"].reviewer_summary,
                "contradictions": [c.model_dump() for c in entry["contradictions"]],
            }
            for rank_idx, entry in enumerate(sorted_items)
        ],
    }

    user_prompt = f"""Review this sorted applicant portfolio and generate justifications, site-visit questions, and batch summary:

PORTFOLIO DATA:
{json.dumps(ranking_payload, indent=2, ensure_ascii=False)}

Respond strictly in JSON matching the RankedShortlist schema."""

    config = types.GenerateContentConfig(
        system_instruction=RANKER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=RankedShortlist,
        temperature=0.0,
    )

    try:
        response = ai_client.models.generate_content(
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception:
        raw_text = ""
    if not raw_text:
        # Deterministic fallback assembly if LLM is unavailable
        fallback_companies = [
            RankedCompany(
                rank=i + 1,
                business_name=entry["business_name"],
                total_score=entry["scoring_result"].total_score,
                grid_variant=entry["scoring_result"].grid_variant,
                justification=f"{entry['business_name']} achieved rank #{i + 1} with a total score of {entry['scoring_result'].total_score}/100 evaluated under the {entry['scoring_result'].grid_variant.value} track.",
                site_visit_questions=[
                    "Inspect operational facility and verify declared machinery assets.",
                    "Review payroll records to substantiate reported employment count.",
                    "Verify local supply agreements and tax compliance clearance.",
                ],
                contradictions=entry["contradictions"],
            )
            for i, entry in enumerate(sorted_items)
        ]
        return RankedShortlist(
            companies=fallback_companies,
            batch_summary=f"Batch evaluation comprising {len(sorted_items)} applicants sorted by total score."
        )

    try:
        shortlist = RankedShortlist.model_validate_json(raw_text)
    except Exception:
        data = json.loads(raw_text)
        shortlist = RankedShortlist.model_validate(data)

    # Ensure rank sequence and score order integrity is strictly maintained
    for idx, comp in enumerate(shortlist.companies):
        comp.rank = idx + 1
        comp.total_score = sorted_items[idx]["scoring_result"].total_score
        comp.business_name = sorted_items[idx]["business_name"]
        comp.grid_variant = sorted_items[idx]["scoring_result"].grid_variant
        comp.contradictions = sorted_items[idx]["contradictions"]

    return shortlist
