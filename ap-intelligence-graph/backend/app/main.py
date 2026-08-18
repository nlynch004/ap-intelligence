from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import SessionLocal
from app.routers import activity, chat, decisions, demo, graph, memory, recommendations
from app.seed import seed

app = FastAPI(title="AP Intelligence API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(decisions.router)
app.include_router(activity.router)
app.include_router(demo.router)
