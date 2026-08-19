from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.memory.manager import run_memory_history, run_what_changed_summary

router = APIRouter(prefix="/api/memory-history", tags=["memory-history"])


@router.post("", response_model=schemas.MemoryHistoryResponse)
def memory_history(req: schemas.MemoryHistoryRequest, db: Session = Depends(get_db)):
    """Deterministic timeline + optional narration for one governed
    (subject, predicate) - the same shared service the bounded chat intent
    in routers/chat.py calls (spec Phase 4 Sec.25). Strictly read-only."""
    result = run_memory_history(
        db, subject_type=req.subject_type, subject_id=req.subject_id,
        predicate=req.predicate, client_id=req.client_id,
    )
    if result is None:
        raise HTTPException(404, "no governed claim exists for this subject/predicate")
    return result


@router.post("/what-changed", response_model=schemas.WhatChangedSummary)
def what_changed(req: schemas.WhatChangedRequest, db: Session = Depends(get_db)):
    """Broader 'what changed for this subject?' summary (spec Phase 4
    Sec.10) - deterministic only, no LLM call. Returns an empty
    changed_dimensions list rather than an error when nothing has
    changed; that is itself useful information (spec Sec.30)."""
    return run_what_changed_summary(db, subject_type=req.subject_type, subject_id=req.subject_id, client_id=req.client_id)
