from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.memory.manager import run_scenario_comparison

router = APIRouter(prefix="/api/scenario-comparison", tags=["scenario-comparison"])


@router.post("", response_model=schemas.ScenarioComparisonResponse)
def scenario_comparison(req: schemas.ScenarioComparisonRequest, db: Session = Depends(get_db)):
    result = run_scenario_comparison(db, client_id=req.client_id, partner_id=req.partner_id, current_ask=req.current_ask)
    if result is None:
        raise HTTPException(404, "partner not found")
    return result
