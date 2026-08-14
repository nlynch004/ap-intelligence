from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.serializers import activity_to_out

router = APIRouter(prefix="/api/clients", tags=["activity"])


@router.get("/{client_id}/activity", response_model=list[schemas.ActivityEventOut])
def get_activity(client_id: str, limit: int = 25, db: Session = Depends(get_db)):
    events = (
        db.query(models.ActivityEvent)
        .filter(or_(models.ActivityEvent.client_id == client_id, models.ActivityEvent.client_id.is_(None)))
        .order_by(models.ActivityEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [activity_to_out(e) for e in reversed(events)]
