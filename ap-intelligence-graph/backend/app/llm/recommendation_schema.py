"""Pydantic validation for raw recommendation-agent output.

`LLMProvider.recommend()` (both the mock and OpenAI implementations) is
documented to return a dict shaped like spec Sec.20's structured output, but
nothing previously enforced that shape - a live model could return
syntactically valid JSON that is missing a required key, has the wrong
type, or has a structurally invalid `recommended_terms`, and that would
reach `chat.py`/`recommendations.py`'s direct dict-key access
(`raw_rec["confidence"]`, etc.) and crash as an unhandled 500 *after* the
call itself had already "succeeded" - past the point `call_with_fallback`'s
try/except could catch it.

`RawRecommendationOut` is the schema that closes that gap. It is used by
`llm/factory.py::call_with_fallback` via its `validate=` parameter, which
treats a validation failure exactly like a call failure: it triggers the
same deterministic mock fallback, never an unhandled exception.

Deliberately excluded: `supporting_memory_ids`. Those are constructed
server-side by `app/memory/retrieval.py` from claims actually retrieved
from the database - the model is never asked for them (see
`agents/prompts.py`), and this schema does not declare the field, so even
if a model ever included one anyway it would be silently dropped by
`model_dump()` rather than used. That architecture is unchanged by this file.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecommendedTerms(BaseModel):
    model_config = ConfigDict(extra="ignore")

    base_fee: float = Field(gt=0)
    performance_bonus_pct: float = Field(ge=0, le=100)
    bonus_basis: str

    @field_validator("bonus_basis")
    @classmethod
    def _bonus_basis_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("bonus_basis must not be blank")
        return v


class RawRecommendationOut(BaseModel):
    """The exact shape routers rely on: `recommendation`, `recommended_terms`,
    `confidence`, `uncertainties`, `explanation`. No `supporting_memory_ids`
    - see module docstring."""

    model_config = ConfigDict(extra="ignore")

    recommendation: str
    recommended_terms: RecommendedTerms
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainties: list[str] = []
    explanation: str = ""

    @field_validator("recommendation")
    @classmethod
    def _recommendation_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("recommendation must not be blank")
        return v


def validate_raw_recommendation(raw: object) -> dict:
    """Raises on any structural problem; returns a plain dict on success
    (same shape callers already expect from `LLMProvider.recommend()`)."""
    return RawRecommendationOut(**raw).model_dump()
