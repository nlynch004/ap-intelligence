"""Plan-proposal agent (spec Phase 6). Input: PlanningContext.model_dump() -
already-retrieved, already-computed evidence only (app/memory/retrieval.py::
build_planning_context), including any partner-level scenario-comparison
result the frontend chose to carry into planning via "Use in plan." Output:
a draft plan name/objective plus zero or more proposed actions, each
sanitized against the real evidence before it is ever shown to a human
(app/memory/planning_rules.py) - the model explains and proposes; it never
gets the final say on which partner/memory/campaign/scenario ids survive
into the response, and nothing it returns here is ever persisted directly."""

from typing import Any

from app import schemas
from app.llm.factory import call_with_fallback
from app.llm.plan_schema import validate_raw_plan_proposal
from app.memory.planning_rules import sanitize_proposed_action


def generate_plan_proposal(context: schemas.PlanningContext) -> tuple[dict, str]:
    """Returns (dict with plan_name/objective/proposed_actions - the latter
    already schemas.ProposedPlannedAction-shaped and fully sanitized against
    `context` - , provider_name). Falls back to the deterministic mock if the
    live provider's response is structurally invalid OR names only
    nonexistent partners (i.e. nothing survives sanitization despite the
    model having proposed something) - the same "a validation failure is
    treated exactly like a call failure" contract every other agent uses."""

    def _validate(raw: object) -> dict:
        validated = validate_raw_plan_proposal(raw)
        raw_actions = validated["proposed_actions"]
        sanitized = [
            action for action in (
                sanitize_proposed_action(a, context=context, index=i) for i, a in enumerate(raw_actions)
            )
            if action is not None
        ]
        if raw_actions and not sanitized:
            raise ValueError("every proposed action named a partner_id not present in the supplied PlanningContext")
        return {
            "plan_name": validated["plan_name"],
            "objective": validated["objective"],
            "proposed_actions": [a.model_dump() for a in sanitized],
        }

    result, provider_name = call_with_fallback("propose_plan", context.model_dump(), validate=_validate)
    return result, provider_name
