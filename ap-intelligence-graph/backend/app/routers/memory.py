from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.memory.manager import approve_candidate, reject_candidate, resolve_conflict
from app.serializers import claim_to_out

router = APIRouter(prefix="/api/memories", tags=["memory"])


@router.post("/review", response_model=schemas.MemoryReviewResponse)
def review_candidate(req: schemas.MemoryReviewRequest, db: Session = Depends(get_db)):
    candidate = db.get(models.MemoryCandidate, req.candidate_id)
    if not candidate:
        raise HTTPException(404, "candidate not found")
    if candidate.status != "pending":
        raise HTTPException(409, f"candidate already {candidate.status}")

    if req.action == "reject":
        reject_candidate(db, candidate)
        db.commit()
        return schemas.MemoryReviewResponse(candidate_id=candidate.id, operation_executed="REJECT", claim=None)

    result = approve_candidate(db, candidate)
    db.commit()
    return schemas.MemoryReviewResponse(
        candidate_id=candidate.id,
        operation_executed=result["operation_executed"],
        claim=claim_to_out(result["claim"]) if result["claim"] else None,
        superseded_claim=claim_to_out(result["superseded_claim"]) if result["superseded_claim"] else None,
        requires_conflict_resolution=result["requires_conflict_resolution"],
        conflict_with_claim=claim_to_out(result["conflict_with_claim"]) if result["conflict_with_claim"] else None,
    )


@router.post("/conflicts/{conflict_id}/resolve", response_model=schemas.ConflictResolveResponse)
def resolve(conflict_id: str, req: schemas.ConflictResolveRequest, db: Session = Depends(get_db)):
    candidate = db.get(models.MemoryCandidate, conflict_id)
    if not candidate:
        raise HTTPException(404, "conflict not found")
    if candidate.status == "rejected":
        raise HTTPException(409, "candidate already resolved")

    result = resolve_conflict(db, candidate, req.operation)
    db.commit()
    return schemas.ConflictResolveResponse(
        new_claim=claim_to_out(result["new_claim"]) if result["new_claim"] else None,
        superseded_claim=claim_to_out(result["superseded_claim"]) if result["superseded_claim"] else None,
    )
