"""Earnings-calendar Agent (Build E) — file-ingest of a Moneycontrol results-calendar
export (operator-downloaded; no website scraping — CLAUDE.md §2 rule 5 allow-list).

`parse_earnings_csv` is pure (synthetic-testable). The agent resolves company name
-> ISIN via pg_trgm `similarity()` (threshold 0.3) and upserts into
`earnings_calendar`. A bad/dateless row is skipped (logged), never raised.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

import structlog

log = structlog.get_logger()

SOURCE = "moneycontrol"
_SIM_THRESHOLD = 0.30
_DATE_FORMATS = (
    "%d-%b-%Y",
    "%d %b %Y",
    "%d-%B-%Y",
    "%d %B %Y",
    "%Y-%m-%d",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d/%m/%Y",
)


@dataclass(frozen=True)
class EarningsRaw:
    company_name: str
    result_date: date
    quarter: str | None


@dataclass
class EarningsResult:
    parsed: int = 0
    matched: int = 0
    unmatched: int = 0
    upserted: int = 0
    sample: list[tuple[str, str]] = field(default_factory=list)


def _match(norm: dict[str, str], *, include: tuple[str, ...]) -> str | None:
    for key, val in norm.items():
        if all(s in key for s in include):
            return val
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    s = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_earnings_csv(content: str) -> list[EarningsRaw]:
    """Parse a Moneycontrol results-calendar CSV (tolerant header matching).

    Expected columns: Company name, result date, (optional) quarter. Rows with no
    company or an unparseable date are skipped (logged), never raised.
    """
    out: list[EarningsRaw] = []
    for rec in csv.DictReader(io.StringIO(content)):
        norm = {(k or "").strip().upper(): (v or "").strip() for k, v in rec.items()}
        name = (
            _match(norm, include=("COMPANY",))
            or _match(norm, include=("SECURITY",))
            or norm.get("SYMBOL")
        )
        if not name:
            continue
        result_date = _parse_date(
            _match(norm, include=("RESULT", "DATE")) or _match(norm, include=("DATE",))
        )
        if result_date is None:
            log.warning("earnings.parse.bad_date", company=name)
            continue
        out.append(
            EarningsRaw(
                company_name=name,
                result_date=result_date,
                quarter=(
                    _match(norm, include=("QUARTER",)) or _match(norm, include=("QTR",))
                ),
            )
        )
    return out


class EarningsAgent:
    name = "earnings"

    async def ingest_from_file(
        self, *, path: str | None, dry_run: bool = False
    ) -> EarningsResult:
        """Parse a results-calendar CSV, match names -> ISIN (pg_trgm), upsert."""
        text = await self._read(path)
        if text is None:
            return EarningsResult()
        try:
            raws = parse_earnings_csv(text)
        except ValueError as exc:
            log.warning("earnings.parse.failed", path=path, error=str(exc))
            return EarningsResult()

        from backend.db.repositories import earnings as earnings_repo
        from backend.db.session import SessionLocal

        result = EarningsResult(parsed=len(raws))
        rows: list[dict[str, object]] = []
        async with SessionLocal() as session:
            for r in raws:
                isin = await self._match_isin(session, r.company_name)
                if isin is None:
                    result.unmatched += 1
                    log.warning("earnings.match.miss", company=r.company_name)
                    continue
                rows.append(
                    {
                        "isin": isin,
                        "result_date": r.result_date,
                        "quarter": r.quarter,
                        "status": "upcoming",
                        "source": SOURCE,
                    }
                )
                if len(result.sample) < 10:
                    result.sample.append((isin, r.company_name))
            result.matched = len(rows)
            if not dry_run and rows:
                result.upserted = await earnings_repo.bulk_upsert(session, rows)
                await session.commit()

        log.info(
            "earnings.ingest.done",
            parsed=result.parsed,
            matched=result.matched,
            unmatched=result.unmatched,
            upserted=result.upserted,
            dry_run=dry_run,
        )
        return result

    @staticmethod
    async def _match_isin(session: object, name: str) -> str | None:
        from sqlalchemy import text as sa_text
        from sqlalchemy.ext.asyncio import AsyncSession

        assert isinstance(session, AsyncSession)
        res = await session.execute(
            sa_text(
                "SELECT isin FROM stocks "
                "WHERE delisted_on IS NULL AND similarity(company_name, :n) > :thr "
                "ORDER BY similarity(company_name, :n) DESC LIMIT 1"
            ),
            {"n": name, "thr": float(_SIM_THRESHOLD)},
        )
        row = res.first()
        return row[0] if row else None

    @staticmethod
    async def _read(path: str | None) -> str | None:
        import asyncio
        from pathlib import Path

        if not path:
            log.warning("earnings.read.no_path")
            return None

        def _sync() -> str | None:
            p = Path(path)
            if not p.exists():
                log.warning("earnings.read.missing", path=path)
                return None
            try:
                return p.read_text(encoding="utf-8")
            except OSError as exc:
                log.warning("earnings.read.failed", path=path, error=str(exc))
                return None

        return await asyncio.to_thread(_sync)
