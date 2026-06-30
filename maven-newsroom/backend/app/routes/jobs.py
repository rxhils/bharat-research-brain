"""Read endpoints: jobs, nodes, events, artifacts, scores."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from .. import database as db
from ..registry import CLASS_LABELS, GRAPH_ORDER, NODES

router = APIRouter(prefix="/api")


@router.get("/nodes")
def registry():
    """Static node registry (names, classes, types, graph order)."""
    return {"nodes": NODES, "graph_order": GRAPH_ORDER, "class_labels": CLASS_LABELS}


@router.get("/jobs")
def list_jobs():
    jobs = db.query_all("SELECT * FROM jobs ORDER BY date DESC, created_at DESC")
    for j in jobs:
        j["scores"] = db.query_one("SELECT * FROM scores WHERE job_id=?", (j["job_id"],))
        j["thumbnails"] = [a["name"] for a in db.query_all(
            "SELECT name FROM artifacts WHERE job_id=? AND name LIKE 'slide_%.jpg' "
            "ORDER BY name", (j["job_id"],))]
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = db.query_one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
    if not job:
        raise HTTPException(404, f"job {job_id} not found")
    job["scores"] = db.query_one("SELECT * FROM scores WHERE job_id=?", (job_id,))
    job["nodes"] = db.query_all("SELECT * FROM nodes WHERE job_id=? ORDER BY ord", (job_id,))
    job["artifact_count"] = db.query_one(
        "SELECT COUNT(*) AS n FROM artifacts WHERE job_id=?", (job_id,))["n"]
    return job


@router.get("/jobs/{job_id}/nodes")
def get_nodes(job_id: str):
    return {"nodes": db.query_all(
        "SELECT * FROM nodes WHERE job_id=? ORDER BY ord", (job_id,))}


@router.get("/jobs/{job_id}/events")
def get_events(job_id: str, after_seq: int = 0, limit: int = 2000):
    return {"events": db.query_all(
        "SELECT * FROM events WHERE job_id=? AND seq>? ORDER BY seq LIMIT ?",
        (job_id, after_seq, limit))}


@router.get("/jobs/{job_id}/artifacts")
def get_artifacts(job_id: str):
    return {"artifacts": db.query_all(
        "SELECT * FROM artifacts WHERE job_id=? ORDER BY created_at", (job_id,))}


@router.get("/jobs/{job_id}/scores")
def get_scores(job_id: str):
    return db.query_one("SELECT * FROM scores WHERE job_id=?", (job_id,)) or {}


@router.get("/jobs/{job_id}/artifact/{name}")
def serve_artifact(job_id: str, name: str):
    art = db.query_one("SELECT * FROM artifacts WHERE job_id=? AND name=?",
                       (job_id, name))
    if not art:
        raise HTTPException(404, "artifact not found")
    path = Path(art["path"])
    if not path.exists():
        raise HTTPException(410, "artifact file missing on disk")
    if art["artifact_type"] == "json":
        try:
            return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return FileResponse(str(path))
    media = {"video": "video/mp4", "audio": "audio/mp4", "log": "text/plain"
             }.get(art["artifact_type"])
    return FileResponse(str(path), media_type=media) if media else FileResponse(str(path))
