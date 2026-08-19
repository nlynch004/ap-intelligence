from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.memory.manager import run_partner_brief

router = APIRouter(prefix="/api/partner-brief", tags=["partner-brief"])


@router.post("", response_model=schemas.PartnerBriefResponse)
def partner_brief(req: schemas.PartnerBriefRequest, db: Session = Depends(get_db)):
    result = run_partner_brief(db, partner_id=req.partner_id, client_id=req.client_id)
    if result is None:
        raise HTTPException(404, "partner not found")
    return result
