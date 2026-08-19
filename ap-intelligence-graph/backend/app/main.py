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
    """Light shared-secret gate (spec: "light password protected login just
    for me to use as admin") - not a real auth system. A single password,
    configured once via ADMIN_PASSWORD, must be echoed back on every request
    as the X-Admin-Password header; the deployed frontend's login flow
    stores it after a successful login and attaches it to every API call
    (see frontend/lib/api.ts + frontend/proxy.ts).

    Deliberately a no-op when ADMIN_PASSWORD isn't set (local dev, and any
    environment that hasn't opted in) so this never affects local
    development or the existing test suite - every test/live-verification
    call in this repo runs with no ADMIN_PASSWORD set. CORS preflight
    (OPTIONS) and the health check are always let through - the browser's
    own preflight request never carries custom headers, and health checks
    are harmless to leave open."""
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
