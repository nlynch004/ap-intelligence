"""Demo-only reset endpoint.

NOT a production pattern - a real product would never expose an endpoint
that drops and recreates the entire schema. This exists purely so this
prototype's live demo can be rehearsed and re-run from a known-good state
without restarting the backend process or reloading the browser. The route
prefix, response body, and the frontend control that calls it are all
labeled demo-only for the same reason.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.seed import seed

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset")
def reset_demo(db: Session = Depends(get_db)) -> dict:
    seed(db, reset=True)
    return {
        "status": "ok",
        "demo_only": True,
        "message": (
            "Demo data reset to the original seeded state. This reset capability is "
            "demo-only scaffolding for rehearsing this prototype and would not exist "
            "in this form in a production system."
        ),
    }
