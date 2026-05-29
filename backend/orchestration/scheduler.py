"""Nightly Scheduler (Chunk 4.6) — runs the whole agent pipeline after close.

A single APScheduler cron fires at 18:30 IST (13:00 UTC) Mon-Fri and runs every
agent in sequence. Each step is wrapped so ONE agent failing is logged and
recorded but does NOT stop the rest (partial status). The run is recorded in
`pipeline_runs`. Holidays (trading_calendar.is_open=False) are skipped.

`execute_steps` + `summarize_status` are pure orchestration (unit tested with
mock agents); `build_steps` wires the real agents; `run_pipeline` adds the
holiday gate + DB persistence; `schedule` registers the cron.
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import structlog

log = structlog.get_logger()

Step = tuple[str, Callable[[], Awaitable[Any]]]

# Intended IST ordering (single run executes them in this sequence).
SEQUENCE = (
    "price",
    "price_yf",  # yfinance EOD fallback when the manual bhavcopy is absent
    "adjusted",
    "technical",
    "news",
    "sentiment",
    "fundamentals",  # Sunday only
    "sector",
    "fii",
    "macro",
    "risk",
    "ranking",
    "outcome",  # Phase 5.1 — track picks vs actuals (after ranking writes picks)
    "report",
    "auditor",
    "vault",
)


@dataclass
class PipelineResult:
    run_date: date
    started_at: datetime
    finished_at: datetime
    status: str
    agents_run: list[dict[str, Any]]
    total_duration_seconds: int
    error_message: str | None = None


def summarize_status(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    if all(s == "success" for s in statuses):
        return "success"
    if all(s == "failed" for s in statuses):
        return "failed"
    return "partial"


async def execute_steps(steps: list[Step], *, run_date: date) -> PipelineResult:
    """Run steps in order; isolate per-step failures; aggregate the result."""
    started = datetime.now(UTC)
    t0 = time.perf_counter()
    agents_run: list[dict[str, Any]] = []
    statuses: list[str] = []
    errors: list[str] = []

    for name, fn in steps:
        s0 = time.perf_counter()
        status = "success"
        err: str | None = None
        try:
            await fn()
        except Exception as exc:  # one agent failing must not stop the rest
            status = "failed"
            err = f"{type(exc).__name__}: {exc}"
            errors.append(f"{name}: {err}")
            log.warning("pipeline.step.failed", agent=name, error=err)
        else:
            log.info("pipeline.step.ok", agent=name)
        agents_run.append(
            {
                "agent": name,
                "status": status,
                "duration_seconds": round(time.perf_counter() - s0, 2),
                "error": err,
            }
        )
        statuses.append(status)

    return PipelineResult(
        run_date=run_date,
        started_at=started,
        finished_at=datetime.now(UTC),
        status=summarize_status(statuses),
        agents_run=agents_run,
        total_duration_seconds=int(time.perf_counter() - t0),
        error_message="; ".join(errors) or None,
    )


# ---------------------------------------------------------------------------
# Real agent wiring
# ---------------------------------------------------------------------------
class PipelineScheduler:
    name = "pipeline"

    def planned_steps(self, run_date: date) -> list[str]:
        """Names that would run for this date (fundamentals Sunday only)."""
        is_sunday = run_date.weekday() == 6
        return [s for s in SEQUENCE if s != "fundamentals" or is_sunday]

    def build_steps(self, run_date: date, vault_dir: str | None) -> list[Step]:
        builders = self._builders(run_date, vault_dir)
        return [(n, builders[n]) for n in self.planned_steps(run_date)]

    def _builders(
        self, run_date: date, vault_dir: str | None
    ) -> dict[str, Callable[[], Awaitable[Any]]]:
        async def price() -> None:
            from backend.agents.base import RunContext
            from backend.agents.price import PriceAgent, PriceRequest

            await PriceAgent(request=PriceRequest(mode="today")).run(RunContext())

        async def price_yf() -> None:
            from backend.agents.base import RunContext
            from backend.agents.price import PriceAgent, PriceRequest

            await PriceAgent(
                request=PriceRequest(mode="today_yfinance")
            ).run(RunContext())

        async def adjusted() -> None:
            from backend.agents.price_adjust import AdjustedPriceAgent

            await AdjustedPriceAgent().adjust_all()

        async def technical() -> None:
            from backend.agents.technical import TechnicalAgent

            await TechnicalAgent().run_all()

        async def news() -> None:
            from backend.agents.news import NewsAgent

            await NewsAgent().run(sources=("rss",))

        async def sentiment() -> None:
            from backend.agents.sentiment import SentimentAgent

            await SentimentAgent().run()

        async def fundamentals() -> None:
            from backend.agents.fundamentals import FundamentalsAgent

            await FundamentalsAgent().run_all()

        async def sector() -> None:
            from backend.agents.sector import SectorAgent

            await SectorAgent().run_all(as_of_date=run_date)

        async def fii() -> None:
            from backend.agents.fii_dii import FiiDiiAgent

            await FiiDiiAgent().run()  # no file -> resilient empty

        async def macro() -> None:
            from backend.agents.macro import MacroAgent

            await MacroAgent().run()

        async def risk() -> None:
            from backend.agents.risk import RiskAgent

            await RiskAgent().run_all()

        async def ranking() -> None:
            from backend.agents.ranking import RankingAgent

            await RankingAgent().run_all()

        async def outcome() -> None:
            from backend.agents.outcome import OutcomeAgent

            # vault_dir gates memory-file writes (skipped when not mounted).
            await OutcomeAgent().run(today=run_date, vault_dir=vault_dir)

        async def report() -> None:
            from backend.agents.report import ReportAgent

            out = f"{vault_dir}/04_Reports/Daily" if vault_dir else None
            await ReportAgent().run(as_of_date=run_date, out_dir=out)

        async def auditor() -> None:
            from backend.agents.meta_auditor import MetaAuditor

            out = f"{vault_dir}/04_Reports/Audits" if vault_dir else None
            await MetaAuditor().run(report_date=run_date, out_dir=out)

        async def vault() -> None:
            await self._run_vault(vault_dir)

        return {
            "price": price,
            "price_yf": price_yf,
            "adjusted": adjusted,
            "technical": technical,
            "news": news,
            "sentiment": sentiment,
            "fundamentals": fundamentals,
            "sector": sector,
            "fii": fii,
            "macro": macro,
            "risk": risk,
            "ranking": ranking,
            "outcome": outcome,
            "report": report,
            "auditor": auditor,
            "vault": vault,
        }

    @staticmethod
    async def _run_vault(vault_dir: str | None) -> None:
        if not vault_dir:
            raise RuntimeError("no vault_dir configured (mount the vault volume)")
        import asyncio
        from pathlib import Path

        from backend.agents.vault_writer import (
            assemble_notes,
            note_filename,
            render_note,
        )
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            notes = await assemble_notes(session)

        def _write() -> None:
            base = Path(vault_dir) / "01_Stocks"
            base.mkdir(parents=True, exist_ok=True)
            for nd in notes:
                fp = base / note_filename(nd.symbol)
                existing = fp.read_text(encoding="utf-8") if fp.exists() else None
                fp.write_text(render_note(nd, existing), encoding="utf-8")

        await asyncio.to_thread(_write)

    async def run_pipeline(
        self,
        *,
        run_date: date | None = None,
        dry_run: bool = False,
        vault_dir: str | None = None,
    ) -> PipelineResult:
        from backend.db.repositories import pipeline as pipeline_repo
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        as_of = run_date or today_ist()

        if dry_run:
            names = self.planned_steps(as_of)
            now = datetime.now(UTC)
            return PipelineResult(
                run_date=as_of,
                started_at=now,
                finished_at=now,
                status="planned",
                agents_run=[{"agent": n, "status": "planned"} for n in names],
                total_duration_seconds=0,
            )

        async with SessionLocal() as session:
            open_day = await pipeline_repo.is_trading_day(session, as_of)
        if not open_day:
            log.info("pipeline.skipped.holiday", date=as_of.isoformat())
            now = datetime.now(UTC)
            return PipelineResult(
                run_date=as_of,
                started_at=now,
                finished_at=now,
                status="skipped",
                agents_run=[],
                total_duration_seconds=0,
                error_message="market closed (trading_calendar.is_open=False)",
            )

        steps = self.build_steps(as_of, vault_dir)
        result = await execute_steps(steps, run_date=as_of)

        async with SessionLocal() as session:
            await pipeline_repo.upsert_run(session, _result_to_row(result))
            await session.commit()
        log.info(
            "pipeline.run.done",
            date=as_of.isoformat(),
            status=result.status,
            seconds=result.total_duration_seconds,
        )
        return result

    def schedule(self, scheduler: Any, *, vault_dir: str | None = None) -> None:
        """Register the nightly cron: 13:30 UTC (18:30 IST) Mon-Fri."""
        from apscheduler.triggers.cron import CronTrigger

        async def _job() -> None:
            await self.run_pipeline(vault_dir=vault_dir)

        scheduler.add_job(
            _job,
            CronTrigger(day_of_week="mon-fri", hour=13, minute=30),
            id="nightly_pipeline",
            replace_existing=True,
        )
        log.info("pipeline.scheduled", cron="mon-fri 13:30 UTC (18:30 IST)")


def _result_to_row(r: PipelineResult) -> dict[str, Any]:
    return {
        "run_date": r.run_date,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "status": r.status,
        "agents_run": r.agents_run,
        "total_duration_seconds": r.total_duration_seconds,
        "error_message": r.error_message,
    }
