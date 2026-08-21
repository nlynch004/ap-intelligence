from typing import Any

from app import schemas
from app.llm.factory import call_with_fallback
from app.llm.plan_schema import validate_raw_plan_proposal
from app.memory.planning_rules import sanitize_proposed_action


def generate_plan_proposal(context: schemas.PlanningContext) -> tuple[dict, str]:

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
