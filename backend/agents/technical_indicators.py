"""Pure technical-indicator math (Chunk 3.1).

All functions operate on plain float series (the agent converts adjusted-price
Decimals to float — these are analytical signals, not money amounts). Each
returns the latest indicator value, or None when there isn't enough data.
No I/O.
"""
from __future__ import annotations


def rsi(closes: list[float], period: int = 14) -> float | None:
    """Wilder's RSI on `closes`. None if fewer than period+1 points."""
    if len(closes) < period + 1:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def ema_series(values: list[float], period: int) -> list[float]:
    """EMA series seeded with the SMA of the first `period` values. [] if short."""
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out = [seed]
    for v in values[period:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


def ema(values: list[float], period: int) -> float | None:
    series = ema_series(values, period)
    return series[-1] if series else None


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None, float | None]:
    """(macd_line, signal_line, histogram) latest values, or (None, None, None)."""
    if len(closes) < slow + signal:
        return (None, None, None)
    fast_s = ema_series(closes, fast)
    slow_s = ema_series(closes, slow)
    # Align the fast series to the slow one (slow starts `slow-fast` later).
    fast_aligned = fast_s[slow - fast :]
    macd_line = [fast_aligned[i] - slow_s[i] for i in range(len(slow_s))]
    sig_s = ema_series(macd_line, signal)
    if not sig_s:
        return (None, None, None)
    line = macd_line[-1]
    sig = sig_s[-1]
    return (line, sig, line - sig)


def atr(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> float | None:
    """Wilder's ATR. None if fewer than period+1 bars."""
    n = len(closes)
    if n < period + 1 or len(highs) != n or len(lows) != n:
        return None
    trs: list[float] = []
    for i in range(1, n):
        trs.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )
    atr_v = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr_v = (atr_v * (period - 1) + trs[i]) / period
    return atr_v


def avg_last_n(values: list[float | None], n: int) -> float | None:
    """Mean of the last `n` entries, skipping None. None if none are present."""
    window = [v for v in values[-n:] if v is not None]
    return sum(window) / len(window) if window else None


def ema_cross_signal(
    closes: list[float],
    short: int = 20,
    long: int = 200,
    lookback: int = 20,
) -> str:
    """Detect a recent short/long EMA cross.

    'golden' if the short EMA is now above the long AND was at/below it within
    the last `lookback` steps; 'death' for the mirror case; otherwise 'none'
    (including when there isn't enough data for the long EMA).
    """
    short_s = ema_series(closes, short)
    long_s = ema_series(closes, long)
    if not long_s or len(short_s) < len(long_s):
        return "none"
    short_aligned = short_s[len(short_s) - len(long_s) :]
    diff = [short_aligned[i] - long_s[i] for i in range(len(long_s))]
    if len(diff) < 2:
        return "none"
    window = diff[-(lookback + 1) :]
    current = window[-1]
    prior = window[:-1]
    if current > 0 and any(d <= 0 for d in prior):
        return "golden"
    if current < 0 and any(d >= 0 for d in prior):
        return "death"
    return "none"
