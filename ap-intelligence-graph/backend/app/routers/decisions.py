"""Decision capture + simulated outcome loop (spec Sec.19 Scenes 5-6).

Both endpoints write graph edges directly (deterministic - spec Sec.22),
never through the LLM.
"""

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.memory.operations import execute_promote_pattern_evidence, log_activity
from app.serializers import decision_to_out, outcome_to_out

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.post("", response_model=schemas.DecisionOut)
def create_decision(req: schemas.DecisionCreateRequest, db: Session = Depends(get_db)):
    client = db.get(models.Client, req.client_id)
    partner = db.get(models.Partner, req.partner_id)
    if not client or not partner:
        raise HTTPException(404, "client or partner not found")

    decision = models.Decision(
        client_id=req.client_id, partner_id=req.partner_id, decision_type="creator_renewal",
        summary=req.summary, terms=req.terms, rationale=req.rationale,
        motivated_by_claim_ids=req.motivated_by_claim_ids, status="approved", synthetic=False,
    )
    db.add(decision)
    db.flush()

    db.add(models.MemoryEdge(from_type="client", from_id=req.client_id, to_type="decision", to_id=decision.id, relationship="MADE_DECISION", client_id=req.client_id))
    db.add(models.MemoryEdge(from_type="decision", from_id=decision.id, to_type="partner", to_id=req.partner_id, relationship="APPLIES_TO", client_id=req.client_id))
    for claim_id in req.motivated_by_claim_ids:
        target_type = "portfolio_pattern" if db.get(models.PortfolioPattern, claim_id) else "memory_claim"
        db.add(models.MemoryEdge(from_type="decision", from_id=decision.id, to_type=target_type, to_id=claim_id, relationship="MOTIVATED_BY", client_id=req.client_id))

    log_activity(db, req.client_id, "DECISION", req.summary, detail={"decision_id": decision.id, "terms": req.terms})
    db.commit()
    return decision_to_out(decision)


@router.post("/{decision_id}/simulate-outcome", response_model=schemas.SimulateOutcomeResponse)
def simulate_outcome(decision_id: str, db: Session = Depends(get_db)):
    """DEMO-ONLY: fabricates a plausible outcome for the accepted decision so
    the learning-loop story (decision -> outcome -> pattern evidence) can be
    shown live without waiting on a real campaign cycle."""
    decision = db.get(models.Decision, decision_id)
    if not decision:
        raise HTTPException(404, "decision not found")

    base_fee = decision.terms.get("base_fee", 3500)
    bonus_pct = decision.terms.get("performance_bonus_pct", 10)
    rng = random.Random(decision_id)
    verified_new_customer_revenue = round(base_fee * rng.uniform(5.5, 6.5), -2)
    attributed_revenue = round(verified_new_customer_revenue * rng.uniform(1.3, 1.5), -2)
    metrics = {
        "verified_new_customer_revenue": verified_new_customer_revenue,
        "attributed_revenue": attributed_revenue,
        "promo_code_integrity": "clean",
        "contribution_target": "exceeded",
        "base_fee": base_fee,
        "performance_bonus_pct": bonus_pct,
    }
    outcome = models.Outcome(decision_id=decision.id, metrics=metrics, outcome_label="positive", is_simulated=True)
    db.add(outcome)
    db.flush()

    db.add(models.MemoryEdge(from_type="decision", from_id=decision.id, to_type="outcome", to_id=outcome.id, relationship="RESULTED_IN", client_id=decision.client_id))

    log_activity(
        db, decision.client_id, "OUTCOME",
        f"Simulated outcome for {decision.summary}: verified new-customer revenue ${verified_new_customer_revenue:,.0f}, outcome positive.",
        detail={"decision_id": decision.id, "outcome_id": outcome.id, "metrics": metrics, "is_simulated": True},
    )

    pattern = None
    before = after = None
    for claim_id in decision.motivated_by_claim_ids:
        pattern = db.get(models.PortfolioPattern, claim_id)
        if pattern:
            break
    if pattern:
        before, after = execute_promote_pattern_evidence(db, pattern, positive=True, new_decision_id=decision.id)
        db.add(models.MemoryEdge(from_type="outcome", from_id=outcome.id, to_type="portfolio_pattern", to_id=pattern.id, relationship="SUPPORTS", client_id=decision.client_id))

    db.commit()
    return schemas.SimulateOutcomeResponse(
        outcome=outcome_to_out(outcome), pattern_id=pattern.id if pattern else None,
        pattern_evidence_count_before=before, pattern_evidence_count_after=after,
    )
