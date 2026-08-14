"""Idempotent seed loader.

Loads the two data fixtures (`data/northwind_seed.json` - real case-study
data, `data/synthetic_portfolio.json` - fictional cross-client portfolio)
into SQLite. Safe to call on every startup: if `clients` already has rows,
it's a no-op unless `reset=True`.

The attribution hypothesis (spec Sec.26) is *not* hardcoded here - it is
derived deterministically from the campaign numbers by `_derive_attribution_hypothesis`,
matching spec Sec.26's "can either be seeded or generated deterministically."
"""

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.models import (
    ActivityEvent,
    Campaign,
    Client,
    Decision,
    MemoryClaim,
    MemoryEdge,
    Partner,
    PortfolioPattern,
    TeamMember,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REDEMPTION_LEAKAGE_RATIO = 1.5  # redemptions > clicks * ratio triggers the hypothesis


def _load_json(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text())


def _derive_attribution_hypothesis(campaign: dict) -> dict | None:
    """Deterministic rule: if code redemptions materially exceed tracked link
    clicks, flag a promo-code-leakage hypothesis. Confidence scales mildly
    with how extreme the ratio is, capped well below 'verified' territory -
    this must never look like a fact (spec Sec.5, Sec.13)."""
    clicks = campaign.get("link_clicks") or 0
    redemptions = campaign.get("code_redemptions") or 0
    if clicks <= 0 or redemptions <= clicks * REDEMPTION_LEAKAGE_RATIO:
        return None
    ratio = redemptions / clicks
    confidence = round(min(0.5 + 0.023 * ratio, 0.7), 2)
    return {
        "id": f"mem_{campaign['id']}_attribution_risk",
        "type": "hypothesis",
        "subject_type": "campaign",
        "subject_id": campaign["id"],
        "predicate": "attribution_integrity_risk",
        "value": "possible_promo_code_leakage",
        "claim_class": "hypothesis",
        "confidence": confidence,
        "authority_score": 0.4,
        "source": {
            "type": "agent_inference",
            "source_id": "deterministic_rule:redemption_click_ratio",
            "detail": f"{redemptions} code redemptions vs {clicks} tracked link clicks (ratio {ratio:.1f}x)",
        },
        "valid_from": f"{campaign['month']}-01",
        "status": "needs_review",
    }


def _claim_defaults(raw: dict, *, client_id: str | None, synthetic: bool) -> dict:
    return dict(
        id=raw["id"],
        type=raw["type"],
        subject_type=raw["subject_type"],
        subject_id=raw["subject_id"],
        predicate=raw["predicate"],
        value=raw["value"],
        scope=raw.get("scope") or ({"client_id": client_id} if client_id else {"portfolio": "privacy_safe"}),
        client_id=client_id,
        claim_class=raw["claim_class"],
        confidence=raw["confidence"],
        authority_score=raw["authority_score"],
        source=raw["source"],
        valid_from=raw["valid_from"],
        valid_to=raw.get("valid_to"),
        status=raw.get("status", "active"),
        supersedes=raw.get("supersedes", []),
        synthetic=synthetic,
    )


def _already_seeded(db: Session) -> bool:
    return db.query(Client).count() > 0


def seed(db: Session, reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    if not reset and _already_seeded(db):
        return

    nw = _load_json("northwind_seed.json")
    pf = _load_json("synthetic_portfolio.json")

    # --- Northwind (real case-study data) ---
    db.add(Client(id=nw["client"]["id"], name=nw["client"]["name"], industry=nw["client"].get("industry"), synthetic=False))

    for tm in nw["team_members"]:
        db.add(TeamMember(id=tm["id"], name=tm["name"], role=tm["role"], primary_client_id=tm.get("manages_client_id"), synthetic=False))

    for c in nw["creators"]:
        db.add(Partner(id=c["id"], name=c["name"], kind="creator", platform=c.get("platform"), meta=c, synthetic=False))
    for p in nw.get("publishers", []):
        db.add(Partner(id=p["id"], name=p["name"], kind="publisher", platform=p.get("network"), meta=p, synthetic=False))

    for camp in nw["campaigns"]:
        db.add(Campaign(
            id=camp["id"], client_id=nw["client"]["id"], partner_id=camp["creator_id"], month=camp["month"],
            flat_fee=camp.get("flat_fee"), impressions=camp.get("impressions"), engagements=camp.get("engagements"),
            link_clicks=camp.get("link_clicks"), code_redemptions=camp.get("code_redemptions"),
            attributed_revenue=camp.get("attributed_revenue"), meta={k: v for k, v in camp.items() if k not in {
                "id", "creator_id", "month", "flat_fee", "impressions", "engagements", "link_clicks",
                "code_redemptions", "attributed_revenue",
            }},
        ))

    for raw_claim in nw["seed_memories"]:
        db.add(MemoryClaim(**_claim_defaults(raw_claim, client_id=nw["client"]["id"], synthetic=False)))

    for camp in nw["campaigns"]:
        hyp = _derive_attribution_hypothesis(camp)
        if hyp:
            db.add(MemoryClaim(**_claim_defaults(hyp, client_id=nw["client"]["id"], synthetic=False)))

    db.flush()

    # --- graph edges for Northwind's real entities ---
    client_id = nw["client"]["id"]
    db.add(MemoryEdge(from_type="team_member", from_id="jessica_moreno", to_type="client", to_id=client_id, relationship="MANAGES"))
    db.add(MemoryEdge(from_type="team_member", from_id="jessica_moreno", to_type="partner", to_id="summit_sisters", relationship="WORKED_WITH"))
    db.add(MemoryEdge(from_type="client", from_id=client_id, to_type="memory_claim", to_id="mem_northwind_strategy_coupon", relationship="HAS_STRATEGY", client_id=client_id))
    db.add(MemoryEdge(from_type="client", from_id=client_id, to_type="memory_claim", to_id="mem_summit_relationship", relationship="HAS_RELATIONSHIP", client_id=client_id))
    for camp in nw["campaigns"]:
        db.add(MemoryEdge(from_type="client", from_id=client_id, to_type="campaign", to_id=camp["id"], relationship="HAS_CAMPAIGN", client_id=client_id))
        db.add(MemoryEdge(from_type="campaign", from_id=camp["id"], to_type="partner", to_id=camp["creator_id"], relationship="APPLIES_TO", client_id=client_id))
        hyp_id = f"mem_{camp['id']}_attribution_risk"
        db.add(MemoryEdge(from_type="campaign", from_id=camp["id"], to_type="memory_claim", to_id=hyp_id, relationship="HAS_RISK", client_id=client_id))

    # --- synthetic portfolio layer ---
    seen_team_ids = {tm.id for tm in db.query(TeamMember).all()}
    for cl in pf["clients"]:
        db.add(Client(id=cl["id"], name=cl["name"], industry=cl.get("industry"), synthetic=True))
    for cr in pf["creators"]:
        db.add(Partner(id=cr["id"], name=cr["name"], kind="creator", platform=cr.get("platform"), meta=cr, synthetic=True))
    for tm in pf["team_members"]:
        if tm["id"] in seen_team_ids:
            continue
        db.add(TeamMember(id=tm["id"], name=tm["name"], role=tm["role"], synthetic=True))

    for dec in pf["decisions"]:
        db.add(Decision(
            id=dec["id"], client_id=dec["client_id"], partner_id=dec["creator_id"], decision_type="creator_renewal",
            summary=f"{dec['compensation_structure'].replace('_', ' ')} renewal ({dec['outcome']})",
            terms={"compensation_structure": dec["compensation_structure"]},
            rationale=dec["reason"], motivated_by_claim_ids=[], status="historical", synthetic=True,
        ))

    for mem in pf["relationship_memories"]:
        db.add(MemoryClaim(
            id=mem["id"], type="relationship_memory", subject_type="creator", subject_id=mem["creator_id"],
            predicate=mem["predicate"], value=mem["value"], scope={"portfolio": "privacy_safe", "synthetic": True},
            client_id=None, claim_class="historical_observation", confidence=0.8, authority_score=0.6,
            source={"type": "portfolio_evidence", "source_id": "synthetic_portfolio"}, valid_from="2026-01-01",
            status="active", supersedes=[], synthetic=True,
        ))

    for pat in pf["patterns"]:
        db.add(PortfolioPattern(
            id=pat["id"], name=pat["name"], predicate=pat["predicate"], value=pat["value"],
            description=pat["description"], evidence_count=pat["evidence_count"], positive_outcomes=pat["positive_outcomes"],
            flat_fee_success_rate=pat["flat_fee_success_rate"], hybrid_success_rate=pat["hybrid_success_rate"],
            strongest_conditions=pat["strongest_conditions"], status=pat["status"],
            supporting_decision_ids=pat["supporting_decision_ids"], synthetic=True,
        ))

    # Make the approved privacy-safe portfolio pattern visible in Northwind's
    # graph from the start (spec Sec.29: aggregated portfolio intelligence is
    # legitimately visible to any client team, unlike raw cross-client terms).
    hybrid_pattern = next((p for p in pf["patterns"] if p["status"] == "approved_portfolio_pattern"), None)
    if hybrid_pattern:
        db.add(MemoryEdge(
            from_type="portfolio_pattern", from_id=hybrid_pattern["id"], to_type="client", to_id=client_id,
            relationship="SUPPORTS", client_id=client_id, synthetic=True,
        ))

    db.flush()

    db.add(ActivityEvent(
        client_id=None, event_type="SEED",
        summary=f"Portfolio seeded: {len(pf['clients'])} synthetic clients, {len(pf['decisions'])} historical decisions, {len(pf['patterns'])} portfolio patterns.",
        detail={"synthetic": True},
    ))
    db.add(ActivityEvent(
        client_id=client_id, event_type="SEED",
        summary="Northwind seeded: client, creator, and campaign data loaded from the case-study data pack.",
        detail={"synthetic": False},
    ))

    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        seed(db, reset=args.reset)
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
