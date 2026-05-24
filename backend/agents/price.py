"""Price Agent — backfills + refreshes end-of-day OHLCV from NSE bhavcopies.

Two modes:
  - backfill(start, end): download every open trading day in range that we
    don't already have, filter, and bulk-insert.
  - fetch_today(): the same for today only, skipping non-trading days and
    bailing politely if the file isn't published yet (before 18:30 IST).

Downloads run concurrently (bounded by a semaphore). A missing file for one
date logs a BHAVCOPY_MISSING data-quality warning and the run continues.
`--dry-run` downloads + parses + filters but inserts nothing.

Scope (Chunk 1.3): raw OHLCV only. No adjusted prices, corporate actions,
or live ticks.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import ClassVar

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import AgentResult, BaseAgent, HealthStatus, RunContext
from backend.data_sources.nse_bhavcopy import (
    BhavRow,
    FilterWarning,
    NSEBhavcopyClient,
    filter_rows,
)
from backend.db.models import DataIngestionRun, DataQualityLog, Stock
from backend.db.repositories import calendar as calendar_repo
from backend.db.repositories import prices as prices_repo
from backend.db.repositories._helpers import IST, today_ist
from backend.db.session import SessionLocal, ping_db
from backend.errors import DataSourceError

log = structlog.get_logger()

_QUALITY_CODES = frozenset({"ZERO_OR_NEGATIVE_PRICE", "OHLC_VIOLATION"})
_PUBLISH_HOUR = 18
_PUBLISH_MINUTE = 30


@dataclass
class PriceResult:
    open_days: int = 0
    present_days: int = 0
    dates_attempted: int = 0
    dates_succeeded: int = 0
    dates_failed: int = 0
    rows_ready: int = 0
    rows_inserted: int = 0
    rows_skipped: int = 0
    rows_warned: int = 0
    warnings: list[FilterWarning] = field(default_factory=list)
    missing: list[date] = field(default_factory=list)
    failed_dates: list[date] = field(default_factory=list)
    note: str | None = None

    def counts(self) -> dict[str, int]:
        return {
            "dates_attempted": self.dates_attempted,
            "dates_succeeded": self.dates_succeeded,
            "dates_failed": self.dates_failed,
            "rows_ready": self.rows_ready,
            "rows_inserted": self.rows_inserted,
            "rows_skipped": self.rows_skipped,
            "rows_warned": self.rows_warned,
        }


@dataclass
class PriceRequest:
    """What a base.run()-driven invocation should do."""

    mode: str  # 'backfill' | 'today'
    start: date | None = None
    end: date | None = None


class PriceAgent(BaseAgent):
    name: ClassVar[str] = "prices"

    def __init__(
        self,
        *,
        client: NSEBhavcopyClient | None = None,
        request: PriceRequest | None = None,
    ) -> None:
        super().__init__()
        self.client = client or NSEBhavcopyClient()
        self._request = request

    # ----- public modes -----
    async def backfill(
        self,
        *,
        start: date,
        end: date,
        dry_run: bool = False,
        ingestion_run_id: int | None = None,
        cache_ttl: int = 3600,
        max_concurrency: int = 10,
    ) -> PriceResult:
        async with SessionLocal() as session:
            open_dates = await calendar_repo.get_open_dates(session, start, end)
            present = await prices_repo.get_dates_present(session, start, end)
            known = await self._load_known_isins(session)

        missing = [d for d in open_dates if d not in present]
        log.info(
            "prices.backfill.plan",
            start=str(start),
            end=str(end),
            open_days=len(open_dates),
            present=len(present),
            missing=len(missing),
            dry_run=dry_run,
        )

        sem = asyncio.Semaphore(max_concurrency)
        fetched = await asyncio.gather(
            *(self._fetch_one(d, known, sem, cache_ttl) for d in missing)
        )

        result = PriceResult(
            open_days=len(open_dates),
            present_days=len(present),
            dates_attempted=len(missing),
            missing=missing,
        )
        good_rows: list[BhavRow] = []
        for d, rows, warns, parsed, ok in fetched:
            result.warnings.extend(warns)
            if not ok:
                result.dates_failed += 1
                result.failed_dates.append(d)
                continue
            result.dates_succeeded += 1
            good_rows.extend(rows)
            warned = sum(1 for w in warns if w.code in _QUALITY_CODES)
            result.rows_warned += warned
            result.rows_skipped += parsed - len(rows) - warned

        result.rows_ready = len(good_rows)

        if not dry_run and good_rows:
            if ingestion_run_id is None:
                raise ValueError("ingestion_run_id required for a non-dry-run insert")
            async with SessionLocal() as session:
                result.rows_inserted = await prices_repo.bulk_insert(
                    session, good_rows, ingestion_run_id=ingestion_run_id
                )
                await self._write_warnings(session, result.warnings, ingestion_run_id)
                await session.commit()

        log.info("prices.backfill.done", **result.counts())
        return result

    async def fetch_today(
        self,
        *,
        dry_run: bool = False,
        ingestion_run_id: int | None = None,
        cache_ttl: int = 3600,
    ) -> PriceResult:
        today = today_ist()
        async with SessionLocal() as session:
            open_dates = await calendar_repo.get_open_dates(session, today, today)
        if not open_dates:
            log.info("prices.today.not_trading_day", date=str(today))
            return PriceResult(note=f"{today} is not an NSE trading day")

        now = datetime.now(IST)
        if (now.hour, now.minute) < (_PUBLISH_HOUR, _PUBLISH_MINUTE):
            log.warning("prices.today.not_published_yet", now=now.isoformat())
            return PriceResult(
                note="bhavcopy not yet published (before 18:30 IST) — try later"
            )

        return await self.backfill(
            start=today,
            end=today,
            dry_run=dry_run,
            ingestion_run_id=ingestion_run_id,
            cache_ttl=cache_ttl,
        )

    # ----- per-date download + filter -----
    async def _fetch_one(
        self,
        d: date,
        known: set[str],
        sem: asyncio.Semaphore,
        cache_ttl: int,
    ) -> tuple[date, list[BhavRow], list[FilterWarning], int, bool]:
        async with sem:
            try:
                rows, _meta = await self.client.fetch_for_date(d, cache_ttl=cache_ttl)
            except DataSourceError as exc:
                log.warning("prices.bhavcopy.missing", date=str(d), error=str(exc))
                return (
                    d,
                    [],
                    [FilterWarning("BHAVCOPY_MISSING", "", d, str(exc))],
                    0,
                    False,
                )
        good, warns = filter_rows(rows, known)
        return d, good, warns, len(rows), True

    # ----- helpers -----
    async def _load_known_isins(self, session: AsyncSession) -> set[str]:
        rows = (await session.execute(select(Stock.isin))).scalars().all()
        return set(rows)

    @staticmethod
    async def _write_warnings(
        session: AsyncSession, warnings: list[FilterWarning], run_pk: int
    ) -> None:
        for w in warnings:
            session.add(
                DataQualityLog(
                    ingestion_run_id=run_pk,
                    isin=w.isin or None,
                    severity="warn",
                    code=w.code,
                    message=w.message,
                    context={
                        "trade_date": w.trade_date.isoformat() if w.trade_date else None
                    },
                )
            )

    @staticmethod
    async def _lookup_run_pk(session: AsyncSession, run_id: uuid.UUID) -> int:
        stmt = select(DataIngestionRun.id).where(DataIngestionRun.run_id == run_id)
        return (await session.execute(stmt)).scalar_one()

    # ----- base.run integration (real apply, with run-lifecycle bookkeeping) -----
    async def _execute(self, ctx: RunContext) -> AgentResult:
        if self._request is None:
            raise ValueError("PriceAgent requires a PriceRequest for run()")
        async with SessionLocal() as session:
            run_pk = await self._lookup_run_pk(session, ctx.run_id)

        if self._request.mode == "backfill":
            assert self._request.start is not None and self._request.end is not None
            res = await self.backfill(
                start=self._request.start,
                end=self._request.end,
                dry_run=False,
                ingestion_run_id=run_pk,
            )
        else:
            res = await self.fetch_today(dry_run=False, ingestion_run_id=run_pk)

        warnings = ([res.note] if res.note else []) + [
            f"{w.code}:{w.isin or '-'}" for w in res.warnings[:50]
        ]
        return AgentResult(
            status="partial" if res.dates_failed else "success",
            rows_inserted=res.rows_inserted,
            warnings=warnings,
            metrics={k: float(v) for k, v in res.counts().items()},
        )

    async def health(self) -> HealthStatus:
        ok = await ping_db()
        return HealthStatus(healthy=ok, detail="db reachable" if ok else "db down")
