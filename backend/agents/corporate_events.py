"""Corporate Events Agent — splits + dividends from yfinance (Chunk 1.5).

Populates `corporate_actions` (the Phase 2.5 adjusted-price prerequisite).
Source is yfinance (permitted; CLAUDE.md §2 rule 5) — splits + dividends only,
not rights/face-value. The yfinance symbol is derived as `{nse_symbol}.NS`
(CLAUDE.md §4); `stocks.yfinance_symbol` is not relied upon.

Adapted to the existing `corporate_actions` schema: action_type is 'split' or
'dividend' (both allowed by the CHECK); splits store the yfinance factor in
ratio_numerator (denominator 1); dividends store cash/share in amount_inr; the
raw description goes to `description`. There is no ingestion_run_id column on
this table, so inserts carry no run linkage.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import ClassVar

import structlog

from backend.agents.base import AgentResult, BaseAgent, HealthStatus, RunContext
from backend.data_sources.yfinance_client import RawDividend, RawSplit, YFinanceClient
from backend.db.repositories import corporate_actions as ca_repo
from backend.db.repositories._helpers import today_ist
from backend.db.session import SessionLocal, ping_db

log = structlog.get_logger()

SOURCE = "yfinance"


@dataclass(frozen=True)
class CorpActionRow:
    isin: str
    action_type: str
    ex_date: date
    record_date: date | None
    announcement_date: date | None
    ratio_numerator: Decimal | None
    ratio_denominator: Decimal | None
    amount_inr: Decimal | None
    description: str
    source: str


def split_to_row(isin: str, raw: RawSplit, source: str = SOURCE) -> CorpActionRow:
    return CorpActionRow(
        isin=isin,
        action_type="split",
        ex_date=raw.ex_date,
        record_date=None,
        announcement_date=None,
        ratio_numerator=raw.ratio,
        ratio_denominator=Decimal(1),
        amount_inr=None,
        description=f"yfinance split factor {raw.ratio} (new per old)",
        source=source,
    )


def dividend_to_row(
    isin: str, raw: RawDividend, source: str = SOURCE
) -> CorpActionRow:
    return CorpActionRow(
        isin=isin,
        action_type="dividend",
        ex_date=raw.ex_date,
        record_date=None,
        announcement_date=None,
        ratio_numerator=None,
        ratio_denominator=None,
        amount_inr=raw.amount,
        description=f"yfinance dividend {raw.amount}/share",
        source=source,
    )


@dataclass
class EventsResult:
    stocks_attempted: int = 0
    stocks_succeeded: int = 0
    stocks_failed: int = 0
    splits: int = 0
    dividends: int = 0
    rows_ready: int = 0
    rows_inserted: int = 0
    failed_symbols: list[str] = field(default_factory=list)


class CorporateEventsAgent(BaseAgent):
    name: ClassVar[str] = "corporate_events"

    def __init__(self, *, client: YFinanceClient | None = None) -> None:
        super().__init__()
        self.client = client or YFinanceClient()

    async def backfill(
        self,
        *,
        years: int = 5,
        dry_run: bool = False,
        reference: date | None = None,
        max_concurrency: int = 8,
    ) -> EventsResult:
        end = reference or today_ist()
        start = end - timedelta(days=years * 365)
        async with SessionLocal() as session:
            symbols = await self._load_active_symbols(session)

        sem = asyncio.Semaphore(max_concurrency)
        fetched = await asyncio.gather(
            *(self._fetch_one(isin, sym, start, end, sem) for isin, sym in symbols)
        )

        result = EventsResult(stocks_attempted=len(symbols))
        rows: list[CorpActionRow] = []
        for ok, isin, action_rows in fetched:
            if ok:
                result.stocks_succeeded += 1
                rows.extend(action_rows)
            else:
                result.stocks_failed += 1
                result.failed_symbols.append(isin)

        result.splits = sum(1 for r in rows if r.action_type == "split")
        result.dividends = sum(1 for r in rows if r.action_type == "dividend")
        result.rows_ready = len(rows)

        if not dry_run and rows:
            async with SessionLocal() as session:
                result.rows_inserted = await ca_repo.bulk_insert(session, rows)
                await session.commit()

        log.info(
            "corporate_events.backfill.done",
            attempted=result.stocks_attempted,
            succeeded=result.stocks_succeeded,
            failed=result.stocks_failed,
            splits=result.splits,
            dividends=result.dividends,
            inserted=result.rows_inserted,
            dry_run=dry_run,
        )
        return result

    async def _fetch_one(
        self,
        isin: str,
        nse_symbol: str,
        start: date,
        end: date,
        sem: asyncio.Semaphore,
    ) -> tuple[bool, str, list[CorpActionRow]]:
        yf_symbol = f"{nse_symbol}.NS"
        async with sem:
            try:
                splits, dividends = await self.client.fetch_corporate_actions(
                    yf_symbol, start=start, end=end
                )
            except Exception as exc:  # yfinance raises many types; record, continue
                log.warning(
                    "corporate_events.fetch_failed",
                    isin=isin,
                    symbol=yf_symbol,
                    error=str(exc),
                )
                return (False, isin, [])
        rows = [split_to_row(isin, s) for s in splits]
        rows += [dividend_to_row(isin, d) for d in dividends]
        return (True, isin, rows)

    async def _load_active_symbols(self, session: object) -> list[tuple[str, str]]:
        return await ca_repo.fetch_active_symbols(session)  # type: ignore[arg-type]

    async def _execute(self, ctx: RunContext) -> AgentResult:
        res = await self.backfill(dry_run=False)
        return AgentResult(
            status="partial" if res.stocks_failed else "success",
            rows_inserted=res.rows_inserted,
            warnings=(
                [f"{len(res.failed_symbols)} symbols failed to fetch"]
                if res.failed_symbols
                else []
            ),
            metrics={
                "stocks_attempted": float(res.stocks_attempted),
                "stocks_succeeded": float(res.stocks_succeeded),
                "stocks_failed": float(res.stocks_failed),
                "splits": float(res.splits),
                "dividends": float(res.dividends),
                "rows_inserted": float(res.rows_inserted),
            },
        )

    async def health(self) -> HealthStatus:
        ok = await ping_db()
        return HealthStatus(healthy=ok, detail="db reachable" if ok else "db down")
