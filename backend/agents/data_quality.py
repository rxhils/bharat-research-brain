"""Data Quality Agent — validates prices_eod + stocks after ingestion.

Five checks, each emitting at most ONE finding per ISIN (counts + samples in
context) so data_quality_log can't flood:
  1. PRICE_GAP          (warn)  — internal missing trading days
  2. OHLC_VIOLATION     (error) — low>high / close>high / close<low
  3. ZERO_NEGATIVE_PRICE(error) — any of o/h/l/c <= 0
  4. VOLUME_ZERO        (warn)  — volume = 0 on a present trading day
  5. STALE_UNIVERSE     (warn)  — no price row in >= 30 calendar days

The detection predicates / gap finder / staleness rule / finding builders are
pure (unit tested). The agent fetches via repos, runs the checks, and writes
findings unless dry_run.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401  (type clarity)

from backend.agents.base import AgentResult, BaseAgent, HealthStatus, RunContext
from backend.db.models import DataIngestionRun
from backend.db.repositories import calendar as calendar_repo
from backend.db.repositories import data_quality as dq_repo
from backend.db.repositories._helpers import today_ist
from backend.db.session import SessionLocal, ping_db

log = structlog.get_logger()

_SAMPLE = 20
STALE_THRESHOLD_DAYS = 30


@dataclass(frozen=True)
class Finding:
    severity: str  # 'warn' | 'error'
    code: str
    isin: str | None
    message: str
    context: dict[str, Any]


@dataclass
class QualityReport:
    findings: list[Finding] = field(default_factory=list)

    def by_code(self) -> dict[str, int]:
        return dict(Counter(f.code for f in self.findings))

    def by_severity(self) -> dict[str, int]:
        return dict(Counter(f.severity for f in self.findings))


# ---------------------------------------------------------------------------
# Pure detection
# ---------------------------------------------------------------------------
def find_price_gaps(open_dates: Sequence[date], present: set[date]) -> list[date]:
    """Internal missing trading days within [min(present), max(present)].

    Excludes pre-listing (before first row) and trailing absence (after last
    row — that is the staleness check's job).
    """
    if not present:
        return []
    lo, hi = min(present), max(present)
    return sorted(d for d in open_dates if lo <= d <= hi and d not in present)


def is_stale(
    last_date: date | None, reference: date, threshold_days: int = STALE_THRESHOLD_DAYS
) -> bool:
    if last_date is None:
        return True
    return (reference - last_date).days >= threshold_days


def is_ohlc_violation(
    open_: Decimal | None,
    high: Decimal | None,
    low: Decimal | None,
    close: Decimal | None,
) -> bool:
    if high is None or low is None:
        return False
    if low > high:
        return True
    return close is not None and (close > high or close < low)


def is_nonpositive(
    open_: Decimal | None,
    high: Decimal | None,
    low: Decimal | None,
    close: Decimal | None,
) -> bool:
    return any(p is not None and p <= 0 for p in (open_, high, low, close))


# ---------------------------------------------------------------------------
# Pure finding builders
# ---------------------------------------------------------------------------
def gap_finding(isin: str, gaps: list[date]) -> Finding:
    g = sorted(gaps)
    return Finding(
        severity="warn",
        code="PRICE_GAP",
        isin=isin,
        message=f"{len(g)} missing trading day(s) in price history",
        context={
            "gap_count": len(g),
            "first_gap": g[0].isoformat() if g else None,
            "last_gap": g[-1].isoformat() if g else None,
            "sample": [d.isoformat() for d in g[:_SAMPLE]],
        },
    )


def ohlc_finding(isin: str, bad_rows: list[dict[str, Any]]) -> Finding:
    return Finding(
        severity="error",
        code="OHLC_VIOLATION",
        isin=isin,
        message=f"{len(bad_rows)} row(s) violate OHLC bounds",
        context={"count": len(bad_rows), "sample": bad_rows[:_SAMPLE]},
    )


def nonpositive_finding(isin: str, bad_rows: list[dict[str, Any]]) -> Finding:
    return Finding(
        severity="error",
        code="ZERO_NEGATIVE_PRICE",
        isin=isin,
        message=f"{len(bad_rows)} row(s) with non-positive price",
        context={"count": len(bad_rows), "sample": bad_rows[:_SAMPLE]},
    )


def volume_finding(isin: str, zero_dates: list[date]) -> Finding:
    z = sorted(zero_dates)
    return Finding(
        severity="warn",
        code="VOLUME_ZERO",
        isin=isin,
        message=f"{len(z)} trading day(s) with zero volume",
        context={"count": len(z), "sample": [d.isoformat() for d in z[:_SAMPLE]]},
    )


def stale_finding(isin: str, last_date: date | None, reference: date) -> Finding:
    days = (reference - last_date).days if last_date else None
    msg = (
        f"no price row in {days} days (last {last_date})"
        if last_date
        else "no price rows at all"
    )
    return Finding(
        severity="warn",
        code="STALE_UNIVERSE",
        isin=isin,
        message=msg,
        context={
            "last_price_date": last_date.isoformat() if last_date else None,
            "days_stale": days,
        },
    )


def _group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault(r["isin"], []).append(r)
    return grouped


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class DataQualityAgent(BaseAgent):
    name: ClassVar[str] = "data_quality"

    def __init__(self, *, stale_threshold_days: int = STALE_THRESHOLD_DAYS) -> None:
        super().__init__()
        self.stale_threshold_days = stale_threshold_days

    async def run_checks(
        self,
        *,
        dry_run: bool = False,
        ingestion_run_id: int | None = None,
        reference: date | None = None,
    ) -> QualityReport:
        ref = reference or today_ist()
        async with SessionLocal() as session:
            active = await dq_repo.fetch_active_isins(session)
            lo, hi = await dq_repo.fetch_price_span(session)
            open_dates = (
                await calendar_repo.get_open_dates(session, lo, hi)
                if lo and hi
                else []
            )
            presence = await dq_repo.fetch_presence(session)
            last_dates = await dq_repo.fetch_last_price_dates(session)
            ohlc_rows = await dq_repo.fetch_ohlc_violations(session)
            nonpos_rows = await dq_repo.fetch_nonpositive(session)
            zero_vol = await dq_repo.fetch_zero_volume(session)

        report = QualityReport()

        # 1. price gaps (active stocks only)
        for isin in active:
            gaps = find_price_gaps(open_dates, presence.get(isin, set()))
            if gaps:
                report.findings.append(gap_finding(isin, gaps))

        # 2 + 3. OHLC / non-positive (grouped per isin)
        for isin, rows in _group_rows(ohlc_rows).items():
            report.findings.append(ohlc_finding(isin, rows))
        for isin, rows in _group_rows(nonpos_rows).items():
            report.findings.append(nonpositive_finding(isin, rows))

        # 4. zero volume (grouped per isin)
        zero_by_isin: dict[str, list[date]] = {}
        for isin, d in zero_vol:
            zero_by_isin.setdefault(isin, []).append(d)
        for isin, dates in zero_by_isin.items():
            report.findings.append(volume_finding(isin, dates))

        # 5. stale universe (active stocks only)
        for isin in active:
            if is_stale(last_dates.get(isin), ref, self.stale_threshold_days):
                report.findings.append(stale_finding(isin, last_dates.get(isin), ref))

        log.info(
            "data_quality.checks.done",
            findings=len(report.findings),
            by_code=report.by_code(),
            active=len(active),
            dry_run=dry_run,
        )

        if not dry_run and report.findings:
            async with SessionLocal() as session:
                await dq_repo.insert_findings(
                    session, report.findings, ingestion_run_id
                )
                await session.commit()

        return report

    async def _execute(self, ctx: RunContext) -> AgentResult:
        async with SessionLocal() as session:
            run_pk = (
                await session.execute(
                    select(DataIngestionRun.id).where(
                        DataIngestionRun.run_id == ctx.run_id
                    )
                )
            ).scalar_one()
        report = await self.run_checks(dry_run=False, ingestion_run_id=run_pk)
        errors = report.by_severity().get("error", 0)
        return AgentResult(
            status="partial" if errors else "success",
            rows_inserted=len(report.findings),
            warnings=[f"{code}={n}" for code, n in sorted(report.by_code().items())],
            metrics={code: float(n) for code, n in report.by_code().items()},
        )

    async def health(self) -> HealthStatus:
        ok = await ping_db()
        return HealthStatus(healthy=ok, detail="db reachable" if ok else "db down")
