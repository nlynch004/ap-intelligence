"""Pydantic validation for raw partner-brief-agent output (spec Phase 3).

Same role as llm/campaign_review_schema.py and llm/recommendation_schema.py:
`LLMProvider.generate_partner_brief()` is documented to return a dict shaped
like this, but nothing previously enforced that shape. `RawPartnerBriefOut`
is what `llm/factory.py::call_with_fallback` validates against - a
structurally invalid live response is treated exactly like a call failure
and falls back to the deterministic mock provider.

Phase 3 is read-only preparation, not a learning loop (spec: "No new memory
from Partner Brief yet") - there is no candidate-lessons-shaped field here
at all, unlike RawCampaignReviewOut.
"""

from pydantic import BaseModel, ConfigDict, field_validator


class RawPartnerBriefOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    relationship_summary: str
    performance_summary: str
    what_to_know: list[str] = []
    negotiation_considerations: list[str] = []
    measurement_considerations: list[str] = []
    open_questions: list[str] = []
    planning_implications: list[str] = []

    @field_validator("relationship_summary", "performance_summary")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


def validate_raw_partner_brief(raw: object) -> dict:
    """Raises on any structural problem; returns a plain dict on success."""
    return RawPartnerBriefOut(**raw).model_dump()
