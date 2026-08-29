"""
Batch Ranking and Shortlist Agent (Reviewer Path).
Ranks a portfolio of scored SME applications using deterministic score sorting
and Gemini portfolio-level justification synthesis.
"""

import json
from typing import List, Dict, Optional, Any, Union, Tuple
from pydantic import ValidationError

from google.genai import types

from extractors.config import get_gemini_client, call_gemini_with_fallback
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
- For companies with contradictions or low scores, reflect those concerns in the site visit questions and justification."""


def rank_batch(
    scored_applications: List[Union[ScoringResult, Tuple[str, ScoringResult], Dict[str, Any]]],
    contradictions_map: Optional[Dict[str, List[Contradiction]]] = None,
    batch_name: str = "Batch Evaluation Portfolio",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    client: Optional[Any] = None,
) -> RankedShortlist:
    """
    Ranks a batch of scored grant applications in descending score order and enriches them
    with executive justifications and site-visit inquiries.
    """
    contra_map = contradictions_map or {}

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

    # Deterministic descending sort by eligibility and total score
    sorted_items = sorted(
        normalized_list,
        key=lambda x: (x["scoring_result"].eligibility_gate.is_eligible, x["scoring_result"].total_score),
        reverse=True
    )

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

    schema_prompt = f"\nRETURN ONLY VALID JSON MATCHING THIS EXACT SCHEMA:\n{json.dumps(RankedShortlist.model_json_schema(), default=str)}"
    user_prompt = f"""Review this sorted applicant portfolio and generate justifications, site-visit questions, and batch summary:

PORTFOLIO DATA:
{json.dumps(ranking_payload, indent=2, ensure_ascii=False)}
{schema_prompt}"""

    config = types.GenerateContentConfig(
        system_instruction=RANKER_SYSTEM_PROMPT,
        response_mime_type="application/json",
        temperature=0.0,
    )

    try:
        response, _ = call_gemini_with_fallback(
            client=ai_client,
            model=model,
            contents=[types.Part.from_text(text=user_prompt)],
            config=config,
        )
        raw_text = response.text if response and hasattr(response, "text") else ""
    except Exception:
        raw_text = ""

    if not raw_text:
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
    except (ValidationError, json.JSONDecodeError):
        try:
            data = json.loads(raw_text)
            shortlist = RankedShortlist.model_validate(data)
        except Exception:
            fallback_companies = [
                RankedCompany(
                    rank=i + 1,
                    business_name=entry["business_name"],
                    total_score=entry["scoring_result"].total_score,
                    grid_variant=entry["scoring_result"].grid_variant,
                    justification=f"{entry['business_name']} achieved rank #{i + 1} with a total score of {entry['scoring_result'].total_score}/100.",
                    site_visit_questions=[
                        "Inspect operational facility and verify declared assets.",
                        "Audit employee payroll register.",
                        "Examine tax clearance and business license validity.",
                    ],
                    contradictions=entry["contradictions"],
                )
                for i, entry in enumerate(sorted_items)
            ]
            return RankedShortlist(
                companies=fallback_companies,
                batch_summary=f"Batch portfolio evaluation of {len(sorted_items)} applicants sorted by total score."
            )

    # Maintain strict rank ordering integrity
    for idx, comp in enumerate(shortlist.companies):
        comp.rank = idx + 1
        comp.total_score = sorted_items[idx]["scoring_result"].total_score
        comp.business_name = sorted_items[idx]["business_name"]
        comp.grid_variant = sorted_items[idx]["scoring_result"].grid_variant
        comp.contradictions = sorted_items[idx]["contradictions"]

    return shortlist
