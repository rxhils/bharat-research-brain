"""Back-adjustment engine for split/bonus + dividend corporate actions (2.1).

Pure logic. `adjust_series` takes a stock's raw OHLCV bars and its corporate
actions and returns the back-adjusted series, applying actions most-recent-
first (CLAUDE.md / spec):

  - split/bonus on ex_date D (factor f = numerator/denominator): every bar
    strictly BEFORE D has its prices divided by f and volume multiplied by f.
    f>1 is a forward split/bonus; f<1 a reverse split.
  - dividend of X on ex_date D: every bar strictly BEFORE D has X subtracted
    from its prices (volume untouched). Subtractive method per spec.

`adj_factor` records the cumulative split divisor applied to each bar (for
reference / debugging); dividend effects are not captured in it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

_Q = Decimal("0.0001")


@dataclass(frozen=True)
class RawBar:
    trade_date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal | None
    volume: int | None


@dataclass(frozen=True)
class Action:
    ex_date: date
    action_type: str
    ratio_numerator: Decimal | None
    ratio_denominator: Decimal | None
    amount_inr: Decimal | None


@dataclass(frozen=True)
class AdjBar:
    trade_date: date
    adj_open: Decimal | None
    adj_high: Decimal | None
    adj_low: Decimal | None
    adj_close: Decimal | None
    adj_volume: int | None
    adj_factor: Decimal


def _q(v: Decimal | None) -> Decimal | None:
    return v.quantize(_Q) if v is not None else None


def adjust_series(bars: list[RawBar], actions: list[Action]) -> list[AdjBar]:
    """Back-adjust `bars` for `actions`. See module docstring. Pure."""
    actions_desc = sorted(actions, key=lambda a: a.ex_date, reverse=True)
    out: list[AdjBar] = []

    for bar in bars:
        o, h, low_, c = bar.open, bar.high, bar.low, bar.close
        vol = bar.volume
        factor = Decimal(1)

        for a in actions_desc:
            if a.ex_date <= bar.trade_date:
                continue  # only actions AFTER this bar adjust it
            if a.action_type == "split":
                if a.ratio_numerator is None or not a.ratio_denominator:
                    continue
                f = a.ratio_numerator / a.ratio_denominator
                if f == 0:
                    continue
                o = o / f if o is not None else None
                h = h / f if h is not None else None
                low_ = low_ / f if low_ is not None else None
                c = c / f if c is not None else None
                vol = int(vol * f) if vol is not None else None
                factor *= f
            elif a.action_type == "dividend":
                amt = a.amount_inr
                if amt is None:
                    continue
                o = o - amt if o is not None else None
                h = h - amt if h is not None else None
                low_ = low_ - amt if low_ is not None else None
                c = c - amt if c is not None else None
            # other action types (bonus/rights/etc.) are not adjusted here.

        out.append(
            AdjBar(
                trade_date=bar.trade_date,
                adj_open=_q(o),
                adj_high=_q(h),
                adj_low=_q(low_),
                adj_close=_q(c),
                adj_volume=vol,
                adj_factor=factor,
            )
        )
    return out
