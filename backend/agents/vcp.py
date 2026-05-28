"""VCP Agent — Minervini Volatility Contraction Pattern screener (Chunk 4.10).

Scoring is PURE: every `score_*` / `find_*` / `detect_*` / `compute_*` function
takes a PriceSeries (list of `(date, high, low, close, volume)` tuples, oldest
first) and returns scores with no I/O. Only `VcpAgent.run_all` touches the DB.

The composite `vcp_score` (0-100) blends five components; `vcp_detected` is the
hard gate (trend template satisfied + >=2 contractions + composite >= 40). No
LLMs, no advisory language — this is a screen, not a signal.

ADJUSTMENT NOTE: the series is the split/bonus-adjusted OHLCV
(`prices_eod_adjusted`, incl. `adj_volume`) per CLAUDE.md §4 — technicals must
run on adjusted prices or breakouts/contractions are fake.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

import structlog

log = structlog.get_logger()

SOURCE = "vcp_agent"

# (date, high, low, close, volume) oldest first.
PriceRow = tuple[date, float, float, float, float]

MIN_ROWS = 100  # below this, no screen — log + emit a not-detected row.
_LOOKBACK = 60  # bars for contractions / pivot.
_RS_LOOKBACK = 63  # ~3 trading months for relative strength.
_Q2 = Decimal("0.01")

# Contraction tuning (real Indian EOD data, not clean zigzags):
_PIVOT_WIDTH = 2  # 5-bar pivot: strict extreme vs the 2 bars on each side.
_MIN_DEPTH = 0.03  # ignore swings shallower than 3% — pure noise, not a pullback.
_DEPTH_TOLERANCE = 1.20  # a leg may be up to 20% DEEPER than the previous one.


def _dec(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_Q2, rounding=ROUND_HALF_EVEN)


def _ema(values: list[float], period: int) -> float | None:
    """EMA seeded with the SMA of the first `period` values. None if too short."""
    if len(values) < period:
        return None
    seed = sum(values[:period]) / period
    ema = seed
    alpha = 2.0 / (period + 1)
    for v in values[period:]:
        ema = alpha * v + (1.0 - alpha) * ema
    return ema


# --- pure scoring -----------------------------------------------------------


def score_trend_template(prices: list[PriceRow]) -> Decimal:
    """Minervini trend template, 4 conditions x 25 pts (0/25/50/75/100):

    1. close > EMA50   2. close > EMA200
    3. EMA50 > EMA200  4. close > 52-week low x 1.25
    """
    closes = [p[3] for p in prices]
    if len(closes) < 50:
        return Decimal(0)
    close = closes[-1]
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)
    low_52w = min(closes[-252:])
    conditions = (
        ema50 is not None and close > ema50,
        ema200 is not None and close > ema200,
        ema50 is not None and ema200 is not None and ema50 > ema200,
        close > low_52w * 1.25,
    )
    return Decimal(25 * sum(1 for c in conditions if c))


def _swing_pivots(highs: list[float], lows: list[float]) -> list[tuple[str, float]]:
    """5-bar swing pivots: a bar is a swing high (low) only if its high (low) is
    a STRICT extreme versus the `_PIVOT_WIDTH` bars on each side. The wider
    window smooths the intrabar chop that a 3-bar pivot mistakes for structure.
    """
    w = _PIVOT_WIDTH
    swings: list[tuple[str, float]] = []
    for i in range(w, len(highs) - w):
        h, lo = highs[i], lows[i]
        if all(h > highs[i + d] for d in range(-w, w + 1) if d != 0):
            swings.append(("high", h))
        elif all(lo < lows[i + d] for d in range(-w, w + 1) if d != 0):
            swings.append(("low", lo))
    return swings


def find_contractions(prices: list[PriceRow]) -> tuple[int, Decimal]:
    """Count sequential, tightening peak->trough contractions in the last 60 bars.

    A contraction is a 5-bar swing high paired with the following 5-bar swing
    low; depth = (high - low) / high. Swings shallower than `_MIN_DEPTH` (3%)
    are dropped as noise. The sequence is a valid contracting base only if it
    tightens overall (last depth < first) and no leg is more than
    `_DEPTH_TOLERANCE` (20%) deeper than the one before it — real data ticks up
    a little between legs, so a strict monotonic rule never fires on it.
    Quality maps count -> {0:0, 1:25, 2:50, 3:75, 4+:100}.
    """
    window = prices[-_LOOKBACK:]
    highs = [p[1] for p in window]
    lows = [p[2] for p in window]

    swings = _swing_pivots(highs, lows)

    depths: list[float] = []
    i = 0
    while i < len(swings) - 1:
        if swings[i][0] == "high" and swings[i + 1][0] == "low":
            hi, lo = swings[i][1], swings[i + 1][1]
            if hi > 0:
                depth = (hi - lo) / hi
                if depth >= _MIN_DEPTH:
                    depths.append(depth)
            i += 2
        else:
            i += 1

    if not depths:
        return 0, Decimal(0)
    within_tolerance = all(
        depths[j] <= depths[j - 1] * _DEPTH_TOLERANCE for j in range(1, len(depths))
    )
    contracts_overall = len(depths) == 1 or depths[-1] < depths[0]
    valid = within_tolerance and contracts_overall
    count = len(depths) if valid else 0
    quality = 100 if count >= 4 else {0: 0, 1: 25, 2: 50, 3: 75}[count]
    return count, Decimal(quality)


def detect_volume_dryup(prices: list[PriceRow]) -> bool:
    """True if the last 10 bars' avg volume < 70% of the 50-day avg AND the last
    10 bars are trending down (last-5 avg < first-5 avg of those 10)."""
    vols = [p[4] for p in prices]
    if len(vols) < 50:
        return False
    avg50 = sum(vols[-50:]) / 50
    last10 = vols[-10:]
    if sum(last10) / 10 >= avg50 * 0.70:
        return False
    return sum(last10[5:]) / 5 < sum(last10[:5]) / 5


def score_pivot_proximity(prices: list[PriceRow]) -> Decimal:
    """How close the current close is to the 60-bar pivot (highest close).

    <=2%->100, <=5%->80, <=10%->50, <=20%->25, else 0.
    """
    closes = [p[3] for p in prices[-_LOOKBACK:]]
    if not closes:
        return Decimal(0)
    pivot = max(closes)
    if pivot <= 0:
        return Decimal(0)
    prox = (pivot - closes[-1]) / pivot * 100
    if prox <= 2:
        return Decimal(100)
    if prox <= 5:
        return Decimal(80)
    if prox <= 10:
        return Decimal(50)
    if prox <= 20:
        return Decimal(25)
    return Decimal(0)


def score_relative_strength(
    stock_prices: list[PriceRow], nifty_prices: list[PriceRow]
) -> Decimal:
    """Stock's 63-bar return minus the market's, scored 0-100.

    rs > +0.15->100, > +0.08->75, > 0->50, > -0.08->25, else 0.
    """
    s = [p[3] for p in stock_prices][-_RS_LOOKBACK:]
    n = [p[3] for p in nifty_prices][-_RS_LOOKBACK:]
    if len(s) < 2 or len(n) < 2 or s[0] == 0 or n[0] == 0:
        return Decimal(0)
    rs = (s[-1] - s[0]) / s[0] - (n[-1] - n[0]) / n[0]
    if rs > 0.15:
        return Decimal(100)
    if rs > 0.08:
        return Decimal(75)
    if rs > 0:
        return Decimal(50)
    if rs > -0.08:
        return Decimal(25)
    return Decimal(0)


def compute_vcp_score(
    *,
    trend: Decimal,
    contractions: int,
    quality: Decimal,
    volume_dryup: bool,
    proximity: Decimal,
    rs: Decimal,
) -> tuple[bool, Decimal]:
    """Weighted composite + the detection gate.

    composite = trend*0.25 + quality*0.25 + dryup(100/0)*0.20
              + proximity*0.15 + rs*0.15
    detected  = trend >= 75 AND contractions >= 2 AND composite >= 40
    """
    dryup_pts = Decimal(100) if volume_dryup else Decimal(0)
    composite = (
        trend * Decimal("0.25")
        + quality * Decimal("0.25")
        + dryup_pts * Decimal("0.20")
        + proximity * Decimal("0.15")
        + rs * Decimal("0.15")
    ).quantize(_Q2, rounding=ROUND_HALF_EVEN)
    detected = trend >= 75 and contractions >= 2 and composite >= 40
    return detected, composite


# --- agent ------------------------------------------------------------------


@dataclass
class VcpRunResult:
    stocks_processed: int = 0
    rows_upserted: int = 0
    detected: int = 0
    skipped_no_data: int = 0


class VcpAgent:
    """Screens every active stock and upserts one `stock_vcp_signals` row each."""

    async def run_all(self, *, dry_run: bool = False) -> VcpRunResult:
        from sqlalchemy import select

        from backend.db.models import Stock
        from backend.db.repositories import vcp as vcp_repo
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            isins = list(
                (
                    await session.execute(
                        select(Stock.isin)
                        .where(Stock.delisted_on.is_(None))
                        .order_by(Stock.isin)
                    )
                )
                .scalars()
                .all()
            )
            nifty = await vcp_repo.load_market_proxy(session)

        if not nifty:
            log.warning("vcp.no_market_proxy")  # RS scores fall back to 0.

        res = VcpRunResult()
        today = today_ist()
        rows: list[vcp_repo.VcpRow] = []
        for isin in isins:
            async with SessionLocal() as session:
                series = await vcp_repo.load_series(session, isin)
            if len(series) < MIN_ROWS:
                res.skipped_no_data += 1
                rows.append(
                    vcp_repo.VcpRow(
                        isin=isin,
                        computed_date=today,
                        vcp_detected=False,
                        contraction_count=None,
                        contraction_quality=None,
                        volume_dryup=None,
                        trend_score=None,
                        pivot_proximity=None,
                        relative_strength=None,
                        vcp_score=None,
                    )
                )
                continue

            trend = score_trend_template(series)
            count, quality = find_contractions(series)
            dryup = detect_volume_dryup(series)
            proximity = score_pivot_proximity(series)
            rs = (
                score_relative_strength(series, nifty) if nifty else Decimal(0)
            )
            detected, vcp_score = compute_vcp_score(
                trend=trend,
                contractions=count,
                quality=quality,
                volume_dryup=dryup,
                proximity=proximity,
                rs=rs,
            )
            rows.append(
                vcp_repo.VcpRow(
                    isin=isin,
                    computed_date=today,
                    vcp_detected=detected,
                    contraction_count=count,
                    contraction_quality=quality,
                    volume_dryup=dryup,
                    trend_score=trend,
                    pivot_proximity=proximity,
                    relative_strength=rs,
                    vcp_score=vcp_score,
                )
            )
            res.stocks_processed += 1
            if detected:
                res.detected += 1
            if res.stocks_processed % 50 == 0:
                log.info(
                    "vcp.progress", processed=res.stocks_processed, total=len(isins)
                )

        if not dry_run and rows:
            async with SessionLocal() as session:
                res.rows_upserted = await vcp_repo.bulk_upsert(session, rows)
                await session.commit()

        log.info(
            "vcp.run_all.done",
            processed=res.stocks_processed,
            upserted=res.rows_upserted,
            detected=res.detected,
            skipped=res.skipped_no_data,
            dry_run=dry_run,
        )
        return res
