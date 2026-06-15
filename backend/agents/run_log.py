"""Agent run-log heartbeat (Chunk 5.3 — Maven observability).

Lightweight status telemetry: as each agent runs in the nightly pipeline it upserts
one row in `agent_run_log` (status / progress / one-line headline / timing), keyed
(run_id, agent_name). The Maven dashboard's Agent Activity board polls this table.

This is PURE telemetry — it does NOT touch F+, the paper engine, or the scores. An
agent typically calls `heartbeat(... "running")` at start, optional progress updates,
then `heartbeat(... "done", headline=...)` at the end. The `agent_run` async context
manager wires start/done/error + timing automatically:

    async with agent_run(session, run_id, "Momentum") as hb:
        ...
        await hb.progress(340, 507)
        await hb.set_headline("Scored 507 stocks")

Or one-shot for already-known outcomes:

    await heartbeat(session, run_id, "Sentiment", "offline",
                    offline_reason="FinBERT not enabled")
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()

IST = timezone(timedelta(hours=5, minutes=30))
Status = Literal["running", "done", "waiting", "offline", "error"]

_UPSERT = text(
    """
    INSERT INTO agent_run_log
        (run_id, agent_name, status, progress_current, progress_total,
         headline_output, offline_reason, started_at, finished_at, duration_ms,
         updated_at)
    VALUES
        (:run_id, :agent, :status, :pc, :pt, :headline, :offline, :started,
         :finished, :duration, now())
    ON CONFLICT (run_id, agent_name) DO UPDATE SET
        status = EXCLUDED.status,
        progress_current = COALESCE(EXCLUDED.progress_current, agent_run_log.progress_current),
        progress_total = COALESCE(EXCLUDED.progress_total, agent_run_log.progress_total),
        headline_output = CASE WHEN EXCLUDED.headline_output = ''
            THEN agent_run_log.headline_output ELSE EXCLUDED.headline_output END,
        offline_reason = EXCLUDED.offline_reason,
        started_at = COALESCE(agent_run_log.started_at, EXCLUDED.started_at),
        finished_at = EXCLUDED.finished_at,
        duration_ms = EXCLUDED.duration_ms,
        updated_at = now()
    """
)


async def heartbeat(
    session: AsyncSession,
    run_id: str,
    agent_name: str,
    status: Status,
    *,
    progress: int | None = None,
    total: int | None = None,
    headline: str = "",
    offline_reason: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    duration_ms: int | None = None,
) -> None:
    """Upsert one agent_run_log row. Commits immediately so the dashboard polls see
    it live. Never raises into the caller's agent logic (telemetry is best-effort)."""
    try:
        await session.execute(_UPSERT, {
            "run_id": run_id, "agent": agent_name, "status": status,
            "pc": progress, "pt": total, "headline": headline,
            "offline": offline_reason, "started": started_at,
            "finished": finished_at, "duration": duration_ms,
        })
        await session.commit()
    except Exception as exc:  # noqa: BLE001 - telemetry must not break the pipeline
        log.warning("agent_run_log.heartbeat_failed", agent=agent_name, error=str(exc))
        await session.rollback()


class _Beat:
    """Handle yielded by `agent_run` for progress/headline updates mid-run."""

    def __init__(self, session: AsyncSession, run_id: str, agent: str, started: datetime):
        self._s, self._run, self._agent, self._started = session, run_id, agent, started
        self._headline = ""

    async def progress(self, current: int, total: int) -> None:
        await heartbeat(self._s, self._run, self._agent, "running",
                        progress=current, total=total, headline=self._headline,
                        started_at=self._started)

    async def set_headline(self, headline: str) -> None:
        self._headline = headline
        await heartbeat(self._s, self._run, self._agent, "running",
                        headline=headline, started_at=self._started)


@asynccontextmanager
async def agent_run(session: AsyncSession, run_id: str, agent_name: str):
    """Mark an agent running on entry; done (with duration) on clean exit, error on
    exception. Yields a `_Beat` for progress/headline updates."""
    started = datetime.now(IST)
    await heartbeat(session, run_id, agent_name, "running", started_at=started)
    beat = _Beat(session, run_id, agent_name, started)
    try:
        yield beat
    except Exception:
        await heartbeat(session, run_id, agent_name, "error",
                        headline=beat._headline, started_at=started,
                        finished_at=datetime.now(IST))
        raise
    else:
        end = datetime.now(IST)
        await heartbeat(session, run_id, agent_name, "done",
                        headline=beat._headline, started_at=started,
                        finished_at=end,
                        duration_ms=int((end - started).total_seconds() * 1000))
