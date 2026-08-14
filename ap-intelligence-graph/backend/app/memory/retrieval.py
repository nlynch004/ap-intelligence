"""Filtered + scored retrieval (spec Sec.15). Produces the compact evidence
brief handed to the recommendation agent - never the raw graph.
"""

from sqlalchemy.orm import Session

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

    client_memories = [c for c in scored if c.client_id == client_id and c.claim_class != "hypothesis" and c.status == "active"]
    hypotheses = [
        c for c in scored
        if c.claim_class == "hypothesis" and c.subject_id in {
            camp.id for camp in db.query(Campaign).filter(Campaign.partner_id == partner_id).all()
        }
    ]
    portfolio_memories = [c for c in scored if c.client_id is None and c.status == "active"]

    pattern = _select_hybrid_pattern(db)

    campaigns = db.query(Campaign).filter(Campaign.partner_id == partner_id, Campaign.client_id == client_id).all()

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

    return {
        "evidence_brief": evidence_brief,
        "supporting_memory_ids": supporting_memory_ids,
        "hypothesis_claims": hypotheses,
        "pattern": pattern,
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
