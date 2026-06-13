"""India equity-delivery cost model (Chunk 5.2 STEP 1).

Pure math on Decimals. The round-trip cost is the sum of conservative real-world
frictions for a CNC (delivery) trade: discount brokerage, STT, exchange + SEBI
charges, stamp duty (buy side only), GST on (brokerage + exchange fee), and a
slippage assumption applied per side. Returns are expressed as a fraction of
turnover (entry + exit notional), not of capital.
"""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

_Q4 = Decimal("0.0001")

# Per-side rates as fractions (not %). Operator-specified conservative numbers
# from the Chunk 5.2 STEP 1 spec.
_BROKERAGE_PER_SIDE = Decimal("0.0003")  # 0.03% (most discount brokers free; conservative)
_STT_PER_SIDE = Decimal("0.001")  # 0.1% buy + 0.1% sell = 0.2% round trip
_EXCHANGE_PER_SIDE = Decimal("0.0000297")  # 0.00297%
_SEBI_PER_SIDE = Decimal("0.000001")  # 0.0001%
_STAMP_DUTY_BUY = Decimal("0.00015")  # 0.015% buy-side only
_GST = Decimal("0.18")  # 18% on (brokerage + exchange charge)
_SLIPPAGE_PER_SIDE = Decimal("0.001")  # 0.10% per side -> 0.20% round trip


def round_trip_cost_pct() -> Decimal:
    """Total round-trip cost as a Decimal fraction of turnover (e.g. 0.0040 ≈ 0.40%).

    Costs are billed on EACH side of the trade (entry + exit), so per-side rates
    sum to 2× their value except for stamp duty (buy only). GST is charged on the
    cost components per side, also 2× when both sides apply.
    """
    per_side_taxable_for_gst = _BROKERAGE_PER_SIDE + _EXCHANGE_PER_SIDE
    per_side = (
        _BROKERAGE_PER_SIDE
        + _STT_PER_SIDE
        + _EXCHANGE_PER_SIDE
        + _SEBI_PER_SIDE
        + _SLIPPAGE_PER_SIDE
        + per_side_taxable_for_gst * _GST
    )
    round_trip = per_side * 2 + _STAMP_DUTY_BUY
    return round_trip.quantize(_Q4, rounding=ROUND_HALF_EVEN)


def cost_on_notional(position_notional: Decimal) -> Decimal:
    """Round-trip cost (Decimal, rupees) on the capital deployed in one position.

    `round_trip_cost_pct()` already covers BOTH legs (per-side rates are doubled),
    so it is applied ONCE to the position notional (capital deployed), NOT to
    turnover (entry+exit ≈ 2× position) — applying it to turnover double-counts
    every per-side charge (the Chunk 5.2 BUG 2 overcount). Single source of truth
    for both `apply_costs` (share-based) and the engine's capital-weight basket.
    """
    return (position_notional * round_trip_cost_pct()).quantize(
        _Q4, rounding=ROUND_HALF_EVEN
    )


def apply_costs(entry: Decimal, exit_price: Decimal, qty: int) -> Decimal:
    """Net P&L (Decimal, rupees) on a CNC round trip after all frictions.

    cost = round_trip_cost_pct() × position_notional (entry × qty). Returns
    gross_pnl - cost; negative when a tiny move is eaten by costs.
    """
    gross = (exit_price - entry) * Decimal(qty)
    cost = cost_on_notional(entry * Decimal(qty))
    return (gross - cost).quantize(_Q4, rounding=ROUND_HALF_EVEN)
