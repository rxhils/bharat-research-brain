"""Delivery-percentage Agent (Build D) — file-ingest of a Moneycontrol deliverables
export (operator-downloaded; no website scraping — CLAUDE.md §2 rule 5 allow-list).

`parse_delivery_csv` is pure (synthetic-testable). The agent resolves company name
-> ISIN via pg_trgm `similarity()` and upserts into `delivery_signals`. Tolerant
parsing: unknown/blank columns are handled gracefully; a bad row is skipped (logged),
never raised (CLAUDE.md error-handling).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

import structlog

log = structlog.get_logger()

SOURCE = "moneycontrol"
_SIM_THRESHOLD = 0.35


@dataclass(frozen=True)
class DeliveryRaw:
    company_name: str
    delivery_pct: Decimal
    avg_5d_delivery_pct: Decimal | None
    delivery_volume: int | None
    traded_volume: int | None


@dataclass
class DeliveryResult:
    parsed: int = 0
    matched: int = 0
    unmatched: int = 0
    upserted: int = 0
    sample: list[tuple[str, str]] = field(default_factory=list)


def _match(
    norm: dict[str, str], *, include: tuple[str, ...], exclude: tuple[str, ...] = ()
) -> str | None:
    for key, val in norm.items():
        if all(s in key for s in include) and not any(s in key for s in exclude):
            return val
    return None


def _to_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    s = value.replace(",", "").replace("%", "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    s = value.replace(",", "").strip()
    if not s:
        return None
    try:
        return int(Decimal(s))
    except (InvalidOperation, ValueError):
        return None


def parse_delivery_csv(content: str) -> list[DeliveryRaw]:
    """Parse a Moneycontrol deliverables CSV (tolerant header matching).

    Expected columns: Company name, Dely%, 5-Day Avg Del%, Delivery Volumes,
    Traded Volumes. Rows with no company or an unparseable delivery_pct are
    skipped (logged), never raised.
    """
    out: list[DeliveryRaw] = []
    for rec in csv.DictReader(io.StringIO(content)):
        norm = {(k or "").strip().upper(): (v or "").strip() for k, v in rec.items()}
        name = (
            _match(norm, include=("COMPANY",))
            or _match(norm, include=("SECURITY",))
            or norm.get("SYMBOL")
        )
        if not name:
            continue
        delivery_pct = _to_decimal(
            _match(norm, include=("DELY",))
            or _match(norm, include=("DEL", "%"), exclude=("5", "AVG", "DAY"))
        )
        if delivery_pct is None:
            log.warning("delivery.parse.bad_pct", company=name)
            continue
        out.append(
            DeliveryRaw(
                company_name=name,
                delivery_pct=delivery_pct,
                avg_5d_delivery_pct=_to_decimal(
                    _match(norm, include=("AVG",)) or _match(norm, include=("5", "DEL"))
                ),
                delivery_volume=_to_int(_match(norm, include=("DELIVERY", "VOL"))),
                traded_volume=_to_int(_match(norm, include=("TRADED", "VOL"))),
            )
        )
    return out


class DeliveryAgent:
    name = "delivery"

    async def ingest_from_file(
        self, *, path: str | None, trade_date: date | None = None, dry_run: bool = False
    ) -> DeliveryResult:
        """Parse a deliverables CSV, match names -> ISIN (pg_trgm), upsert."""
        text = await self._read(path)
        if text is None:
            return DeliveryResult()
        try:
            raws = parse_delivery_csv(text)
        except ValueError as exc:
            log.warning("delivery.parse.failed", path=path, error=str(exc))
            return DeliveryResult()

        from backend.db.repositories import delivery as delivery_repo
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        td = trade_date or today_ist()
        result = DeliveryResult(parsed=len(raws))
        rows: list[dict[str, object]] = []
        seen: set[str] = set()
        async with SessionLocal() as session:
            for r in raws:
                isin = await self._match_isin(session, r.company_name)
                if isin is None:
                    result.unmatched += 1
                    log.warning("delivery.match.miss", company=r.company_name)
                    continue
                if isin in seen:
                    # Two source names fuzzy-matched to the same ISIN (pg_trgm
                    # false positive, e.g. 'LIC India' -> 3M India). Keep the
                    # first, skip the rest so the ON CONFLICT batch has unique
                    # (isin, trade_date) keys (Postgres rejects a dup PK there).
                    result.unmatched += 1
                    log.warning(
                        "delivery.match.duplicate_isin",
                        isin=isin,
                        company=r.company_name,
                    )
                    continue
                seen.add(isin)
                rows.append(
                    {
                        "isin": isin,
                        "trade_date": td,
                        "delivery_pct": r.delivery_pct,
                        "avg_5d_delivery_pct": r.avg_5d_delivery_pct,
                        "traded_volume": r.traded_volume,
                        "delivery_volume": r.delivery_volume,
                        "source": SOURCE,
                    }
                )
                if len(result.sample) < 10:
                    result.sample.append((isin, r.company_name))
            result.matched = len(rows)
            if not dry_run and rows:
                result.upserted = await delivery_repo.bulk_upsert(session, rows)
                await session.commit()

        log.info(
            "delivery.ingest.done",
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
            log.warning("delivery.read.no_path")
            return None

        def _sync() -> str | None:
            p = Path(path)
            if not p.exists():
                log.warning("delivery.read.missing", path=path)
                return None
            try:
                return p.read_text(encoding="utf-8")
            except OSError as exc:
                log.warning("delivery.read.failed", path=path, error=str(exc))
                return None

        return await asyncio.to_thread(_sync)
