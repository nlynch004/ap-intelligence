from app import schemas

ACTION_TYPES = ("renew", "renegotiate", "test", "expand", "pause", "review_measurement", "follow_up")


def valid_partner_ids(context: schemas.PlanningContext) -> set[str]:
    return {p.partner.partner_id for p in context.partners}


def valid_memory_ids(context: schemas.PlanningContext) -> set[str]:
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
    return next(
        (a for a in context.existing_open_actions if a.partner_id == partner_id and a.action_type == action_type),
        None,
    )


def sanitize_proposed_action(raw: dict, *, context: schemas.PlanningContext, index: int) -> schemas.ProposedPlannedAction | None:
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
