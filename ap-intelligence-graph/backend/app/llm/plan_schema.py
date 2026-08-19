"""Pydantic validation for raw plan-proposal-agent output (spec Phase 6).
Same role as scenario_comparison_schema.py: validates the STRUCTURAL shape
`llm/factory.py::call_with_fallback` checks before trusting a live response.

Runtime, PlanningContext-dependent validation (does partner_id name a real
partner, are the supporting ids real, is source_scenario_id one this partner
actually has) is NOT a static Pydantic rule and does not belong here - that
sanitization happens in app.memory.planning_rules, composed into the same
call_with_fallback `validate=` hook by app.agents.plan_agent, exactly like
scenario_comparison_agent.py composes its own runtime check."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

ACTION_TYPES = ("renew", "renegotiate", "test", "expand", "pause", "review_measurement", "follow_up")


class RawProposedPlannedAction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    partner_id: str
    action_type: str
    summary: str
    rationale: str
    supporting_memory_ids: list[str] = []
    supporting_campaign_ids: list[str] = []
    source_scenario_id: str | None = None

    @field_validator("partner_id", "summary", "rationale")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("action_type")
    @classmethod
    def _bounded_action_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ACTION_TYPES:
            raise ValueError(f"action_type {v!r} is not one of {ACTION_TYPES}")
        return v


class RawPlanProposalOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_name: str
    objective: str
    proposed_actions: list[RawProposedPlannedAction] = []

    @field_validator("plan_name", "objective")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


def validate_raw_plan_proposal(raw: object) -> dict:
    """Raises on any structural problem; returns a plain dict on success."""
    return RawPlanProposalOut(**raw).model_dump()
