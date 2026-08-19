"""Orchestrates the memory write pipeline (spec Sec.10):

conversation -> extraction agent -> candidate claims -> schema validation
-> conflict lookup -> operation decision -> (human approval where required)
-> canonical store -> graph refresh

This module owns that orchestration; app/memory/operations.py owns the
actual state transitions.
"""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import schemas
from app.agents.campaign_review_agent import generate_campaign_review
from app.agents.memory_extractor import extract_candidate_claims
from app.agents.memory_history_agent import generate_historical_summary
from app.agents.partner_brief_agent import generate_partner_brief
from app.agents.plan_agent import generate_plan_proposal
from app.agents.scenario_comparison_agent import generate_scenario_comparison
from app.memory.conflict_resolver import decide_operation, find_active_conflict
from app.memory.extraction_schema import ExtractedClaimIn
from app.memory.operations import execute_create, execute_reject, execute_supersede, execute_update, log_activity
from app.memory.predicates import normalize_predicate
from app.memory.retrieval import (
    _resolve_subject_name,
    build_campaign_review_context,
    build_memory_history,
    build_partner_brief_context,
    build_planning_context,
    build_scenario_comparison_context,
    find_changed_predicates,
    open_planned_actions,
)
from app.models import Campaign, Client, MemoryCandidate, MemoryClaim, MemoryEdge, Partner, Plan, PlannedAction, RawEvent, TeamMember
from app.serializers import candidate_to_out


def _propose_candidate_from_raw(
    db: Session, raw: dict, *, client_id: str, client_name: str,
    source_type: str, origin: str, source_message: str | None, origin_detail: dict,
) -> MemoryCandidate | None:
    """Shared per-claim pipeline: schema validation -> alias normalization
    -> deterministic conflict lookup -> pending MemoryCandidate row. Used by
    both propose_candidates_from_message (chat extraction) and
    propose_candidates_from_campaign_review (Phase 2) - one place owns
    "how a raw proposed claim becomes a reviewable candidate," regardless of
    which agent proposed it (spec Sec.18: never silently persisted, and the
    LLM never writes canonical memory directly - see approve_candidate)."""
    # 1. Schema validation - a malformed or out-of-range proposed claim
    # (missing field, confidence outside [0,1], unrecognized claim_class,
    # blank predicate/value) is dropped here and never reaches the
    # candidate table, rather than crashing or silently persisting junk.
    try:
        validated = ExtractedClaimIn(**raw)
    except ValidationError as e:
        first_error = e.errors()[0]["msg"] if e.errors() else "validation error"
        log_activity(
            db, client_id, "REJECT",
            f"Dropped a malformed {origin} claim: {first_error}",
            detail={"raw": raw, "errors": e.errors(), **origin_detail},
        )
        return None

    payload = validated.model_dump()
    if payload["subject_type"] == "client":
        payload["subject_id"] = client_id
    if not payload["subject_label"]:
        payload["subject_label"] = client_name if payload["subject_type"] == "client" else payload["subject_id"]
    # Set here (not by the agent) so the review card can show provenance
    # before approval, not just after (spec Sec.18) - this is also the
    # value execute_create/execute_supersede will use as source.type if
    # approved, via _source_for_candidate below.
    payload["source_type"] = source_type

    # 2. Deterministic alias normalization - rewrites a semantically
    # equivalent predicate spelling (e.g. "client_strategy") to the
    # canonical name ("partnership_strategy") *before* conflict lookup,
    # so a differently-worded restatement of an existing belief still
    # collides with it instead of silently missing the conflict.
    normalized_predicate, is_known = normalize_predicate(payload["predicate"])
    payload["predicate"] = normalized_predicate

    if is_known:
        existing = find_active_conflict(
            db,
            subject_type=payload["subject_type"],
            subject_id=payload["subject_id"],
            predicate=payload["predicate"],
            client_id=client_id if payload["subject_type"] == "client" else None,
        )
        operation = decide_operation(payload, existing)
    else:
        # 3. Genuinely unknown predicate: do NOT guess which existing
        # belief (if any) this might contradict, and do NOT silently
        # treat it as a normal CREATE. Flag it for explicit human
        # review - it still requires the same manual approval every
        # candidate does, but is visibly distinguished (in the API/DB)
        # as an unrecognized concept rather than a matched-vocabulary one.
        existing = None
        operation = "REQUEST_HUMAN_REVIEW"

    candidate = MemoryCandidate(
        client_id=client_id,
        claim_payload=payload,
        proposed_operation=operation,
        conflict_with_claim_id=existing.id if operation == "SUPERSEDE" else None,
        status="pending",
        source_message=source_message,
        origin=origin,
        origin_detail=origin_detail,
    )
    db.add(candidate)
    return candidate


def propose_candidates_from_message(db: Session, *, client_id: str, message: str) -> tuple[list[MemoryCandidate], str]:
    """Runs the extraction agent, validates + normalizes each candidate,
    deterministically checks it against existing active memory, and
    persists surviving candidates as pending MemoryCandidate rows
    (spec Sec.18 - never silently persisted, and the LLM never writes
    canonical memory directly - see approve_candidate)."""
    client = db.get(Client, client_id)
    client_name = client.name if client else client_id

    db.add(RawEvent(client_id=client_id, event_type="chat_message", payload={"message": message}))

    known_predicates = sorted({
        c.predicate for c in
        db.query(MemoryClaim).filter(MemoryClaim.client_id == client_id, MemoryClaim.status == "active").all()
    })
    # Partners this client has actually run campaigns with (same join chat.py
    # uses to resolve a partner mention) - given to the extraction agent so
    # a relationship_status/negotiation_history claim about a named partner
    # resolves to that partner's real id instead of subject_type defaulting
    # to "client" or a fabricated slug (spec follow-up: subject_type
    # resolution accuracy).
    known_partners = [
        {"id": p.id, "name": p.name, "kind": p.kind}
        for p in (
            db.query(Partner)
            .join(Campaign, Campaign.partner_id == Partner.id)
            .filter(Campaign.client_id == client_id)
            .distinct()
            .all()
        )
    ]
    raw_claims, provider_name = extract_candidate_claims(message, client_id, client_name, known_predicates, known_partners)

    candidates: list[MemoryCandidate] = []
    for raw in raw_claims:
        candidate = _propose_candidate_from_raw(
            db, raw, client_id=client_id, client_name=client_name,
            source_type="account_team_statement", origin="chat",
            source_message=message, origin_detail={},
        )
        if candidate:
            candidates.append(candidate)

    db.flush()
    return candidates, provider_name


def propose_candidates_from_campaign_review(
    db: Session, *, client_id: str, client_name: str, campaign_id: str, campaign_label: str, raw_lessons: list[dict],
) -> list[MemoryCandidate]:
    """Same governed candidate pipeline as propose_candidates_from_message,
    fed by the campaign review agent's candidate_lessons instead of the chat
    extractor's claims (spec Phase 2: "Candidate lessons must reuse the
    existing governed memory-candidate pipeline"). Every lesson still passes
    through ExtractedClaimIn validation, alias normalization, and
    deterministic conflict lookup - a lesson naming an unrecognized
    predicate still routes to REQUEST_HUMAN_REVIEW, exactly like an
    unrecognized chat-extracted claim would."""
    candidates: list[MemoryCandidate] = []
    for raw in raw_lessons:
        candidate = _propose_candidate_from_raw(
            db, raw, client_id=client_id, client_name=client_name,
            source_type="agent_inference", origin="campaign_review",
            source_message=f"Campaign review — {campaign_label}",
            origin_detail={"campaign_id": campaign_id, "campaign_label": campaign_label},
        )
        if candidate:
            candidates.append(candidate)

    db.flush()
    return candidates


def run_campaign_review(db: Session, *, campaign_id: str) -> schemas.CampaignReviewResponse | None:
    """Orchestrates Phase 2's full pipeline for one campaign: deterministic
    evidence (app.memory.retrieval) -> bounded LLM call
    (app.agents.campaign_review_agent) -> candidate_lessons routed through
    the governed candidate pipeline above -> serialized response. Called by
    both routers/campaign_review.py (the "Review campaign" button) and
    routers/chat.py (the bounded chat intent) so the two entry points can
    never drift apart. Returns None if the campaign doesn't exist."""
    ctx = build_campaign_review_context(db, campaign_id=campaign_id)
    if ctx is None:
        return None

    client = db.get(Client, ctx["client_id"])
    client_name = client.name if client else ctx["client_id"]

    raw, _provider = generate_campaign_review(ctx["evidence"].model_dump())

    candidates = propose_candidates_from_campaign_review(
        db, client_id=ctx["client_id"], client_name=client_name, campaign_id=campaign_id,
        campaign_label=ctx["campaign_label"], raw_lessons=raw.get("candidate_lessons", []),
    )
    db.commit()

    conflicts = {
        c.conflict_with_claim_id: db.get(MemoryClaim, c.conflict_with_claim_id)
        for c in candidates if c.conflict_with_claim_id
    }
    candidate_outs = [candidate_to_out(c, conflicts.get(c.conflict_with_claim_id)) for c in candidates]

    return schemas.CampaignReviewResponse(
        client_id=ctx["client_id"], partner_id=ctx["partner_id"], campaign_id=campaign_id,
        evidence=ctx["evidence"], summary=raw["summary"],
        what_worked=raw.get("what_worked", []), what_is_uncertain=raw.get("what_is_uncertain", []),
        planning_implications=raw.get("planning_implications", []), candidate_lessons=candidate_outs,
    )


def run_partner_brief(db: Session, *, partner_id: str, client_id: str) -> schemas.PartnerBriefResponse | None:
    """Orchestrates Phase 3's pipeline for one partner: deterministic
    evidence (app.memory.retrieval.build_partner_brief_context) -> bounded
    LLM call (app.agents.partner_brief_agent) -> serialized response.
    Read-only - unlike run_campaign_review, this never writes anything to
    the database (spec Phase 3: "No new memory from Partner Brief yet").
    Called by both routers/partner_brief.py (the "Generate partner brief"
    button) and routers/chat.py (the bounded chat intent). Returns None if
    the partner doesn't exist."""
    ctx = build_partner_brief_context(db, partner_id=partner_id, client_id=client_id)
    if ctx is None:
        return None

    raw, _provider = generate_partner_brief(ctx["evidence"].model_dump())

    return schemas.PartnerBriefResponse(
        client_id=ctx["client_id"], partner_id=ctx["partner_id"], evidence=ctx["evidence"],
        relationship_summary=raw["relationship_summary"], performance_summary=raw["performance_summary"],
        what_to_know=raw.get("what_to_know", []), negotiation_considerations=raw.get("negotiation_considerations", []),
        measurement_considerations=raw.get("measurement_considerations", []),
        open_questions=raw.get("open_questions", []), planning_implications=raw.get("planning_implications", []),
    )


def run_memory_history(
    db: Session, *, subject_type: str, subject_id: str, predicate: str, client_id: str | None = None,
) -> schemas.MemoryHistoryResponse | None:
    """Orchestrates Phase 4's pipeline for one (subject, predicate):
    deterministic timeline (app.memory.retrieval.build_memory_history) ->
    optional bounded LLM narration (app.agents.memory_history_agent) ->
    serialized response. Strictly read-only (spec Phase 4 Sec.23) - no
    MemoryCandidate, MemoryClaim, Decision, or portfolio-evidence write
    ever happens here, unlike run_campaign_review. Called by both
    routers/memory_history.py and routers/chat.py's bounded historical
    intent. Returns None if no claim at all exists for this concept."""
    result = build_memory_history(db, subject_type=subject_type, subject_id=subject_id, predicate=predicate, client_id=client_id)
    if result is None:
        return None

    entries = result["entries"]
    timeline = schemas.MemoryHistoryTimeline(
        subject=schemas.MemoryHistorySubject(subject_type=subject_type, subject_id=subject_id, name=result["subject_name"]),
        predicate=predicate, current_claim_id=result["current_claim_id"], changes=entries,
    )

    raw, _provider = generate_historical_summary({
        "subject_name": result["subject_name"], "predicate": predicate,
        "current_claim_id": result["current_claim_id"],
        "entries": [e.model_dump() for e in entries],
    })

    return schemas.MemoryHistoryResponse(
        timeline=timeline, summary=raw.get("summary", ""), material_changes=raw.get("material_changes", []),
        current_state=raw.get("current_state", ""), historical_context=raw.get("historical_context", []),
    )


def run_what_changed_summary(db: Session, *, subject_type: str, subject_id: str, client_id: str | None = None) -> schemas.WhatChangedSummary:
    """Broader 'what changed?' view (spec Phase 4 Sec.10): deterministically
    finds every predicate for this subject with genuine version history
    and reports only the oldest-vs-newest-active value pair for each -
    never a fabricated 'change' from two unrelated claims. Purely
    deterministic; no LLM call (nothing here requires narration beyond the
    plain old->new pairs, and keeping this deterministic-only avoids a
    second narrative layer with its own hallucination surface for a
    summary that's already just a values diff)."""
    changed = find_changed_predicates(db, subject_type=subject_type, subject_id=subject_id, client_id=client_id)
    subject_name = _resolve_subject_name(db, subject_type, subject_id)
    dimensions = [
        schemas.ChangedDimension(
            subject_type=subject_type, subject_id=subject_id, subject_name=subject_name,
            predicate=c["predicate"], old_value=c["old_value"], new_value=c["new_value"],
        )
        for c in changed
    ]
    return schemas.WhatChangedSummary(
        subject=schemas.MemoryHistorySubject(subject_type=subject_type, subject_id=subject_id, name=subject_name),
        changed_dimensions=dimensions,
    )


def run_scenario_comparison(
    db: Session, *, client_id: str, partner_id: str, current_ask: float,
) -> schemas.ScenarioComparisonResponse | None:
    """Orchestrates Phase 5's pipeline for one partner: deterministic
    scenario construction + assessment (app.memory.retrieval.
    build_scenario_comparison_context, which itself calls
    app.memory.scenario_rules) -> bounded LLM narration/choice
    (app.agents.scenario_comparison_agent) -> serialized response.
    Strictly read-only (spec Phase 5 Sec.20) - no MemoryClaim,
    MemoryCandidate, Decision, Outcome, or PortfolioPattern write ever
    happens here. Called by both routers/scenario_comparison.py (the
    "Compare scenarios" button) and routers/chat.py's bounded intent.
    Returns None if the partner doesn't exist."""
    ctx = build_scenario_comparison_context(db, partner_id=partner_id, client_id=client_id, current_ask=current_ask)
    if ctx is None:
        return None

    evidence = ctx["evidence"]
    valid_scenario_ids = {s.scenario.id for s in evidence.scenarios}
    raw, _provider = generate_scenario_comparison(evidence.model_dump(), valid_scenario_ids=valid_scenario_ids)

    return schemas.ScenarioComparisonResponse(
        client_id=ctx["client_id"], partner_id=ctx["partner_id"], evidence=evidence,
        preferred_scenario_id=raw["preferred_scenario_id"], comparison_summary=raw["comparison_summary"],
        tradeoffs=raw.get("tradeoffs", []), uncertainties=raw.get("uncertainties", []),
        questions_before_finalizing=raw.get("questions_before_finalizing", []), confidence=raw["confidence"],
    )


def _source_for_candidate(candidate: MemoryCandidate) -> dict:
    if candidate.origin == "campaign_review":
        detail = candidate.origin_detail or {}
        return {
            "type": "agent_inference",
            "source_id": f"campaign_review:{candidate.id}",
            "speaker": None,
            "campaign_id": detail.get("campaign_id"),
            "campaign_label": detail.get("campaign_label"),
        }
    return {
        "type": "account_team_statement",
        "source_id": f"chat:{candidate.id}",
        "speaker": "account_manager",
        "message_excerpt": (candidate.source_message or "")[:280],
    }


def approve_candidate(db: Session, candidate: MemoryCandidate) -> dict:
    """Returns a dict with keys: operation_executed, claim, superseded_claim,
    requires_conflict_resolution, conflict_with_claim."""
    source = _source_for_candidate(candidate)

    if candidate.proposed_operation == "SUPERSEDE":
        # Do not auto-execute a supersede on review approval - surface the
        # conflict dialog first (spec Sec.19 Scene 3 is a distinct step).
        candidate.status = "approved"
        db.flush()
        conflicting = db.get(MemoryClaim, candidate.conflict_with_claim_id) if candidate.conflict_with_claim_id else None
        return {
            "operation_executed": None,
            "claim": None,
            "superseded_claim": None,
            "requires_conflict_resolution": True,
            "conflict_with_claim": conflicting,
        }

    if candidate.proposed_operation == "UPDATE":
        existing = find_active_conflict(
            db,
            subject_type=candidate.claim_payload["subject_type"],
            subject_id=candidate.claim_payload["subject_id"],
            predicate=candidate.claim_payload["predicate"],
            client_id=candidate.client_id,
        )
        claim = execute_update(db, existing, candidate.claim_payload, source=source)
        candidate.status = "approved"
        db.flush()
        return {"operation_executed": "UPDATE", "claim": claim, "superseded_claim": None, "requires_conflict_resolution": False, "conflict_with_claim": None}

    # CREATE, and also REQUEST_HUMAN_REVIEW (an unrecognized-predicate
    # candidate from propose_candidates_from_message): both execute as a
    # plain create once a human has explicitly clicked Approve here - that
    # click *is* the human review the label promises. The distinction only
    # matters pre-approval, where REQUEST_HUMAN_REVIEW candidates skip
    # automatic conflict matching against the canonical vocabulary.
    claim = execute_create(db, candidate.claim_payload, client_id=candidate.client_id, source=source)
    candidate.status = "approved"
    db.flush()
    return {"operation_executed": "CREATE", "claim": claim, "superseded_claim": None, "requires_conflict_resolution": False, "conflict_with_claim": None}


def reject_candidate(db: Session, candidate: MemoryCandidate) -> None:
    candidate.status = "rejected"
    execute_reject(db, candidate.client_id, f"Candidate rejected: {candidate.claim_payload.get('predicate')} = {candidate.claim_payload.get('value')}")
    db.flush()


def resolve_conflict(db: Session, candidate: MemoryCandidate, operation: str) -> dict:
    source = _source_for_candidate(candidate)

    if operation == "REJECT":
        candidate.status = "rejected"
        execute_reject(db, candidate.client_id, "Conflicting candidate rejected; prior belief retained.")
        return {"new_claim": None, "superseded_claim": None}

    if operation != "SUPERSEDE":
        raise ValueError(f"Unsupported conflict resolution operation: {operation}")

    existing = db.get(MemoryClaim, candidate.conflict_with_claim_id)
    if existing is None:
        raise ValueError("Conflicting claim not found")

    new_claim, old_claim = execute_supersede(db, existing, candidate.claim_payload, client_id=candidate.client_id, source=source)
    candidate.status = "approved"
    db.flush()
    return {"new_claim": new_claim, "superseded_claim": old_claim}


# ---- account planning (Phase 6) ----


def _planned_action_to_out(db: Session, a: PlannedAction) -> schemas.PlannedActionOut:
    partner = db.get(Partner, a.partner_id) if a.partner_id else None
    owner = db.get(TeamMember, a.owner_id) if a.owner_id else None
    return schemas.PlannedActionOut(
        id=a.id, plan_id=a.plan_id, client_id=a.client_id, partner_id=a.partner_id,
        partner_name=partner.name if partner else None, campaign_id=a.campaign_id, action_type=a.action_type,
        summary=a.summary, rationale=a.rationale, owner_id=a.owner_id, owner_name=owner.name if owner else None,
        due_date=a.due_date, status=a.status, supporting_memory_ids=a.supporting_memory_ids,
        supporting_campaign_ids=a.supporting_campaign_ids, source_scenario_id=a.source_scenario_id,
        source_decision_id=a.source_decision_id, synthetic=a.synthetic,
        created_at=a.created_at.isoformat(), updated_at=a.updated_at.isoformat(),
    )


def _plan_to_out(db: Session, plan: Plan) -> schemas.PlanOut:
    actions = db.query(PlannedAction).filter(PlannedAction.plan_id == plan.id).order_by(PlannedAction.created_at).all()
    return schemas.PlanOut(
        id=plan.id, client_id=plan.client_id, name=plan.name, planning_period=plan.planning_period,
        objective=plan.objective, status=plan.status, synthetic=plan.synthetic,
        created_at=plan.created_at.isoformat(), updated_at=plan.updated_at.isoformat(),
        actions=[_planned_action_to_out(db, a) for a in actions],
    )


def propose_plan(
    db: Session, *, client_id: str, partner_ids: list[str] | None = None,
    planning_period: str | None = None, scenario_inputs: list[schemas.ScenarioComparisonRef] | None = None,
) -> schemas.PlanProposalResponse | None:
    """Orchestrates Phase 6's proposal step: deterministic PlanningContext
    (app.memory.retrieval.build_planning_context) -> bounded LLM proposal,
    already sanitized against real ids (app.agents.plan_agent) -> serialized
    response. Strictly read-only (spec Sec.14 step 1 - "may remain
    frontend/API response state only") - no Plan or PlannedAction row is
    ever created here, regardless of how confident the proposal is. Called
    by both routers/plans.py (the "Build plan" button) and routers/chat.py's
    bounded intent. Returns None if the client doesn't exist."""
    context = build_planning_context(
        db, client_id=client_id, partner_ids=partner_ids, planning_period=planning_period, scenario_inputs=scenario_inputs,
    )
    if context is None:
        return None

    raw, _provider = generate_plan_proposal(context)

    return schemas.PlanProposalResponse(
        client_id=client_id, plan_name=raw["plan_name"], objective=raw["objective"],
        planning_period=planning_period,
        proposed_actions=[schemas.ProposedPlannedAction(**a) for a in raw["proposed_actions"]],
        context=context,
    )


def create_plan(db: Session, req: schemas.PlanCreateRequest) -> schemas.PlanCreateResponse | None:
    """Persists a Plan and its approved PlannedActions - the ONLY place in
    the app that writes either table (spec Sec.14 step 3). Every action in
    `req.actions` is, by construction, one the human has already approved
    (the frontend only ever builds this request from ProposedPlannedActions
    the user clicked Approve on - see PlanProposalPanel.tsx) - so every
    PlannedAction created here starts at status "approved" directly, never
    "proposed" (spec Sec.8/29). Re-applies the duplicate-open-action guard
    one more time here, deterministically and independent of whatever the
    proposal step already filtered (spec Sec.31: "Do not silently create
    duplicates") - both against already-persisted open actions and against
    other actions in this same request, since two proposed actions for the
    same partner+action_type could otherwise both slip through the
    proposal-time check if constructed by hand via the API. Returns None if
    the client doesn't exist."""
    client = db.get(Client, req.client_id)
    if client is None:
        return None

    plan = Plan(
        client_id=req.client_id, name=req.name, planning_period=req.planning_period,
        objective=req.objective, status="approved", synthetic=False, source={"origin": "account_planning"},
    )
    db.add(plan)
    db.flush()
    db.add(MemoryEdge(from_type="client", from_id=req.client_id, to_type="plan", to_id=plan.id, relationship="HAS_PLAN", client_id=req.client_id))

    existing_open = [
        schemas.PlanningExistingActionRef(id=a.id, partner_id=a.partner_id, action_type=a.action_type, summary=a.summary, status=a.status)
        for a in open_planned_actions(db, req.client_id)
    ]
    seen_in_request: set[tuple[str | None, str]] = set()
    skipped: list[str] = []
    created = 0

    for a in req.actions:
        key = (a.partner_id, a.action_type)
        already_open = any(o.partner_id == a.partner_id and o.action_type == a.action_type for o in existing_open)
        if already_open or key in seen_in_request:
            skipped.append(a.summary)
            continue
        seen_in_request.add(key)

        # Defense in depth: an owner/partner/campaign id that doesn't
        # resolve to a real row is dropped rather than persisted as a
        # dangling reference - the frontend only ever offers real ids from
        # the graph, but the API itself must not trust a caller blindly
        # (same "the application owns the ids" principle as
        # planning_rules.sanitize_proposed_action).
        owner_id = a.owner_id if a.owner_id and db.get(TeamMember, a.owner_id) else None
        partner_id = a.partner_id if a.partner_id and db.get(Partner, a.partner_id) else None
        campaign_id = a.campaign_id if a.campaign_id and db.get(Campaign, a.campaign_id) else None

        action = PlannedAction(
            plan_id=plan.id, client_id=req.client_id, partner_id=partner_id, campaign_id=campaign_id,
            action_type=a.action_type, summary=a.summary, rationale=a.rationale, owner_id=owner_id,
            due_date=a.due_date, status="approved", supporting_memory_ids=a.supporting_memory_ids,
            supporting_campaign_ids=a.supporting_campaign_ids, source_scenario_id=a.source_scenario_id, synthetic=False,
        )
        db.add(action)
        db.flush()
        created += 1

        db.add(MemoryEdge(from_type="plan", from_id=plan.id, to_type="planned_action", to_id=action.id, relationship="CONTAINS_ACTION", client_id=req.client_id))
        if partner_id:
            db.add(MemoryEdge(from_type="planned_action", from_id=action.id, to_type="partner", to_id=partner_id, relationship="APPLIES_TO", client_id=req.client_id))

        log_activity(
            db, req.client_id, "PLANNED_ACTION_APPROVED", a.summary,
            detail={"planned_action_id": action.id, "plan_id": plan.id, "action_type": a.action_type},
        )

    log_activity(
        db, req.client_id, "PLAN_CREATED", f"{req.name} created with {created} approved action(s).",
        detail={"plan_id": plan.id, "action_count": created},
    )
    db.commit()

    return schemas.PlanCreateResponse(plan=_plan_to_out(db, plan), skipped_duplicate_actions=skipped)


def list_plans_for_client(db: Session, client_id: str) -> list[schemas.PlanOut]:
    plans = db.query(Plan).filter(Plan.client_id == client_id).order_by(Plan.created_at).all()
    return [_plan_to_out(db, p) for p in plans]


def update_plan(db: Session, plan_id: str, req: schemas.PlanUpdate) -> schemas.PlanOut | None:
    plan = db.get(Plan, plan_id)
    if plan is None:
        return None
    plan.status = req.status
    db.flush()
    log_activity(db, plan.client_id, "PLANNED_ACTION_STATUS_CHANGED", f"{plan.name} status: {req.status}", detail={"plan_id": plan.id, "status": req.status})
    db.commit()
    return _plan_to_out(db, plan)


def update_planned_action(db: Session, action_id: str, req: schemas.PlannedActionUpdate) -> schemas.PlannedActionOut | None:
    """Manual post-approval editing (spec Sec.19/20/38): status/owner/
    due_date/summary only - never evidence fields (supporting_memory_ids,
    supporting_campaign_ids, source_scenario_id, rationale are immutable
    here by construction, since PlannedActionUpdate doesn't expose them)."""
    action = db.get(PlannedAction, action_id)
    if action is None:
        return None

    changed_status = False
    if req.status is not None and req.status != action.status:
        action.status = req.status
        changed_status = True
    if req.owner_id is not None:
        action.owner_id = req.owner_id if db.get(TeamMember, req.owner_id) else None
    if req.due_date is not None:
        action.due_date = req.due_date
    if req.summary is not None and req.summary.strip():
        action.summary = req.summary.strip()

    db.flush()
    if changed_status:
        log_activity(
            db, action.client_id, "PLANNED_ACTION_STATUS_CHANGED", f"{action.summary} → {action.status}",
            detail={"planned_action_id": action.id, "status": action.status},
        )
    db.commit()
    return _planned_action_to_out(db, action)
