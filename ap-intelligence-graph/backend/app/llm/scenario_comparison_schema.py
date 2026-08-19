"""Pydantic validation for raw scenario-comparison-agent output (spec
Phase 5). Same role as the other llm/*_schema.py modules: validates the
shape `llm/factory.py::call_with_fallback` checks before trusting a live
response.

Structural validation only lives here (RawScenarioComparisonOut) - the
additional, RUNTIME-dependent check that `preferred_scenario_id` actually
names one of the scenarios that were supplied (not an invented fourth
option) can't be a static Pydantic rule, since it depends on which
scenario ids were actually built for this call. That check lives in
app.agents.scenario_comparison_agent, composed into the same
call_with_fallback `validate=` hook - an invented scenario id is treated
exactly like a structurally invalid response and falls back to the mock."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawScenarioComparisonOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preferred_scenario_id: str
    comparison_summary: str
    tradeoffs: list[str] = []
    uncertainties: list[str] = []
    questions_before_finalizing: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("preferred_scenario_id", "comparison_summary")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


def validate_raw_scenario_comparison(raw: object) -> dict:
    """Raises on any structural problem; returns a plain dict on success."""
    return RawScenarioComparisonOut(**raw).model_dump()
