"""Data access for the VCP Agent (Chunk 4.10).

Loads the split/bonus-adjusted OHLCV series per stock (and a market proxy for
relative strength), and upserts computed signals into `stock_vcp_signals`
(ON CONFLICT (isin, computed_date) DO UPDATE). Returns plain dataclasses/tuples
so this layer never imports the agent.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PriceEodAdjusted, Stock, VcpSignal

_BATCH = 1000
_SERIES_BARS = 200  # how many recent adjusted bars to load per stock.
_PROXY_TOP_N = 10  # large-caps to equal-weight when there's no Nifty index row.
SOURCE = "vcp_agent"

# (date, high, low, close, volume) oldest first — matches PriceRow in the agent.
PriceRow = tuple[date, float, float, float, float]

# Symbols a real Nifty-50 index row might carry, if one is ever loaded.
_NIFTY_SYMBOLS = ("NIFTY", "NIFTY50", "NIFTY 50", "^NSEI")


@dataclass
class VcpRow:
    """One screener result per (isin, computed_date). Scores are None when the
    stock has too little history to screen."""

    isin: str
    computed_date: date
    vcp_detected: bool
    contraction_count: int | None
    contraction_quality: Decimal | None
    volume_dryup: bool | None
    trend_score: Decimal | None
    pivot_proximity: Decimal | None
    relative_strength: Decimal | None
    vcp_score: Decimal | None


_UPSERT_COLS = (
    "vcp_detected",
    "contraction_count",
    "contraction_quality",
    "volume_dryup",
    "trend_score",
    "pivot_proximity",
    "relative_strength",
    "vcp_score",
)


def _to_payload(r: VcpRow) -> dict[str, object]:
    d = asdict(r)
    d["source"] = SOURCE
    return d


async def bulk_upsert(session: AsyncSession, rows: Sequence[VcpRow]) -> int:
    """Insert/update stock_vcp_signals rows. Returns affected count; caller commits."""
    affected = 0
    payload = [_to_payload(r) for r in rows]
    for i in range(0, len(payload), _BATCH):
        batch = payload[i : i + _BATCH]
        stmt = pg_insert(VcpSignal).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["isin", "computed_date"],
            set_={c: getattr(stmt.excluded, c) for c in _UPSERT_COLS}
            | {"source": stmt.excluded.source, "computed_at": func.now()},
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def fetch_latest(session: AsyncSession) -> dict[str, VcpRow]:
    """Latest VcpRow per isin (DISTINCT ON isin, newest computed_date first)."""
    stmt = (
        select(
            VcpSignal.isin,
            VcpSignal.computed_date,
            VcpSignal.vcp_detected,
            VcpSignal.contraction_count,
            VcpSignal.contraction_quality,
            VcpSignal.volume_dryup,
            VcpSignal.trend_score,
            VcpSignal.pivot_proximity,
            VcpSignal.relative_strength,
            VcpSignal.vcp_score,
        )
        .distinct(VcpSignal.isin)
        .order_by(VcpSignal.isin, VcpSignal.computed_date.desc())
    )
    out: dict[str, VcpRow] = {}
    for row in (await session.execute(stmt)).all():
        out[row[0]] = VcpRow(*row)
    return out


def _series_from_rows(
    raw: Sequence[tuple[date, Decimal | None, Decimal | None, Decimal | None, int | None]],
) -> list[PriceRow]:
    """Adjusted (high, low, close, volume) → float PriceRows, oldest first.

    Bars missing high/low/close are dropped; missing volume becomes 0.0.
    """
    out: list[PriceRow] = []
    for d, h, low, c, v in raw:
        if h is None or low is None or c is None:
            continue
        out.append((d, float(h), float(low), float(c), float(v) if v is not None else 0.0))
    return out


async def load_series(session: AsyncSession, isin: str) -> list[PriceRow]:
    """Last `_SERIES_BARS` adjusted OHLCV bars for one stock, oldest first."""
    stmt = (
        select(
            PriceEodAdjusted.trade_date,
            PriceEodAdjusted.adj_high,
            PriceEodAdjusted.adj_low,
            PriceEodAdjusted.adj_close,
            PriceEodAdjusted.adj_volume,
        )
        .where(PriceEodAdjusted.isin == isin)
        .order_by(PriceEodAdjusted.trade_date.desc())
        .limit(_SERIES_BARS)
    )
    raw = [tuple(r) for r in (await session.execute(stmt)).all()]
    raw.reverse()  # DB gave newest-first; the math wants oldest-first.
    return _series_from_rows(raw)


async def load_market_proxy(session: AsyncSession) -> list[PriceRow]:
    """A Nifty-50 close series for relative strength.

    Prefers a real index row if one exists; otherwise builds an equal-weight
    proxy from the top `_PROXY_TOP_N` large-caps' adjusted closes per date.
    """
    idx_isin = (
        await session.execute(
            select(Stock.isin).where(Stock.nse_symbol.in_(_NIFTY_SYMBOLS))
        )
    ).scalars().first()
    if idx_isin is not None:
        series = await load_series(session, idx_isin)
        if series:
            return series

    top = list(
        (
            await session.execute(
                select(Stock.isin)
                .where(
                    Stock.delisted_on.is_(None),
                    Stock.mcap_inr_cr.is_not(None),
                )
                .order_by(Stock.mcap_inr_cr.desc())
                .limit(_PROXY_TOP_N)
            )
        )
        .scalars()
        .all()
    )
    if not top:
        return []

    stmt = (
        select(
            PriceEodAdjusted.trade_date,
            func.avg(PriceEodAdjusted.adj_close),
        )
        .where(PriceEodAdjusted.isin.in_(top))
        .group_by(PriceEodAdjusted.trade_date)
        .order_by(PriceEodAdjusted.trade_date.desc())
        .limit(_SERIES_BARS)
    )
    rows = (await session.execute(stmt)).all()
    proxy = [
        (d, float(c), float(c), float(c), 0.0)
        for d, c in rows
        if c is not None
    ]
    proxy.reverse()
    return proxy
