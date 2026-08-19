"""Campaign review agent (spec Phase 2). Input: CampaignReviewEvidence only
(already deterministically assembled - see app/memory/retrieval.py). Output:
structured summary/what_worked/what_is_uncertain/planning_implications plus
proposed candidate_lessons. Never writes to the database - candidate_lessons
are handed to app.memory.manager.propose_candidates_from_campaign_review,
the same governed candidate pipeline chat extraction uses."""

from app.llm.campaign_review_schema import validate_raw_campaign_review
from app.llm.factory import call_with_fallback


def generate_campaign_review(evidence: dict) -> tuple[dict, str]:
    """Returns a dict guaranteed to match RawCampaignReviewOut's shape - the
    raw LLM result is validated before it is trusted; a malformed/incomplete
    live response falls back to the (always-valid) mock provider rather than
    reaching callers as unvalidated data (see llm/factory.py::call_with_fallback)."""
    result, provider_name = call_with_fallback("review_campaign", evidence, validate=validate_raw_campaign_review)
    return result, provider_name
