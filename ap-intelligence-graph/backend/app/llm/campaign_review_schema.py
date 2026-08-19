"""Pydantic validation for raw campaign-review-agent output (spec Phase 2).

Same role as llm/recommendation_schema.py: `LLMProvider.review_campaign()` is
documented to return a dict shaped like this, but nothing previously enforced
that shape. `RawCampaignReviewOut` is what `llm/factory.py::call_with_fallback`
validates against (its `validate=` parameter) - a structurally invalid live
response is treated exactly like a call failure and falls back to the
deterministic mock provider, never reaching a router as unvalidated data.

Deliberately loose on `candidate_lessons`: each entry there is validated
properly downstream by `app.memory.extraction_schema.ExtractedClaimIn` (the
same validator the chat-extraction pipeline uses) inside
`app.memory.manager.propose_candidates_from_campaign_review` - this schema
only checks that the review agent returned a list of dicts, matching how
`RawRecommendationOut` doesn't second-guess supporting_memory_ids either:
one validator per concern, not two divergent schemas for the same shape.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class RawCampaignReviewOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    summary: str
    what_worked: list[str] = []
    what_is_uncertain: list[str] = []
    planning_implications: list[str] = []
    candidate_lessons: list[dict[str, Any]] = []

    @field_validator("summary")
    @classmethod
    def _summary_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("summary must not be blank")
        return v


def validate_raw_campaign_review(raw: object) -> dict:
    """Raises on any structural problem; returns a plain dict on success."""
    return RawCampaignReviewOut(**raw).model_dump()
