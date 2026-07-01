"""Maven Newsroom OS — FastAPI entrypoint (localhost:8000).

Wraps the existing maven_instagram pipeline with observability + control. On
startup it ingests any completed runs from outputs/maven_instagram so the
dashboard has real data immediately.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import FRONTEND_ORIGINS
from .database import init_db
from .routes import actions, jobs, settings, stream
from .services.ingest import ingest_all
from .services.ingest_reels import ingest_all as ingest_reels_all

app = FastAPI(title="Maven Newsroom OS", version="1.0.0",
              description="Observability + control API for the Maven Instagram "
                          "automation pipeline.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(jobs.router)
app.include_router(stream.router)
app.include_router(actions.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    ingested = ingest_all()
    reels = ingest_reels_all()
    print(f"[Newsroom] DB ready. Carousel: {ingested or 'none'} | Reels: {reels or 'none'}")


@app.get("/")
def root():
    return {"service": "Maven Newsroom OS", "docs": "/docs", "api": "/api/health"}
