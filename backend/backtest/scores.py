"""Per-date technical-only score reconstructor (Chunk 5.2 STEP 2b).

mle no-lookahead invariant: every score is computed from `closes`/`volumes` whose
last bar is the simulation date D. The caller MUST pass series ending at D and
nothing past it; the engine cannot tell the difference, so the runner enforces
this with `WHERE trade_date <= :as_of` in the SQL fetch.

Mirrors `score_technical` from `backend.agents.ranking`: RSI zone base + EMA200
position + EMA cross + MACD histogram + 52-week proximity + volume ratio. We do
NOT use any signal that requires data not stored historically per-date
(fundamentals/FII/sector/sentiment/macro/delivery/vcp) — those are simply absent
from this proxy and the result is honestly a technical-only score.
"""
from __future__ import annotations

from decimal import Decimal

from backend.agents.technical_indicators import ema, ema_cross_signal, macd, rsi

# Volume window sizes (sessions).
_AVG_VOL_DAYS = 30
_W52 = 252  # ~52-week trading days


def compute_score_from_history(
    closes: list[float], volumes: list[int] | None = None
) -> Decimal | None:
    """Decimal 0..100 mirroring `score_technical`. None if `closes` is too short.

    Inputs are series ENDING at the simulation date — the caller guarantees no
    future bars are included. The score is the same shape as the live ranking
    technical component so a comparison is meaningful; the absolute numbers will
    differ because the live composite adds fundamentals/macro/sentiment.
    """
    if len(closes) < 26 + 9:  # MACD slow + signal minimum
        return None

    rsi_14 = rsi(closes, 14)
    if rsi_14 is None:
        return None

    # 1) RSI zone base (matches ranking.py score_technical exactly).
    if rsi_14 < 30:
        score = 20.0
    elif rsi_14 < 45:
        score = 40.0
    elif rsi_14 < 55:
        score = 50.0
    elif rsi_14 < 65:
        score = 70.0
    elif rsi_14 < 75:
        score = 60.0
    else:
        score = 30.0

    # 2) EMA200 position (+15 above / -10 below; "at" = ±0.5% band).
    ema200 = ema(closes, 200)
    if ema200 is not None and ema200 > 0:
        last = closes[-1]
        if last > ema200 * 1.005:
            score += 15.0
        elif last < ema200 * 0.995:
            score -= 10.0
        # within 0.5% band -> "at", no change

    # 3) EMA 20/200 cross (+10 golden / -10 death).
    cross = ema_cross_signal(closes, short=20, long=200, lookback=20)
    if cross == "golden":
        score += 10.0
    elif cross == "death":
        score -= 10.0

    # 4) MACD histogram (+5 positive / -5 negative).
    _line, _sig, hist = macd(closes)
    if hist is not None:
        if hist > 0:
            score += 5.0
        elif hist < 0:
            score -= 5.0

    # 5) 52-week proximity (matches ranking.py thresholds).
    window = closes[-_W52:]
    if window:
        hi = max(window)
        lo = min(window)
        last = closes[-1]
        if hi > 0 and last / hi >= 0.97:
            if 55.0 <= rsi_14 <= 70.0:
                score += 8.0  # near high + healthy momentum
            elif rsi_14 > 70.0:
                score += 3.0  # extended but still strong
        if lo > 0 and last / lo <= 1.05:
            score -= 8.0  # near 52w low — value trap

    # 6) Volume trend (current vs 30d average).
    if volumes and len(volumes) >= _AVG_VOL_DAYS + 1:
        current = volumes[-1]
        avg30 = sum(volumes[-(_AVG_VOL_DAYS + 1) : -1]) / _AVG_VOL_DAYS
        if avg30 > 0:
            ratio = current / avg30
            if ratio >= 3:
                score += 10.0
            elif ratio >= 1.5:
                score += 5.0
            elif ratio <= 0.5:
                score -= 5.0

    score = max(0.0, min(100.0, score))
    return Decimal(str(round(score, 2)))
