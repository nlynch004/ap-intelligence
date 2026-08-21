from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import schemas
from app.formatting import extract_dollar_amount, format_month
from app.memory.scenario_rules import assess_scenario, build_scenarios
from app.memory.scoring import query_terms, score_claim
from app.models import Campaign, Client, Decision, MemoryClaim, MemoryEdge, Outcome, Partner, PlannedAction, PortfolioPattern, TeamMember


def active_client_memories(db: Session, client_id: str) -> list[MemoryClaim]:
    return (
        db.query(MemoryClaim)
        .filter(MemoryClaim.client_id == client_id, MemoryClaim.status == "active")
        .order_by(MemoryClaim.predicate)
        .all()
    )


def active_partner_memories(db: Session, partner_id: str) -> list[MemoryClaim]:
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
    prior_fee = campaigns[-1].flat_fee if campaigns else None
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

    client_memories = [c for c in scored if c.client_id == client_id and c.claim_class != "hypothesis" and c.status == "active"]
    hypotheses = [
        c for c in scored
        if c.claim_class == "hypothesis" and c.subject_id in {
            camp.id for camp in db.query(Campaign).filter(Campaign.partner_id == partner_id).all()
        }
    ]

    pattern = _select_hybrid_pattern(db)

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

    terms = query_terms(f"{partner_name} campaign review", partner_name, client.name if client else "")
    entity_ids = {campaign.client_id, campaign.partner_id}
    client_claims = [c for c in active_client_memories(db, campaign.client_id) if c.subject_type == "client" and c.claim_class != "hypothesis"]
    scored_client = sorted(client_claims, key=lambda c: score_claim(c, terms=terms, entity_ids=entity_ids, client_id=campaign.client_id), reverse=True)
    client_memory = [_client_memory_item(c) for c in scored_client[:5]]

    partner_claims = active_partner_memories(db, campaign.partner_id)
    partner_memory = [_partner_memory_item(c) for c in partner_claims[:5]]

    caution_claims = (
        db.query(MemoryClaim)
        .filter(MemoryClaim.subject_type == "campaign", MemoryClaim.subject_id == campaign_id)
        .filter(MemoryClaim.claim_class == "hypothesis")
        .filter(MemoryClaim.status.in_(["needs_review", "active"]))
        .all()
    )
    measurement_cautions = [_measurement_caution(db, c) for c in caution_claims]

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

    relationship_history = [_partner_memory_item(c) for c in active_partner_memories(db, partner_id)]

    team_experience = _team_experience(db, partner_id)

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

    client_context = [
        _client_memory_item(c) for c in active_client_memories(db, client_id)
        if c.subject_type == "client" and c.claim_class != "hypothesis"
    ]

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


def _comparable_created_at(c: MemoryClaim) -> datetime:
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
            continue
        changed.append({"predicate": predicate, "old_value": oldest.value, "new_value": newest_active.value})
    return changed


SCENARIO_CLIENT_PREDICATES = ("partnership_strategy", "primary_growth_objective", "accepts_tradeoff")


def build_scenario_comparison_context(db: Session, *, partner_id: str, client_id: str, current_ask: float) -> dict | None:
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


def partners_with_campaign_history(db: Session, client_id: str) -> list[Partner]:
    return (
        db.query(Partner)
        .join(Campaign, Campaign.partner_id == Partner.id)
        .filter(Campaign.client_id == client_id)
        .distinct()
        .all()
    )


def open_planned_actions(db: Session, client_id: str) -> list[PlannedAction]:
    return (
        db.query(PlannedAction)
        .filter(PlannedAction.client_id == client_id, PlannedAction.status.in_(["approved", "in_progress"]))
        .all()
    )


def build_planning_context(
    db: Session, *, client_id: str, partner_ids: list[str] | None = None,
    planning_period: str | None = None, scenario_inputs: list["schemas.ScenarioComparisonRef"] | None = None,
) -> schemas.PlanningContext | None:
    client = db.get(Client, client_id)
    if client is None:
        return None

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
