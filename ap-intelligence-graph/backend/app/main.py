from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import SessionLocal
from app.routers import (
    activity,
    campaign_review,
    chat,
    decisions,
    demo,
    graph,
    memory,
    memory_history,
    partner_brief,
    plans,
    recommendations,
    scenario_comparison,
)
from app.seed import seed

app = FastAPI(title="AP Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_admin_password(request: Request, call_next):
    if not settings.admin_password or request.method == "OPTIONS" or request.url.path == "/api/health":
        return await call_next(request)
    if request.headers.get("x-admin-password") != settings.admin_password:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.on_event("startup")
def on_startup() -> None:
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict:
    from app.llm.factory import get_provider

    return {"status": "ok", "llm_provider": get_provider().name}


app.include_router(graph.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(recommendations.router)
app.include_router(campaign_review.router)
app.include_router(partner_brief.router)
app.include_router(memory_history.router)
app.include_router(scenario_comparison.router)
app.include_router(plans.router)
app.include_router(decisions.router)
app.include_router(activity.router)
app.include_router(demo.router)
