"""Account planning API (spec Phase 6). Deliberately a small, explicit
surface (spec Sec.28) - no generic write endpoint.

POST /api/plans/propose        - read-only; returns a PlanProposalResponse,
                                  never persists anything.
POST /api/plans                - persists a Plan + its approved
                                  PlannedActions (only what the human
                                  approved reaches this endpoint).
GET  /api/clients/{id}/plans   - list plans for a client.
PATCH /api/plans/{id}          - plan-level status transition.
PATCH /api/planned-actions/{id} - status/owner/due_date/summary edit.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.memory.manager import create_plan, list_plans_for_client, propose_plan, update_plan, update_planned_action

router = APIRouter(tags=["plans"])


@router.post("/api/plans/propose", response_model=schemas.PlanProposalResponse)
def propose(req: schemas.PlanProposeRequest, db: Session = Depends(get_db)):
    result = propose_plan(
        db, client_id=req.client_id, partner_ids=req.partner_ids,
        planning_period=req.planning_period, scenario_inputs=req.scenario_inputs,
    )
    if result is None:
        raise HTTPException(404, "client not found")
    return result


@router.post("/api/plans", response_model=schemas.PlanCreateResponse)
def create(req: schemas.PlanCreateRequest, db: Session = Depends(get_db)):
    result = create_plan(db, req)
    if result is None:
        raise HTTPException(404, "client not found")
    return result


@router.get("/api/clients/{client_id}/plans", response_model=list[schemas.PlanOut])
def list_plans(client_id: str, db: Session = Depends(get_db)):
    return list_plans_for_client(db, client_id)


@router.patch("/api/plans/{plan_id}", response_model=schemas.PlanOut)
def patch_plan(plan_id: str, req: schemas.PlanUpdate, db: Session = Depends(get_db)):
    result = update_plan(db, plan_id, req)
    if result is None:
        raise HTTPException(404, "plan not found")
    return result


@router.patch("/api/planned-actions/{action_id}", response_model=schemas.PlannedActionOut)
def patch_planned_action(action_id: str, req: schemas.PlannedActionUpdate, db: Session = Depends(get_db)):
    result = update_planned_action(db, action_id, req)
    if result is None:
        raise HTTPException(404, "planned action not found")
    return result
