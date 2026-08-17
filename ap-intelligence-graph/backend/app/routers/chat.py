from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agents.recommendation_agent import generate_recommendation
from app.db import get_db
from app.llm.factory import call_with_fallback
from app.memory.manager import propose_candidates_from_message
from app.memory.retrieval import active_client_memories, build_recommendation_context
from app.serializers import candidate_to_out

router = APIRouter(prefix="/api", tags=["chat"])

_UP_TO_SPEED_KEYWORDS = ["bring me up to speed", "up to speed", "catch me up", "where do things stand"]


def _matched_partner(db: Session, client_id: str, text: str) -> models.Partner | None:
    lowered = text.lower()
    partners = (
        db.query(models.Partner)
        .join(models.Campaign, models.Campaign.partner_id == models.Partner.id)
        .filter(models.Campaign.client_id == client_id)
        .distinct()
        .all()
    )
    for p in partners:
        if p.name.lower() in lowered:
            return p
    return None


def _looks_like_decision_question(text: str) -> bool:
    lowered = text.lower()
    return "$" in text or any(kw in lowered for kw in ["renew", "should we", "worth renewing", "renegotiat"])


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(req: schemas.ChatRequest, db: Session = Depends(get_db)):
    client = db.get(models.Client, req.client_id)
    if not client:
        raise HTTPException(404, "client not found")

    text = req.message.strip()
    lowered = text.lower()

    # Scene 1: retrieval-only "bring me up to speed" query.
    if any(kw in lowered for kw in _UP_TO_SPEED_KEYWORDS):
        active = active_client_memories(db, req.client_id)
        claim_dicts = [{"predicate": c.predicate, "value": c.value} for c in active]
        summary, _provider = call_with_fallback("summarize", client.name, claim_dicts)
        return schemas.ChatResponse(reply=summary, candidates=[], referenced_memory_ids=[c.id for c in active])

    # Scene 4: a consequential business question about a specific partner.
    partner = _matched_partner(db, req.client_id, text)
    if partner and _looks_like_decision_question(text):
        ctx = build_recommendation_context(db, client_id=req.client_id, partner_id=partner.id, question=text)
        raw_rec, _provider = generate_recommendation(text, ctx["evidence_brief"], ctx["structured_context"])
        rec = schemas.RecommendationResponse(
            client_id=req.client_id,
            partner_id=partner.id,
            decision_evidence=ctx["decision_evidence"],
            recommendation=raw_rec["recommendation"],
            recommended_terms=raw_rec["recommended_terms"],
            confidence=raw_rec["confidence"],
            supporting_memory_ids=ctx["supporting_memory_ids"],
            uncertainties=raw_rec.get("uncertainties", []),
            explanation=raw_rec.get("explanation", ""),
            evidence_brief=ctx["evidence_brief"],
        )
        reply = f"Recommendation: {raw_rec['recommendation'].replace('_', ' ')}. {raw_rec.get('explanation', '')}"
        return schemas.ChatResponse(reply=reply, candidates=[], referenced_memory_ids=ctx["supporting_memory_ids"], recommendation=rec)

    # Scene 2: natural-language memory extraction.
    candidates, _provider = propose_candidates_from_message(db, client_id=req.client_id, message=text)
    db.commit()

    if not candidates:
        return schemas.ChatResponse(reply="Noted - I didn't find anything durable enough to remember from that message.", candidates=[])

    conflicts = {
        c.conflict_with_claim_id: db.get(models.MemoryClaim, c.conflict_with_claim_id)
        for c in candidates if c.conflict_with_claim_id
    }
    candidate_outs = [candidate_to_out(c, conflicts.get(c.conflict_with_claim_id)) for c in candidates]
    reply = f"I found {len(candidates)} potentially useful {'memory' if len(candidates) == 1 else 'memories'}. Review below."
    return schemas.ChatResponse(reply=reply, candidates=candidate_outs, referenced_memory_ids=[])
