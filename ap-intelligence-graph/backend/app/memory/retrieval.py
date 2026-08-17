"""Filtered + scored retrieval (spec Sec.15). Produces the compact evidence
brief handed to the recommendation agent - never the raw graph - and the
structured DecisionEvidence shown to the user (spec Step 5).

Both are built from the same retrieved rows in one place, so the LLM's
evidence_brief and the UI's decision_evidence never diverge, and neither
router duplicates this construction.
"""

from sqlalchemy.orm import Session

from app import schemas
from app.formatting import extract_dollar_amount, format_month
from app.memory.scoring import query_terms, score_claim
from app.models import Campaign, Client, MemoryClaim, Partner, PortfolioPattern


def active_client_memories(db: Session, client_id: str) -> list[MemoryClaim]:
    """Normal retrieval: active + currently valid only (spec Sec.8)."""
    return (
        db.query(MemoryClaim)
        .filter(MemoryClaim.client_id == client_id, MemoryClaim.status == "active")
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
