"""Named canonical backtest configs (Phase-2 adoption).

Two named strategies, both reproducible and byte-identical run-to-run:

  F+ CLASSIC  — the preserved FALLBACK. Identical to commit 6417a74 behaviour
                (all Phase-2 knobs OFF). Kept available forever so we can always
                fall back. Validated: +81.60% (2021-06..2026-05) / 26.93% COVID maxDD.

  ENHANCED F+ — the NEW canonical/default. F+ CLASSIC + the two changes that PASSED
                the 8-window gauntlet:
                  * vol-adjusted 52-week momentum (momentum_mode="voladj")
                  * idle-cash yield @ 6.5%/yr (cash_yield_annual=0.065)
                Gold (Test 2) and the mid-cap satellite (Test 4) FAILED their
                pre-registered bars and are intentionally EXCLUDED.

Adopting Enhanced F+ = making it the config the reproducibility gate and backtests
treat as canonical. F+ CLASSIC stays a first-class named config (not deleted).

NOTE: the live paper-trading engine (backend/paper/engine.py) still runs F+ CLASSIC
forward; switching the live paper book to Enhanced F+ is a separate, deliberate
migration (it would need momentum + cash-yield wired into the daily paper functions
and a decision about the existing forward track record).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.backtest.engine import BacktestConfig

# Canonical reproducibility/validation window (matches the original frozen-F+ gate).
CANONICAL_START = date(2023, 6, 1)
CANONICAL_END = date(2025, 6, 1)
CANONICAL_FLOOR = date(2021, 5, 26)

# Enhanced-F+ adopted parameters (the two gauntlet winners).
ENHANCED_MOMENTUM_MODE = "voladj"
ENHANCED_CASH_YIELD = Decimal("0.065")

# Shared F+ skeleton — IDENTICAL to scripts.gauntlet_lib.cfg_fplus and the original
# check_backtest_reproducible frozen-F+ config.
_FPLUS_BASE = dict(
    top_n=25, hold_days=63, rebalance_every=63,
    starting_capital=Decimal("1000000"), min_score=Decimal("0"),
    use_full_composite=True, benchmark_weighting="equal", apply_breadth_filter=False,
    quality_gate=True, graded_exposure=True, hold_buffer_rank=40, max_per_sector=4,
    turnover_mode="low", exposure_check_days=5, breakdown_exit_pct=Decimal("0.15"),
)


def fplus_classic(
    start: date = CANONICAL_START,
    end: date = CANONICAL_END,
    history_floor: date | None = CANONICAL_FLOOR,
) -> BacktestConfig:
    """Preserved fallback — frozen F+ (all Phase-2 knobs off; == commit 6417a74)."""
    return BacktestConfig(start_date=start, end_date=end, history_floor=history_floor,
                          **_FPLUS_BASE)


def enhanced_fplus(
    start: date = CANONICAL_START,
    end: date = CANONICAL_END,
    history_floor: date | None = CANONICAL_FLOOR,
) -> BacktestConfig:
    """New canonical engine — F+ + vol-adjusted momentum + cash-yield @ 6.5%/yr."""
    return BacktestConfig(
        start_date=start, end_date=end, history_floor=history_floor,
        momentum_mode=ENHANCED_MOMENTUM_MODE, cash_yield_annual=ENHANCED_CASH_YIELD,
        **_FPLUS_BASE,
    )


# The adopted default. Anything asking "the canonical strategy" gets Enhanced F+.
CANONICAL = enhanced_fplus
