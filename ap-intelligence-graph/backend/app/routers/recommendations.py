from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agents.recommendation_agent import generate_recommendation
from app.db import get_db
from app.memory.retrieval import build_recommendation_context

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.post("", response_model=schemas.RecommendationResponse)
def create_recommendation(req: schemas.RecommendationRequest, db: Session = Depends(get_db)):
    client = db.get(models.Client, req.client_id)
    partner = db.get(models.Partner, req.partner_id)
    if not client or not partner:
        raise HTTPException(404, "client or partner not found")

    ctx = build_recommendation_context(db, client_id=req.client_id, partner_id=req.partner_id, question=req.question)
    raw_rec, _provider = generate_recommendation(req.question, ctx["evidence_brief"], ctx["structured_context"])

    return schemas.RecommendationResponse(
        client_id=req.client_id,
        partner_id=req.partner_id,
        recommendation=raw_rec["recommendation"],
        recommended_terms=raw_rec["recommended_terms"],
        confidence=raw_rec["confidence"],
        supporting_memory_ids=ctx["supporting_memory_ids"],
        uncertainties=raw_rec.get("uncertainties", []),
        explanation=raw_rec.get("explanation", ""),
        evidence_brief=ctx["evidence_brief"],
    )
