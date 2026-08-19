"""Deterministic, application-owned rules for account planning (spec Phase 6).

Two responsibilities, both explicitly application code, never the LLM (spec
Sec.11: "The application owns the evidence IDs"):

1. `sanitize_proposed_action` - intersects every id a raw proposed action
   names (partner_id, supporting_memory_ids, supporting_campaign_ids,
   source_scenario_id) against the ids that actually exist in the
   PlanningContext that was given to the model. An id the model invents is
   dropped, never persisted - this is the same "the application resolves
   bounded identifiers, it does not trust model-supplied ones" principle
   already used for scenario ids (scenario_comparison_agent.py) and
   supporting_memory_ids (build_recommendation_context).
2. `find_duplicate_open_action` - deterministically flags when a proposed
   (partner_id, action_type) pair already has an open PlannedAction, so the
   planner (and the persistence step in app.memory.manager.create_plan)
   never silently creates a second copy of the same open work (spec Sec.31).

Both are pure functions over a schemas.PlanningContext - no DB access here,
same "business rules kept separate from retrieval" split as scenario_rules.py.
"""

from app import schemas

ACTION_TYPES = ("renew", "renegotiate", "test", "expand", "pause", "review_measurement", "follow_up")


def valid_partner_ids(context: schemas.PlanningContext) -> set[str]:
    return {p.partner.partner_id for p in context.partners}


def valid_memory_ids(context: schemas.PlanningContext) -> set[str]:
    """Union of every claim_id actually present in this PlanningContext -
    client strategy claims plus every partner's measurement cautions and
    partner memory. A supporting_memory_ids entry naming anything outside
    this set did not come from the evidence the model was given."""
    ids = {c.claim_id for c in context.client.current_strategy}
    for p in context.partners:
        ids |= {c.claim_id for c in p.measurement_cautions}
        ids |= {c.claim_id for c in p.partner_memory}
    return ids


def valid_campaign_ids(context: schemas.PlanningContext) -> set[str]:
    ids: set[str] = set()
    for p in context.partners:
        ids |= {c.campaign_id for c in p.campaigns}
    return ids


def valid_scenario_ids_for_partner(context: schemas.PlanningContext, partner_id: str) -> set[str]:
    partner = next((p for p in context.partners if p.partner.partner_id == partner_id), None)
    if partner is None or partner.scenario is None:
        return set()
    return {s.scenario.id for s in partner.scenario.scenarios}


def find_duplicate_open_action(context: schemas.PlanningContext, *, partner_id: str, action_type: str) -> schemas.PlanningExistingActionRef | None:
    """A duplicate is the same partner + the same bounded action_type,
    already open (approved/in_progress) - spec Sec.31's exact example."""
    return next(
        (a for a in context.existing_open_actions if a.partner_id == partner_id and a.action_type == action_type),
        None,
    )


def sanitize_proposed_action(raw: dict, *, context: schemas.PlanningContext, index: int) -> schemas.ProposedPlannedAction | None:
    """Returns a fully-sanitized ProposedPlannedAction, or None if the
    action's partner_id doesn't name a real partner in this context (the
    one field that isn't just filtered but disqualifies the whole action -
    an action about a partner that doesn't exist has nothing left to attach
    to)."""
    partners_by_id = {p.partner.partner_id: p for p in context.partners}
    partner_id = raw.get("partner_id")
    partner = partners_by_id.get(partner_id)
    if partner is None:
        return None

    mem_ids = valid_memory_ids(context)
    camp_ids = valid_campaign_ids(context)
    scen_ids = valid_scenario_ids_for_partner(context, partner_id)

    supporting_memory_ids = [i for i in (raw.get("supporting_memory_ids") or []) if i in mem_ids]
    supporting_campaign_ids = [i for i in (raw.get("supporting_campaign_ids") or []) if i in camp_ids]
    source_scenario_id = raw.get("source_scenario_id")
    if source_scenario_id not in scen_ids:
        source_scenario_id = None

    duplicate = find_duplicate_open_action(context, partner_id=partner_id, action_type=raw["action_type"])

    return schemas.ProposedPlannedAction(
        temp_id=f"proposed_{index}",
        partner_id=partner_id,
        partner_name=partner.partner.name,
        action_type=raw["action_type"],
        summary=raw["summary"],
        rationale=raw["rationale"],
        supporting_memory_ids=supporting_memory_ids,
        supporting_campaign_ids=supporting_campaign_ids,
        source_scenario_id=source_scenario_id,
        duplicate_of_planned_action_id=duplicate.id if duplicate else None,
    )
