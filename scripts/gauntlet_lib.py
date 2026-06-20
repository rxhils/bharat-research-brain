"""Shared Phase-2 gauntlet harness (read-only) — one source of truth for the 8
walk-forward windows, the frozen-F+ config, and the metric extraction used by
Tests 1-5. Importing this keeps every test byte-identical on windows + control so
the only thing that varies is the experimental knob under test.

Frozen F+ (control) == commit 6417a74 config: top_n 25, hold/rebalance 63d,
quality_gate, graded_exposure, hold_buffer_rank 40, max_per_sector 4,
turnover low, weekly (5d) exposure check, 15% breakdown exit. momentum_mode off.

CAVEAT (applies to every absolute number this prints): the `stocks` universe has
NO delisted rows (507 active, 0 delisted) -> SURVIVORSHIP BIAS. Absolute returns
are optimistic; only the DELTA vs frozen F+ on the SAME universe is fully fair.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.backtest.engine import BacktestConfig, max_drawdown_pct  # noqa: F401

_CAP = Decimal("1000000")
_FLOOR2 = date(2021, 5, 26)  # native-only warmup, off the yfinance/native seam

# The 8 walk-forward windows (must match ingest_gold.py + diag_fplus.py).
# Era 1 = 2017-2020 (covid era, yfinance data). Era 2 = 2021-2026 (native data).
ERA1 = [
    ("E1W1 2017-18", date(2017, 1, 16), date(2018, 12, 31), None),
    ("E1W2 2017-19", date(2017, 6, 1), date(2019, 6, 1), None),
    ("E1W3 2018-cov", date(2018, 1, 1), date(2020, 6, 30), None),  # COVID
    ("E1W4 2018-20", date(2018, 6, 1), date(2020, 12, 31), None),
]
ERA2 = [
    ("E2W1 2021-23", date(2021, 6, 1), date(2023, 6, 1), _FLOOR2),
    ("E2W2 2022-24", date(2022, 6, 1), date(2024, 6, 1), _FLOOR2),
    ("E2W3 2023-25", date(2023, 6, 1), date(2025, 6, 1), _FLOOR2),
    ("E2W4 2024-26", date(2024, 1, 1), date(2026, 5, 26), _FLOOR2),
]
WINDOWS = ERA1 + ERA2
COVID_LABEL = "E1W3 2018-cov"
FULL1 = ("FULL 2017-20", date(2017, 1, 16), date(2020, 12, 31), None)
FULL2 = ("FULL 2021-26", date(2021, 6, 1), date(2026, 5, 26), _FLOOR2)
# The "₹10L 2021-26" comparison the operator wants on every test.
COMPARE = FULL2
# Jan-Jun 2020 covid crash window for the explicit peak->trough drawdown.
_COVID_CRASH = (date(2020, 1, 1), date(2020, 6, 30))


def cfg_fplus(s: date, e: date, floor: date | None, **overrides) -> BacktestConfig:
    """Frozen F+ control config; **overrides flips ONE experimental knob per test."""
    base = dict(
        start_date=s, end_date=e, top_n=25, hold_days=63, rebalance_every=63,
        starting_capital=_CAP, min_score=Decimal("0"), use_full_composite=True,
        benchmark_weighting="equal", apply_breadth_filter=False,
        quality_gate=True, graded_exposure=True, hold_buffer_rank=40,
        max_per_sector=4, turnover_mode="low", exposure_check_days=5,
        breakdown_exit_pct=Decimal("0.15"), history_floor=floor,
    )
    base.update(overrides)
    return BacktestConfig(**base)


@dataclass
class Metrics:
    label: str
    total_return_pct: Decimal
    cagr_pct: Decimal
    max_dd_pct: Decimal
    sharpe: Decimal | None
    trades: int
    tri_return_pct: Decimal | None
    alpha_vs_tri_pct: Decimal | None
    end_value: Decimal
    covid_crash_dd_pct: Decimal | None  # peak->trough over Jan-Jun 2020 (None if N/A)


def covid_crash_drawdown(equity_curve: list[tuple[date, Decimal]]) -> Decimal | None:
    """Peak-to-trough drawdown of the blended equity restricted to the Jan-Jun 2020
    covid crash. None if the curve doesn't span the crash (Era-2 windows). This
    isolates the crash itself, separate from the whole-window maxDD."""
    a, b = _COVID_CRASH
    seg = [(d, v) for d, v in equity_curve if d <= b]
    if not seg or seg[-1][0] < a:
        return None
    crash = [(d, v) for d, v in equity_curve if a <= d <= b]
    if not crash:
        return None
    peak = max((v for d, v in equity_curve if d <= crash[0][0]), default=crash[0][1])
    trough = min(v for _d, v in crash)
    if peak <= 0:
        return None
    return ((peak - trough) / peak * 100).quantize(Decimal("0.01"))


def metrics(label: str, r) -> Metrics:  # noqa: ANN001
    return Metrics(
        label=label,
        total_return_pct=r.total_return_pct,
        cagr_pct=r.cagr_pct,
        max_dd_pct=r.max_drawdown_pct,
        sharpe=r.sharpe,
        trades=r.total_trades,
        tri_return_pct=r.nifty500_tri_return_pct,
        alpha_vs_tri_pct=r.alpha_vs_nifty500_tri_pct,
        end_value=r.end_value,
        covid_crash_dd_pct=covid_crash_drawdown(r.equity_curve),
    )


HDR = (f"{'window':<15}{'tot%':>9}{'CAGR':>7}{'Shrp':>6}{'maxDD%':>8}"
       f"{'covDD%':>8}{'trd':>5}{'N500%':>9}{'aTRI':>8}")


def row(m: Metrics) -> str:
    cov = "-" if m.covid_crash_dd_pct is None else f"{m.covid_crash_dd_pct}"
    tri = "-" if m.tri_return_pct is None else f"{m.tri_return_pct}"
    al = "-" if m.alpha_vs_tri_pct is None else f"{m.alpha_vs_tri_pct}"
    sh = "-" if m.sharpe is None else f"{m.sharpe}"
    return (f"{m.label:<15}{str(m.total_return_pct):>9}{str(m.cagr_pct):>7}"
            f"{sh:>6}{str(m.max_dd_pct):>8}{cov:>8}{m.trades:>5}{tri:>9}{al:>8}")


def delta_row(label: str, m: Metrics, ctrl: Metrics) -> str:
    dret = (m.total_return_pct - ctrl.total_return_pct).quantize(Decimal("0.01"))
    ddd = (m.max_dd_pct - ctrl.max_dd_pct).quantize(Decimal("0.01"))
    return (f"{label:<15} Δret {str(dret):>8}   Δmaxdd {str(ddd):>8}"
            f"   (Δmaxdd<0 = safer)")
