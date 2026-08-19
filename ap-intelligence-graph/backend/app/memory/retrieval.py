"""Filtered + scored retrieval (spec Sec.15). Produces the compact evidence
brief handed to the recommendation agent - never the raw graph - and the
structured DecisionEvidence shown to the user (spec Step 5).

Both are built from the same retrieved rows in one place, so the LLM's
evidence_brief and the UI's decision_evidence never diverge, and neither
router duplicates this construction.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import schemas
from app.formatting import extract_dollar_amount, format_month
from app.memory.scenario_rules import assess_scenario, build_scenarios
from app.memory.scoring import query_terms, score_claim
from app.models import Campaign, Client, Decision, MemoryClaim, MemoryEdge, Outcome, Partner, PlannedAction, PortfolioPattern, TeamMember


def active_client_memories(db: Session, client_id: str) -> list[MemoryClaim]:
    """Normal retrieval: active + currently valid only (spec Sec.8)."""
    return (
        db.query(MemoryClaim)
        .filter(MemoryClaim.client_id == client_id, MemoryClaim.status == "active")
        .order_by(MemoryClaim.predicate)
        .all()
    )


def active_partner_memories(db: Session, partner_id: str) -> list[MemoryClaim]:
    """Active claims whose SUBJECT is this partner (creator/publisher) -
    distinct from active_client_memories, which is scoped by the claim's
    client_id column and can include partner-subject claims recorded under
    that client's account (spec Phase 2: campaign review needs both a
    'relevant active client memory' bucket and a separate 'relevant partner
    memory' bucket, not one mixed list)."""
    return (
        db.query(MemoryClaim)
        .filter(
            MemoryClaim.subject_type.in_(["creator", "publisher"]),
            MemoryClaim.subject_id == partner_id,
            MemoryClaim.status == "active",
        )
        .order_by(MemoryClaim.predicate)
        .all()
    )


def _select_hybrid_pattern(db: Session) -> PortfolioPattern | None:
    return (
        db.query(PortfolioPattern)
        .filter(PortfolioPattern.status == "approved_portfolio_pattern")
        .first()
    )


def _campaign_performance(camp: Campaign) -> schemas.CampaignPerformance:
    roas = round(camp.attributed_revenue / camp.flat_fee, 2) if camp.flat_fee and camp.attributed_revenue is not None else None
    return schemas.CampaignPerformance(
        campaign_id=camp.id, month=camp.month, month_label=format_month(camp.month),
        fee=camp.flat_fee, attributed_revenue=camp.attributed_revenue, attributed_roas=roas,
        link_clicks=camp.link_clicks, code_redemptions=camp.code_redemptions,
        impressions=camp.impressions, engagements=camp.engagements,
    )


def _commercial_ask(question: str, campaigns: list[Campaign]) -> schemas.CommercialAsk:
    proposed_fee = extract_dollar_amount(question)
    prior_fee = campaigns[-1].flat_fee if campaigns else None  # campaigns is month-sorted - most recent
    increase_pct = round((proposed_fee - prior_fee) / prior_fee * 100, 3) if proposed_fee and prior_fee else None
    return schemas.CommercialAsk(proposed_fee=proposed_fee, prior_fee=prior_fee, increase_pct=increase_pct)


def _measurement_caution(db: Session, claim: MemoryClaim) -> schemas.MeasurementCaution:
    camp = db.get(Campaign, claim.subject_id) if claim.subject_type == "campaign" else None
    if camp:
        summary = (
            f"{format_month(camp.month)} recorded {camp.code_redemptions:,} promo-code redemptions from "
            f"{camp.link_clicks:,} tracked link clicks. This may indicate off-link code distribution or "
            f"promo-code leakage. Unverified hypothesis — not a confirmed attribution failure."
        )
    else:
        summary = f"{claim.value.replace('_', ' ')} — unverified hypothesis, not a confirmed fact."
    return schemas.MeasurementCaution(
        claim_id=claim.id, claim_class=claim.claim_class, status=claim.status, confidence=claim.confidence,
        value=claim.value, summary=summary, campaign_id=camp.id if camp else None,
        link_clicks=camp.link_clicks if camp else None, code_redemptions=camp.code_redemptions if camp else None,
        source_type=(claim.source or {}).get("type"),
    )


def _client_memory_item(c: MemoryClaim) -> schemas.ClientMemoryItem:
    return schemas.ClientMemoryItem(claim_id=c.id, predicate=c.predicate, value=c.value, claim_class=c.claim_class, confidence=c.confidence)


def _partner_memory_item(c: MemoryClaim) -> schemas.PartnerMemoryItem:
    return schemas.PartnerMemoryItem(
        claim_id=c.id, predicate=c.predicate, value=c.value, claim_class=c.claim_class,
        confidence=c.confidence, status=c.status, source=c.source or {},
    )


def _prior_campaign_comparison(campaigns_sorted: list[Campaign], current: Campaign) -> schemas.PriorCampaignComparison:
    """Deterministic delta vs. the same partner's immediately prior campaign
    (month-sorted). All arithmetic here, never left to the LLM (spec Phase 2:
    'All numeric values and comparisons must be application-calculated')."""
    idx = next((i for i, c in enumerate(campaigns_sorted) if c.id == current.id), None)
    if idx is None or idx == 0:
        return schemas.PriorCampaignComparison(has_prior=False)
    prior = campaigns_sorted[idx - 1]

    def roas(c: Campaign) -> float | None:
        return round(c.attributed_revenue / c.flat_fee, 2) if c.flat_fee and c.attributed_revenue is not None else None

    cur_roas, prior_roas = roas(current), roas(prior)
    fee_delta = current.flat_fee - prior.flat_fee if current.flat_fee is not None and prior.flat_fee is not None else None
    fee_delta_pct = round(fee_delta / prior.flat_fee * 100, 2) if fee_delta is not None and prior.flat_fee else None
    revenue_delta = (
        current.attributed_revenue - prior.attributed_revenue
        if current.attributed_revenue is not None and prior.attributed_revenue is not None else None
    )
    revenue_delta_pct = round(revenue_delta / prior.attributed_revenue * 100, 2) if revenue_delta is not None and prior.attributed_revenue else None
    roas_delta = round(cur_roas - prior_roas, 2) if cur_roas is not None and prior_roas is not None else None

    return schemas.PriorCampaignComparison(
        has_prior=True, prior_month_label=format_month(prior.month),
        fee_delta=fee_delta, fee_delta_pct=fee_delta_pct,
        revenue_delta=revenue_delta, revenue_delta_pct=revenue_delta_pct,
        roas_delta=roas_delta,
    )


def _portfolio_evidence_payload(pattern: PortfolioPattern | None) -> schemas.PortfolioEvidence | None:
    if not pattern:
        return None
    return schemas.PortfolioEvidence(
        pattern_id=pattern.id, evidence_count=pattern.evidence_count, positive_outcomes=pattern.positive_outcomes,
        description=pattern.description, synthetic=pattern.synthetic,
    )


def build_recommendation_context(db: Session, *, client_id: str, partner_id: str, question: str) -> dict:
    client = db.get(Client, client_id)
    partner = db.get(Partner, partner_id)

    terms = query_terms(question, partner.name if partner else "", client.name if client else "")
    entity_ids = {client_id, partner_id}

    # Normal retrieval is active-only (spec Sec.8), but the recommendation
    # context is a deliberate exception: needs_review hypotheses tied to this
    # partner's campaigns must still surface, clearly labeled as caution, per
    # spec Sec.15's evidence-brief format and Sec.19 Scene 4.
    candidate_claims = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.status.in_(["active", "needs_review"]))
        .filter((MemoryClaim.client_id == client_id) | (MemoryClaim.client_id.is_(None)))
        .all()
    )
    scored = sorted(
        candidate_claims,
        key=lambda c: score_claim(c, terms=terms, entity_ids=entity_ids, client_id=client_id),
        reverse=True,
    )

    # Active-only, non-hypothesis, client-scoped - a superseded claim's
    # status is "superseded" so it is excluded here by construction, the
    # same filter both the evidence_brief and decision_evidence.client_memory
    # rely on (spec Step 5 Sec.4 - no duplicated filtering logic).
    client_memories = [c for c in scored if c.client_id == client_id and c.claim_class != "hypothesis" and c.status == "active"]
    hypotheses = [
        c for c in scored
        if c.claim_class == "hypothesis" and c.subject_id in {
            camp.id for camp in db.query(Campaign).filter(Campaign.partner_id == partner_id).all()
        }
    ]

    pattern = _select_hybrid_pattern(db)

    # Sorted chronologically rather than relying on DB insertion order, so
    # "prior fee" (commercial ask) and "prior performance" (evidence table)
    # both deterministically mean "most recent campaign" / "in month order."
    campaigns = sorted(
        db.query(Campaign).filter(Campaign.partner_id == partner_id, Campaign.client_id == client_id).all(),
        key=lambda c: c.month,
    )

    brief_lines = ["TRUSTED CLIENT MEMORY"]
    for c in client_memories[:5]:
        brief_lines.append(f"- {client.name} {c.predicate.replace('_', ' ')}: {c.value.replace('_', ' ')}.")

    brief_lines.append("\nCURRENT PARTNER DATA")
    if campaigns:
        best = max(campaigns, key=lambda c: c.attributed_revenue or 0)
        brief_lines.append(f"- {partner.name} has {len(campaigns)} prior campaign(s) with attributed revenue up to ${best.attributed_revenue:,.0f}.")
    for h in hypotheses[:2]:
        camp = db.get(Campaign, h.subject_id)
        if camp:
            brief_lines.append(
                f"- The {camp.month} campaign shows an unusual redemption-to-click relationship "
                f"({camp.code_redemptions} redemptions vs {camp.link_clicks} clicks)."
            )

    brief_lines.append("\nPORTFOLIO EXPERIENCE")
    if pattern:
        brief_lines.append(
            f"- {pattern.evidence_count} comparable creator-renewal decisions across AP's synthetic portfolio "
            f"({pattern.positive_outcomes} positive)."
        )
        brief_lines.append(
            f"- Hybrid compensation succeeded {pattern.hybrid_success_rate:.0%} of the time vs "
            f"{pattern.flat_fee_success_rate:.0%} for flat-fee renewal in comparable cases (synthetic AP portfolio data)."
        )

    if hypotheses:
        brief_lines.append("\nCAUTION")
        for h in hypotheses[:2]:
            brief_lines.append(f"- {h.value.replace('_', ' ')} is an unverified hypothesis (confidence {h.confidence:.2f}), not a confirmed fact.")

    evidence_brief = "\n".join(brief_lines)

    supporting_memory_ids = [c.id for c in client_memories[:5]] + [h.id for h in hypotheses[:2]]
    if pattern:
        supporting_memory_ids.append(pattern.id)

    primary_goal = next((c.value for c in client_memories if c.predicate == "primary_growth_objective"), None)
    strategy = next((c.value for c in client_memories if c.predicate == "partnership_strategy"), None)

    campaign_context = {}
    if campaigns:
        campaign_context = {"prior_fee": campaigns[-1].flat_fee}

    # Structured decision evidence (spec Step 5) - built once, here, from the
    # exact same rows above (client_memories, hypotheses, campaigns, pattern)
    # already fetched for evidence_brief. Neither router reconstructs this.
    decision_evidence = schemas.DecisionEvidence(
        commercial_ask=_commercial_ask(question, campaigns),
        prior_performance=[_campaign_performance(c) for c in campaigns],
        measurement_cautions=[_measurement_caution(db, h) for h in hypotheses[:2]],
        client_memory=[_client_memory_item(c) for c in client_memories[:5]],
        portfolio_evidence=_portfolio_evidence_payload(pattern),
    )

    return {
        "evidence_brief": evidence_brief,
        "supporting_memory_ids": supporting_memory_ids,
        "hypothesis_claims": hypotheses,
        "pattern": pattern,
        "decision_evidence": decision_evidence,
        "structured_context": {
            "client_name": client.name if client else client_id,
            "partner_name": partner.name if partner else partner_id,
            "primary_goal": (primary_goal or "").replace("_", " ") or None,
            "strategy": (strategy or "").replace("_", " ") or None,
            "has_attribution_hypothesis": bool(hypotheses),
            "has_hybrid_pattern": pattern is not None,
            **campaign_context,
        },
    }


def build_campaign_review_context(db: Session, *, campaign_id: str) -> dict | None:
    """Deterministic evidence assembly for Campaign Review (spec Phase 2).
    Returns None if the campaign doesn't exist - caller maps that to 404.

    Mirrors build_recommendation_context's shape: everything numeric or
    comparative is computed here in Python before the LLM ever sees it; the
    LLM only ever receives evidence.model_dump() (see
    app/memory/manager.py::run_campaign_review), never raw DB rows."""
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        return None
    partner = db.get(Partner, campaign.partner_id)
    client = db.get(Client, campaign.client_id)
    partner_name = partner.name if partner else campaign.partner_id

    campaigns_sorted = sorted(
        db.query(Campaign).filter(Campaign.partner_id == campaign.partner_id, Campaign.client_id == campaign.client_id).all(),
        key=lambda c: c.month,
    )
    perf = _campaign_performance(campaign)
    comparison = _prior_campaign_comparison(campaigns_sorted, campaign)

    # Relevant active CLIENT memory: the account's own strategy/goals/
    # tradeoffs (subject_type == "client" specifically) - kept a distinct,
    # non-overlapping bucket from partner_memory below, scored/capped so
    # this is "relevant context," not a full memory dump.
    terms = query_terms(f"{partner_name} campaign review", partner_name, client.name if client else "")
    entity_ids = {campaign.client_id, campaign.partner_id}
    client_claims = [c for c in active_client_memories(db, campaign.client_id) if c.subject_type == "client" and c.claim_class != "hypothesis"]
    scored_client = sorted(client_claims, key=lambda c: score_claim(c, terms=terms, entity_ids=entity_ids, client_id=campaign.client_id), reverse=True)
    client_memory = [_client_memory_item(c) for c in scored_client[:5]]

    # Relevant PARTNER memory: governed claims whose subject is this
    # creator/publisher (relationship_status, negotiation_history, and any
    # already-approved partner_performance_pattern from a prior review).
    partner_claims = active_partner_memories(db, campaign.partner_id)
    partner_memory = [_partner_memory_item(c) for c in partner_claims[:5]]

    # Measurement cautions scoped to THIS campaign specifically - status
    # in (needs_review, active) so a not-yet-resolved hypothesis still
    # surfaces (same needs_review exception build_recommendation_context
    # makes), never silently dropped and never upgraded to a fact here.
    caution_claims = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.subject_type == "campaign", MemoryClaim.subject_id == campaign_id)
        .filter(MemoryClaim.claim_class == "hypothesis")
        .filter(MemoryClaim.status.in_(["needs_review", "active"]))
        .all()
    )
    measurement_cautions = [_measurement_caution(db, c) for c in caution_claims]

    # Creator/publisher-record metadata (Phase 1's descriptive `note` field,
    # e.g. Campfire Kate's audience-fit note) - observed source data the
    # review may interpret in prose, but this is NOT governed memory and
    # must never be silently promoted into a MemoryClaim (spec Phase 2).
    partner_note = (partner.meta or {}).get("note") if partner else None

    evidence = schemas.CampaignReviewEvidence(
        campaign_id=campaign.id, partner_id=campaign.partner_id, partner_name=partner_name,
        month=campaign.month, month_label=format_month(campaign.month), synthetic=campaign.synthetic,
        fee=perf.fee, attributed_revenue=perf.attributed_revenue, attributed_roas=perf.attributed_roas,
        link_clicks=perf.link_clicks, code_redemptions=perf.code_redemptions,
        partner_note=partner_note, client_memory=client_memory, partner_memory=partner_memory,
        measurement_cautions=measurement_cautions, prior_campaign_comparison=comparison,
    )
    return {
        "client_id": campaign.client_id,
        "partner_id": campaign.partner_id,
        "campaign_label": f"{partner_name}, {format_month(campaign.month)}",
        "evidence": evidence,
    }


def _team_experience(db: Session, partner_id: str) -> list[schemas.TeamExperienceItem]:
    """Team members with a WORKED_WITH edge to this partner - a recorded
    graph fact only. Deliberately does NOT look at negotiation_history
    content here (spec Phase 3: "distinguish WORKED_WITH from documented
    negotiation history" - the two must stay separate evidence fields, not
    get merged into one "this person is the expert" claim)."""
    edges = (
        db.query(MemoryEdge)
        .filter(MemoryEdge.from_type == "team_member", MemoryEdge.to_type == "partner", MemoryEdge.to_id == partner_id, MemoryEdge.relationship == "WORKED_WITH")
        .all()
    )
    items = []
    for e in edges:
        tm = db.get(TeamMember, e.from_id)
        if tm:
            items.append(schemas.TeamExperienceItem(team_member_id=tm.id, name=tm.name, role=tm.role, worked_with=True))
    return items


def _campaign_performance_summary(campaigns_sorted: list[Campaign]) -> schemas.CampaignPerformanceSummary:
    """All computed in Python - see module docstring; the LLM never
    calculates a metric (spec Phase 3: "Do not ask the LLM to calculate
    them")."""
    if not campaigns_sorted:
        return schemas.CampaignPerformanceSummary(campaign_count=0)

    def roas(c: Campaign) -> float | None:
        return round(c.attributed_revenue / c.flat_fee, 2) if c.flat_fee and c.attributed_revenue is not None else None

    roas_values = [r for r in (roas(c) for c in campaigns_sorted) if r is not None]
    average_roas = round(sum(roas_values) / len(roas_values), 2) if roas_values else None

    engagement_rates = [
        c.engagements / c.impressions for c in campaigns_sorted
        if c.impressions and c.engagements is not None
    ]
    average_engagement_rate = round(sum(engagement_rates) / len(engagement_rates), 4) if engagement_rates else None

    most_recent = campaigns_sorted[-1]
    first = campaigns_sorted[0]
    fee_change_pct = (
        round((most_recent.flat_fee - first.flat_fee) / first.flat_fee * 100, 2)
        if most_recent.flat_fee is not None and first.flat_fee else None
    )

    revenue_trend = None
    if len(campaigns_sorted) >= 2 and first.attributed_revenue is not None and most_recent.attributed_revenue is not None:
        if most_recent.attributed_revenue > first.attributed_revenue:
            revenue_trend = "rising"
        elif most_recent.attributed_revenue < first.attributed_revenue:
            revenue_trend = "falling"
        else:
            revenue_trend = "flat"

    return schemas.CampaignPerformanceSummary(
        campaign_count=len(campaigns_sorted),
        most_recent_month_label=format_month(most_recent.month),
        most_recent_fee=most_recent.flat_fee,
        most_recent_roas=roas(most_recent),
        average_roas=average_roas,
        average_engagement_rate=average_engagement_rate,
        fee_change_pct=fee_change_pct,
        revenue_trend=revenue_trend,
    )


def build_partner_brief_context(db: Session, *, partner_id: str, client_id: str) -> dict | None:
    """Deterministic evidence assembly for Partner Brief (spec Phase 3).
    Returns None if the partner doesn't exist - caller maps that to 404.

    Same "the LLM only ever sees evidence.model_dump(), never raw DB rows"
    contract as build_recommendation_context / build_campaign_review_context."""
    partner = db.get(Partner, partner_id)
    if partner is None:
        return None
    client = db.get(Client, client_id)

    campaigns_sorted = sorted(
        db.query(Campaign).filter(Campaign.partner_id == partner_id, Campaign.client_id == client_id).all(),
        key=lambda c: c.month,
    )
    campaign_items = [_campaign_performance(c) for c in campaigns_sorted]
    performance_stats = _campaign_performance_summary(campaigns_sorted)

    # Relationship history: active governed claims about this partner only
    # (spec: "Normal Partner Brief should use current/relevant memory. Do
    # not use superseded client strategy as though it is current.") -
    # active_partner_memories is already active-only by construction.
    relationship_history = [_partner_memory_item(c) for c in active_partner_memories(db, partner_id)]

    team_experience = _team_experience(db, partner_id)

    # Measurement cautions across ALL of this partner's campaigns, not just
    # one - a partner brief is preparation for the whole relationship.
    campaign_ids = [c.id for c in campaigns_sorted]
    if campaign_ids:
        caution_claims = (
            db.query(MemoryClaim)
            .filter(MemoryClaim.subject_type == "campaign", MemoryClaim.subject_id.in_(campaign_ids))
            .filter(MemoryClaim.claim_class == "hypothesis")
            .filter(MemoryClaim.status.in_(["needs_review", "active"]))
            .all()
        )
    else:
        caution_claims = []
    measurement_cautions = [_measurement_caution(db, c) for c in caution_claims]

    # Current client context: active, subject_type == "client" claims only -
    # the same rule build_campaign_review_context uses, so a superseded
    # strategy (status != "active") never appears here as though current.
    client_context = [
        _client_memory_item(c) for c in active_client_memories(db, client_id)
        if c.subject_type == "client" and c.claim_class != "hypothesis"
    ]

    # Prior durable decisions for this exact partner+client, chronological.
    decisions = sorted(
        db.query(Decision).filter(Decision.partner_id == partner_id, Decision.client_id == client_id).all(),
        key=lambda d: d.created_at,
    )
    decision_items = [
        schemas.DecisionSummaryItem(
            decision_id=d.id, summary=d.summary, terms=d.terms, status=d.status,
            motivated_by_claim_ids=d.motivated_by_claim_ids, created_at=d.created_at.isoformat(),
        )
        for d in decisions
    ]
    outcome_items = []
    for d in decisions:
        for o in db.query(Outcome).filter(Outcome.decision_id == d.id).order_by(Outcome.created_at).all():
            outcome_items.append(schemas.OutcomeSummaryItem(
                outcome_id=o.id, decision_id=d.id, metrics=o.metrics, outcome_label=o.outcome_label,
                is_simulated=o.is_simulated, created_at=o.created_at.isoformat(),
            ))

    meta = partner.meta or {}
    identity = schemas.PartnerIdentity(
        partner_id=partner.id, name=partner.name, kind=partner.kind, synthetic=partner.synthetic,
        platform=partner.platform, follower_tier=meta.get("follower_tier"),
        record_relationship_status=meta.get("relationship_status"), partner_note=meta.get("note"),
    )

    evidence = schemas.PartnerBriefEvidence(
        partner=identity, relationship_history=relationship_history, team_experience=team_experience,
        campaigns=campaign_items, performance_stats=performance_stats, measurement_cautions=measurement_cautions,
        client_context=client_context, prior_decisions=decision_items, outcomes=outcome_items,
    )
    return {
        "client_id": client_id,
        "partner_id": partner_id,
        "partner_label": partner.name,
        "evidence": evidence,
    }


# ---- memory history / "What Changed?" (Phase 4) ----
#
# A deliberately separate retrieval mode from everything above. Every other
# function in this module either calls active_client_memories /
# active_partner_memories directly or applies the same status == "active"
# filter inline - none of that changes here. The functions below are the
# only ones in this module allowed to return superseded/needs_review claims,
# and only because a caller explicitly asked for history.


def _comparable_created_at(c: MemoryClaim) -> datetime:
    """SQLite's DateTime(timezone=True) column doesn't actually preserve
    tzinfo across a real round-trip - a freshly-constructed-this-session
    MemoryClaim has an aware created_at (models.py's _now() default), but
    one reloaded from SQLite in a fresh session comes back naive. Mixing
    the two in a sort comparison raises TypeError. Normalize to aware UTC
    (assuming naive == UTC, matching what _now() always writes) so the
    chronological sort in build_memory_history is safe regardless of which
    claims in a chain were created in-session vs. reloaded."""
    dt = c.created_at
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _resolve_subject_name(db: Session, subject_type: str, subject_id: str) -> str:
    if subject_type == "client":
        obj = db.get(Client, subject_id)
        return obj.name if obj else subject_id
    if subject_type in ("creator", "publisher"):
        obj = db.get(Partner, subject_id)
        return obj.name if obj else subject_id
    return subject_id


def _history_entry(c: MemoryClaim) -> schemas.MemoryHistoryEntry:
    return schemas.MemoryHistoryEntry(
        claim_id=c.id, subject_type=c.subject_type, subject_id=c.subject_id, predicate=c.predicate,
        value=c.value, claim_class=c.claim_class, status=c.status, valid_from=c.valid_from, valid_to=c.valid_to,
        confidence=c.confidence, authority_score=c.authority_score, source=c.source or {},
        supersedes=c.supersedes or [], superseded_by=c.superseded_by, synthetic=c.synthetic,
        created_at=c.created_at.isoformat(),
    )


def build_memory_history(
    db: Session, *, subject_type: str, subject_id: str, predicate: str, client_id: str | None = None,
) -> dict | None:
    """The ONLY query in this module that intentionally retrieves
    active + superseded + needs_review claims together (spec Phase 4
    Sec.2). Deliberately excludes 'rejected' (spec: "Do not automatically
    include rejected unless a future workflow explicitly asks about
    rejected proposals" - and in practice no MemoryClaim ever reaches that
    status today; MemoryCandidate rejections never become claims at all).

    Returns None only when NO claim at all exists for this (subject,
    predicate) - the true "nothing on file" case. A single-entry result
    (one governed belief, never superseded) is a normal, valid return -
    callers must render that as "no change yet," not an error."""
    q = db.query(MemoryClaim).filter(
        MemoryClaim.subject_type == subject_type,
        MemoryClaim.subject_id == subject_id,
        MemoryClaim.predicate == predicate,
        MemoryClaim.status != "rejected",
    )
    if client_id is not None:
        q = q.filter(MemoryClaim.client_id == client_id)
    claims = q.all()
    if not claims:
        return None

    # Deterministic chronological order (spec Sec.5): valid_from ASC, then
    # created_at ASC as the tiebreaker - never left to the LLM, and never
    # inferred solely from the supersedes/superseded_by pointers (which are
    # additional lifecycle info, not the sort key). A null valid_from
    # sorts first rather than raising (Python 3 can't compare None to str).
    ordered = sorted(claims, key=lambda c: (c.valid_from or "", _comparable_created_at(c)))

    current = next((c for c in ordered if c.status == "active"), None)
    subject_name = _resolve_subject_name(db, subject_type, subject_id)

    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "subject_name": subject_name,
        "predicate": predicate,
        "current_claim_id": current.id if current else None,
        "entries": [_history_entry(c) for c in ordered],
    }


# Deterministic keyword -> canonical-predicate map for the bounded chat
# intent (spec Sec.9). Intentionally small and explicit, like
# predicates.py's alias table - a phrase either clearly names one of these
# concepts or it doesn't; no fuzzy/semantic coercion that could silently
# pick the wrong predicate.
HISTORICAL_PREDICATE_KEYWORDS: dict[str, list[str]] = {
    "partnership_strategy": ["strategy", "partnership direction", "channel strategy", "coupon"],
    "primary_growth_objective": ["priorit", "growth objective", "growth goal", "primary objective"],
    "accepts_tradeoff": ["tradeoff", "trade-off"],
    "partner_performance_pattern": ["performance pattern", "performance"],
}


def resolve_historical_predicate(text: str) -> str | None:
    lowered = text.lower()
    for predicate, keywords in HISTORICAL_PREDICATE_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return predicate
    return None


def find_changed_predicates(db: Session, *, subject_type: str, subject_id: str, client_id: str | None = None) -> list[dict]:
    """Deterministically finds every predicate for this subject that has
    genuine version history - more than one claim, or any claim with
    status in (superseded, expired) - for the broader "what changed?"
    summary (spec Sec.10). Never invents a "change" from two unrelated
    claims; only real supersession chains for the SAME predicate count."""
    q = db.query(MemoryClaim).filter(
        MemoryClaim.subject_type == subject_type,
        MemoryClaim.subject_id == subject_id,
        MemoryClaim.status != "rejected",
    )
    if client_id is not None:
        q = q.filter(MemoryClaim.client_id == client_id)
    claims = q.all()

    by_predicate: dict[str, list[MemoryClaim]] = {}
    for c in claims:
        by_predicate.setdefault(c.predicate, []).append(c)

    changed = []
    for predicate, group in by_predicate.items():
        has_history = len(group) > 1 or any(c.status in ("superseded", "expired") for c in group)
        if not has_history:
            continue
        ordered = sorted(group, key=lambda c: (c.valid_from or "", _comparable_created_at(c)))
        oldest, newest_active = ordered[0], next((c for c in ordered if c.status == "active"), ordered[-1])
        if oldest.id == newest_active.id:
            continue  # a single claim that happens to be e.g. needs_review isn't a "change"
        changed.append({"predicate": predicate, "old_value": oldest.value, "new_value": newest_active.value})
    return changed


# ---- scenario comparison (Phase 5) ----

SCENARIO_CLIENT_PREDICATES = ("partnership_strategy", "primary_growth_objective", "accepts_tradeoff")


def build_scenario_comparison_context(db: Session, *, partner_id: str, client_id: str, current_ask: float) -> dict | None:
    """Deterministic evidence assembly for Scenario Comparison (spec Phase
    5). Returns None if the partner doesn't exist. Every RenewalScenario
    and its ScenarioAssessment is constructed here via
    app.memory.scenario_rules BEFORE the LLM is ever called - the LLM only
    narrates the result (see app.memory.manager.run_scenario_comparison)."""
    partner = db.get(Partner, partner_id)
    if partner is None:
        return None
    client = db.get(Client, client_id)

    campaigns_sorted = sorted(
        db.query(Campaign).filter(Campaign.partner_id == partner_id, Campaign.client_id == client_id).all(),
        key=lambda c: c.month,
    )
    campaign_items = [_campaign_performance(c) for c in campaigns_sorted]
    performance_stats = _campaign_performance_summary(campaigns_sorted)
    latest_fee = campaigns_sorted[-1].flat_fee if campaigns_sorted else None

    # Current-active-only client context, scoped to exactly the three
    # planning-relevant predicates (spec Sec.5) - narrower than Partner
    # Brief's client_context, and never includes a superseded value (same
    # current-state rule every other workflow uses; spec Sec.22 explicitly
    # requires Scenario Comparison not blur this with Historical Retrieval).
    client_context = [
        _client_memory_item(c) for c in active_client_memories(db, client_id)
        if c.subject_type == "client" and c.predicate in SCENARIO_CLIENT_PREDICATES
    ]
    growth_objective_value = next((c.value for c in client_context if c.predicate == "primary_growth_objective"), None)

    partner_memory = [_partner_memory_item(c) for c in active_partner_memories(db, partner_id)]

    campaign_ids = [c.id for c in campaigns_sorted]
    if campaign_ids:
        caution_claims = (
            db.query(MemoryClaim)
            .filter(MemoryClaim.subject_type == "campaign", MemoryClaim.subject_id.in_(campaign_ids))
            .filter(MemoryClaim.claim_class == "hypothesis")
            .filter(MemoryClaim.status.in_(["needs_review", "active"]))
            .all()
        )
    else:
        caution_claims = []
    measurement_cautions = [_measurement_caution(db, c) for c in caution_claims]
    has_caution = len(measurement_cautions) > 0

    decisions = sorted(
        db.query(Decision).filter(Decision.partner_id == partner_id, Decision.client_id == client_id).all(),
        key=lambda d: d.created_at,
    )
    decision_items = [
        schemas.DecisionSummaryItem(
            decision_id=d.id, summary=d.summary, terms=d.terms, status=d.status,
            motivated_by_claim_ids=d.motivated_by_claim_ids, created_at=d.created_at.isoformat(),
        )
        for d in decisions
    ]
    outcome_items = []
    for d in decisions:
        for o in db.query(Outcome).filter(Outcome.decision_id == d.id).order_by(Outcome.created_at).all():
            outcome_items.append(schemas.OutcomeSummaryItem(
                outcome_id=o.id, decision_id=d.id, metrics=o.metrics, outcome_label=o.outcome_label,
                is_simulated=o.is_simulated, created_at=o.created_at.isoformat(),
            ))

    raw_scenarios = build_scenarios(latest_fee=latest_fee, current_ask=current_ask)
    scenarios = [
        schemas.ScenarioWithAssessment(
            scenario=schemas.RenewalScenario(**s),
            assessment=schemas.ScenarioAssessment(**assess_scenario(
                s, latest_fee=latest_fee, has_caution=has_caution, growth_objective_value=growth_objective_value,
            )),
        )
        for s in raw_scenarios
    ]

    meta = partner.meta or {}
    identity = schemas.PartnerIdentity(
        partner_id=partner.id, name=partner.name, kind=partner.kind, synthetic=partner.synthetic,
        platform=partner.platform, follower_tier=meta.get("follower_tier"),
        record_relationship_status=meta.get("relationship_status"), partner_note=meta.get("note"),
    )

    evidence = schemas.ScenarioComparisonEvidence(
        partner=identity, campaigns=campaign_items, performance_stats=performance_stats,
        client_context=client_context, partner_memory=partner_memory, measurement_cautions=measurement_cautions,
        prior_decisions=decision_items, outcomes=outcome_items, current_ask=current_ask, scenarios=scenarios,
    )
    return {"client_id": client_id, "partner_id": partner_id, "evidence": evidence}


# ---- account planning (Phase 6) ----


def partners_with_campaign_history(db: Session, client_id: str) -> list[Partner]:
    """Every partner this client has actually run a campaign with - the same
    join chat.py's `_matched_partner` uses, generalized to "all of them"
    rather than "the one this message names." This is the default planning
    scope (spec Sec.10: "Initial scope: Northwind creator planning... the
    seeded creator partners") when the caller doesn't name specific ones."""
    return (
        db.query(Partner)
        .join(Campaign, Campaign.partner_id == Partner.id)
        .filter(Campaign.client_id == client_id)
        .distinct()
        .all()
    )


def open_planned_actions(db: Session, client_id: str) -> list[PlannedAction]:
    """Every currently-open (approved or in_progress) PlannedAction for this
    client, across all of its plans - used both to steer the planner away
    from casual duplicates (spec Sec.9) and to enforce the duplicate guard
    deterministically at persistence time (spec Sec.31)."""
    return (
        db.query(PlannedAction)
        .filter(PlannedAction.client_id == client_id, PlannedAction.status.in_(["approved", "in_progress"]))
        .all()
    )


def build_planning_context(
    db: Session, *, client_id: str, partner_ids: list[str] | None = None,
    planning_period: str | None = None, scenario_inputs: list["schemas.ScenarioComparisonRef"] | None = None,
) -> schemas.PlanningContext | None:
    """Deterministic evidence assembly for account planning (spec Phase 6).
    Returns None if the client doesn't exist. Every field here is either
    retrieved as-is or computed in Python, exactly like every other
    *Context/*Evidence builder in this module - the LLM (app.agents.
    plan_agent) only ever sees this object's .model_dump(), and only ever
    proposes plan_name/objective/proposed_actions[].summary+rationale over
    it; every id it returns is intersected against this object's own ids
    afterward (app.memory.planning_rules), never trusted directly."""
    client = db.get(Client, client_id)
    if client is None:
        return None

    # Current strategy: active-only, scoped to the same 3 predicates
    # Scenario Comparison uses - never a superseded value (spec Sec.32).
    current_strategy = [
        _client_memory_item(c) for c in active_client_memories(db, client_id)
        if c.subject_type == "client" and c.predicate in SCENARIO_CLIENT_PREDICATES
    ]

    partners = partners_with_campaign_history(db, client_id) if partner_ids is None else [
        p for p in (db.get(Partner, pid) for pid in partner_ids) if p is not None
    ]
    scenario_by_partner = {s.partner_id: s for s in (scenario_inputs or [])}

    partner_summaries: list[schemas.PlanningPartnerSummary] = []
    all_decision_rows: list[Decision] = []
    for partner in partners:
        campaigns_sorted = sorted(
            db.query(Campaign).filter(Campaign.partner_id == partner.id, Campaign.client_id == client_id).all(),
            key=lambda c: c.month,
        )
        campaign_items = [_campaign_performance(c) for c in campaigns_sorted]
        performance_stats = _campaign_performance_summary(campaigns_sorted)

        campaign_ids = [c.id for c in campaigns_sorted]
        if campaign_ids:
            caution_claims = (
                db.query(MemoryClaim)
                .filter(MemoryClaim.subject_type == "campaign", MemoryClaim.subject_id.in_(campaign_ids))
                .filter(MemoryClaim.claim_class == "hypothesis")
                .filter(MemoryClaim.status.in_(["needs_review", "active"]))
                .all()
            )
        else:
            caution_claims = []
        measurement_cautions = [_measurement_caution(db, c) for c in caution_claims]
        partner_memory = [_partner_memory_item(c) for c in active_partner_memories(db, partner.id)]

        meta = partner.meta or {}
        identity = schemas.PartnerIdentity(
            partner_id=partner.id, name=partner.name, kind=partner.kind, synthetic=partner.synthetic,
            platform=partner.platform, follower_tier=meta.get("follower_tier"),
            record_relationship_status=meta.get("relationship_status"), partner_note=meta.get("note"),
        )

        partner_summaries.append(schemas.PlanningPartnerSummary(
            partner=identity, campaigns=campaign_items, performance_stats=performance_stats,
            measurement_cautions=measurement_cautions, partner_memory=partner_memory,
            scenario=scenario_by_partner.get(partner.id),
        ))

        all_decision_rows.extend(
            db.query(Decision).filter(Decision.partner_id == partner.id, Decision.client_id == client_id).all()
        )

    decisions_sorted = sorted(all_decision_rows, key=lambda d: d.created_at)
    existing_decisions = [
        schemas.DecisionSummaryItem(
            decision_id=d.id, summary=d.summary, terms=d.terms, status=d.status,
            motivated_by_claim_ids=d.motivated_by_claim_ids, created_at=d.created_at.isoformat(),
        )
        for d in decisions_sorted
    ]

    existing_open_actions = [
        schemas.PlanningExistingActionRef(id=a.id, partner_id=a.partner_id, action_type=a.action_type, summary=a.summary, status=a.status)
        for a in open_planned_actions(db, client_id)
    ]

    return schemas.PlanningContext(
        client=schemas.PlanningClientContext(client_id=client_id, client_name=client.name, current_strategy=current_strategy),
        planning_period=planning_period,
        partners=partner_summaries,
        existing_decisions=existing_decisions,
        existing_open_actions=existing_open_actions,
    )
