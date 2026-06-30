# Maven Newsroom OS

**Daily Indian Market Intelligence Engine** — an observability + control layer
that lets you watch the Maven Instagram automation pipeline run after the Indian
market closes.

It **wraps** the existing `maven_instagram/` pipeline. It does not modify or
re-implement any pipeline business logic — it reads the artifacts the pipeline
writes, records runs in SQLite, and streams structured events to a dashboard.

```
maven-newsroom/
├── backend/   FastAPI + SQLite + SSE  (localhost:8000)   ✅ built
└── frontend/  Next.js premium dashboard (localhost:3000)  ⏳ next phase
```

## Backend (Phase 1 — done)

A FastAPI app that:
- ingests completed runs from `outputs/maven_instagram/<date>/` on startup (your
  real **2026-06-29** run loads automatically — published, scores 100/94/100,
  permalink `/p/DaK2L2clAFs/`),
- maps the pipeline to **17 newsroom agents** with their honest types
  (LLM Agent / Deterministic / External MCP Service / Guardrail / Publisher /
  Orchestrator),
- emits structured events to SQLite + JSONL + **SSE** (one event path, also used
  by the Telegram bridge),
- runs a **live simulation** you can watch animate the pipeline (`POST /api/run`),
- exposes honest **adapters** for actions that need the agent runtime: image
  regeneration and the real Instagram publish return `requires_runtime` and mark
  the step pending — they never fake a render or a publish.

### Run it
```bash
cd maven-newsroom/backend
pip install -r requirements.txt          # fastapi, uvicorn, pydantic
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open http://localhost:8000/docs for the interactive API, or hit
http://localhost:8000/api/health.

### Key endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health`, `/api/meta` | status, market open?, next run |
| GET | `/api/agents` | the 17-agent registry + graph order |
| GET | `/api/jobs` · `/api/jobs/{id}` | runs (with scores) |
| GET | `/api/jobs/{id}/agents` · `/events` · `/artifacts` · `/scores` | run detail |
| GET | `/api/jobs/{id}/artifact/{name}` | serve a JSON / image / video / log |
| GET | `/api/jobs/{id}/stream` | **SSE** live event stream |
| POST | `/api/run` | start a live simulation run |
| POST | `/api/jobs/{id}/rerun/{agent}` · `/rerun-from/{agent}` | rerun |
| POST | `/api/jobs/{id}/regenerate-images` · `/rewrite-caption` · `/recheck-quality` | step actions |
| POST | `/api/jobs/{id}/approve` · `/reject` · `/publish` | review + publish |
| GET/POST | `/api/settings` | brand, schedule, thresholds, integrations |

### Data model (SQLite, `backend/data/newsroom.db`)
`jobs`, `agents`, `events`, `artifacts`, `scores` — created on startup.

### Honesty contract
- Publishing only ever shows as published if the pipeline artifacts contain a
  real Instagram media id + permalink. The backend cannot reach Composio, so its
  `/publish` returns `requires_runtime` — the real publish happens in the agent
  runtime / 5 PM cron.
- Historical per-agent timings are **reconstructed** (flagged); statuses, scores,
  images and permalinks are read straight from real artifacts.
