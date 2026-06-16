# Repository structure

A file-and-folder map of the repo: what each thing is for, one line each. For *how*
the pieces fit together see [ARCHITECTURE.md](ARCHITECTURE.md); for *why* the strategy
is shaped the way it is see [VALIDATION.md](VALIDATION.md).

---

## Top level

| Path | Purpose |
|---|---|
| `README.md` | Project overview and the honest result — start here. |
| `CLAUDE.md` | Project rules & conventions read by Claude Code at session start. The hard rules (§2) are non-negotiable. |
| `AGENTS.md` | The same contract for Codex/other assistants, plus a running follow-ups log. |
| `DEPLOY.md` | How to deploy the forward paper tracker (VM/Railway + cron + sizing). |
| `HOSTED_DB.md` | Notes on migrating Postgres to a hosted provider (Neon). |
| `docker-compose.yml` | Single-host stack: Postgres, Redis, backend. |
| `pyproject.toml` | Python package + tool config (ruff, mypy, pytest). |
| `alembic.ini` / `alembic/` | Database migrations. |
| `.env.example` | Template for every required env var — copy to `.env` (gitignored) and fill in. |
| `.gitignore` | Ignore rules (secrets, caches, data drops, heavy doc assets, diag scratch). |
| `docs/` | This documentation set. |
| `assets/` | Static assets. |

## `backend/` — the application

| Path | Purpose |
|---|---|
| `main.py` | FastAPI entrypoint. |
| `cli.py` | Typer CLI (`bharat …`) — the main operator interface. |
| `config.py` | `pydantic-settings`, reads `.env`. |
| `errors.py` | `BharatError` base + typed subclasses. |
| `logging_setup.py` | `structlog` configuration. |
| `agents/` | The nightly research agents (price, technical, fundamentals, news, sentiment, sector, fii_dii, macro, risk, ranking, report, meta_auditor, …). |
| `backtest/` | **The validated strategy harness — see below.** |
| `paper/` | Forward paper-trading layer running the frozen F+ engine (`engine.py`). |
| `data_sources/` | Read-only external clients (yfinance, NSE bhavcopy, news APIs). |
| `db/` | SQLAlchemy models (`models.py`) + `repositories/` (data access, no business logic). |
| `orchestration/` | APScheduler triggers / LangGraph wiring. |
| `services/` | Cross-cutting services — `vault.py` (all Obsidian I/O), `finbert.py`, `alerts.py`. |
| `api/` | FastAPI routers. |
| `data/` | In-package data (e.g. scenario patterns) — *tracked*, distinct from the gitignored root `data/`. |
| `tests/` | `pytest` suite (mocked external calls; `respx` for HTTP). |

## `backend/backtest/` — the F+ harness (frozen core)

| Path | Status | Purpose |
|---|---|---|
| `engine.py` | **Frozen** | The strategy engine — configs A–F+ logic. Do not modify. |
| `runner.py` | **Frozen** | Walk-forward / full-period backtest runner. |
| `scores.py` | **Frozen** | Score reconstruction for the backtest. |
| `cost_model.py` | Tracked | Transaction-cost model (round-trip %, applied once on notional). |
| `audit_*.py`, `sweep*.py`, `verify*.py`, `run_config_d.py`, `*_results.json` | Untracked | One-off probes from the validation runs — scratch, not part of the committed engine. |

> **"Frozen" means** the F+ decision logic was validated (see VALIDATION.md) and is not
> changed by ongoing work. Configs A–F are byte-identical earlier rungs; F+'s two extra
> behaviors default OFF. A regression test enforces this.

## Other top-level dirs

| Path | Purpose |
|---|---|
| `scripts/` | Operator/ops scripts: data backfills, benchmark ingest, `nightly_run.py`, `paper_inception.py`, hosted-DB smoke test. |
| `services/finbert/` | Local FinBERT sentiment sidecar (FastAPI + transformers). |
| `frontend/` | Next.js dashboard (early). |
| `maven-dashboard/` | "Maven" — the 2-screen F+ paper-trading UI. |

---

## Conventions worth knowing

- **`scripts/diag_*.py` are throwaway by convention** — diagnostic probes are *not*
  committed (gitignored). Validated logic lives under `backend/`; one-off
  investigation scripts do not. The same applies to the `audit/sweep/verify` scratch
  in `backend/backtest/`: only `engine.py`, `runner.py`, `scores.py`, `cost_model.py`,
  and `__init__.py` are tracked there.
- **The root `data/` is gitignored** (operator-downloaded CSV drop zone). The
  in-package `backend/data/` is *not* — it ships source data files.
- **The Obsidian vault is a separate repository.** It is gitignored here
  (`ResearchBrain/`, `vault_emit.ndjson`) and synced on its own. Claude Code writes
  lessons there, never to `04_Reports/`.
- **`docs/` tracks markdown only.** Heavy/vendored assets under `docs/`
  (`banner.png`, `superpowers/`, `fincept-vs-bharat.html`) are gitignored.
- **Secrets never get committed.** `.env` is gitignored; `.env.example` carries the
  key *names* with empty/placeholder values only.
