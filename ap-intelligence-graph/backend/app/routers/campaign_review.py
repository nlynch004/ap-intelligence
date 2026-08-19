from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.memory.manager import run_campaign_review

router = APIRouter(prefix="/api/campaign-review", tags=["campaign-review"])


@router.post("", response_model=schemas.CampaignReviewResponse)
def review_campaign(req: schemas.CampaignReviewRequest, db: Session = Depends(get_db)):
    result = run_campaign_review(db, campaign_id=req.campaign_id)
    if result is None:
        raise HTTPException(404, "campaign not found")
    return result
