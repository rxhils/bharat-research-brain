"""Pure backtest engine (Chunk 5.2 STEP 2).

No DB, no I/O. `simulate_day` takes pre-fetched scores + entry/exit prices and
returns the day's trades and P&L; the runner is responsible for honoring the
mle-no-lookahead invariant (scores from data <= rebalance_date, exit_prices from
rebalance_date + hold_days). `simulate_day` asserts exit_date > entry_date as a
defensive guard regardless.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

from backend.backtest.cost_model import cost_on_notional

_Q4 = Decimal("0.0001")
_Q2 = Decimal("0.01")


@dataclass(frozen=True)
class BacktestConfig:
    start_date: date
    end_date: date
    top_n: int = 10
    hold_days: int = 5
    rebalance_every: int = 5
    starting_capital: Decimal = Decimal("1000000")
    min_score: Decimal = Decimal("60")


@dataclass(frozen=True)
class Trade:
    isin: str
    entry_date: date
    exit_date: date
    entry_price: Decimal
    exit_price: Decimal
    qty: Decimal  # fractional shares — equal-CAPITAL-weight basket sizing
    gross_pnl: Decimal
    net_pnl: Decimal
    gross_return_pct: Decimal
    score: Decimal


@dataclass
class DayResult:
    date: date
    trades: list[Trade] = field(default_factory=list)
    gross_pnl: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")
    costs_paid: Decimal = Decimal("0")
    positions: list[str] = field(default_factory=list)


def select_top_n(
    scores: dict[str, Decimal], n: int, min_score: Decimal = Decimal("0")
) -> list[str]:
    """ISINs scoring >= min_score, highest first.

    `n <= 0` means NO cap — return every eligible ISIN (the threshold-portfolio
    mode: hold all stocks above the score floor). `n > 0` caps at the top n.
    Deterministic tiebreak by ISIN ascending so the engine is reproducible.
    """
    eligible = [(s, isin) for isin, s in scores.items() if s >= min_score]
    eligible.sort(key=lambda x: (-x[0], x[1]))
    ordered = [isin for _, isin in eligible]
    return ordered if n <= 0 else ordered[:n]


def compute_trade_return(entry_price: Decimal, exit_price: Decimal) -> Decimal:
    """Gross return % (e.g. 100 -> 110 = 10.0000)."""
    if entry_price == 0:
        return Decimal("0")
    return ((exit_price - entry_price) / entry_price * 100).quantize(
        _Q4, rounding=ROUND_HALF_EVEN
    )


def simulate_day(
    rebalance_date: date,
    exit_date: date,
    scores: dict[str, Decimal],
    entry_prices: dict[str, Decimal],
    exit_prices: dict[str, Decimal],
    *,
    n: int,
    capital: Decimal,
    min_score: Decimal = Decimal("0"),
) -> DayResult:
    """Pick top n by score, allocate `capital` equally, apply costs, return result.

    Lookahead guard: exit_date must be strictly after rebalance_date (assert).
    Stocks without an entry or exit price are dropped (no trade); remaining
    capital is divided equally among the actually-tradeable picks.
    """
    if exit_date <= rebalance_date:
        raise AssertionError(
            f"lookahead: exit_date {exit_date} must be > rebalance_date {rebalance_date}"
        )

    picks = select_top_n(scores, n, min_score)
    tradeable = [
        p
        for p in picks
        if p in entry_prices and p in exit_prices and entry_prices[p] > 0
    ]
    result = DayResult(date=rebalance_date, positions=tradeable)
    if not tradeable:
        return result

    # Equal-CAPITAL weight (fractional shares). Integer-share sizing would
    # silently drop every stock priced above capital/len(tradeable) — at ₹1M over
    # ~200 names that's most of them, biasing toward cheap stocks. A backtest sim
    # uses fractional shares so each name carries its true equal weight.
    alloc_per = capital / Decimal(len(tradeable))
    for isin in tradeable:
        entry = entry_prices[isin]
        exit_p = exit_prices[isin]
        qty = alloc_per / entry  # fractional shares
        gross = (alloc_per * (exit_p - entry) / entry).quantize(
            _Q4, rounding=ROUND_HALF_EVEN
        )
        cost = cost_on_notional(alloc_per)
        net = (gross - cost).quantize(_Q4, rounding=ROUND_HALF_EVEN)
        result.trades.append(
            Trade(
                isin=isin,
                entry_date=rebalance_date,
                exit_date=exit_date,
                entry_price=entry,
                exit_price=exit_p,
                qty=qty,
                gross_pnl=gross,
                net_pnl=net,
                gross_return_pct=compute_trade_return(entry, exit_p),
                score=scores.get(isin, Decimal("0")),
            )
        )
        result.gross_pnl += gross
        result.net_pnl += net
        result.costs_paid += cost
    return result


# ---------------------------------------------------------------------------
# Metrics (pure)
# ---------------------------------------------------------------------------
def max_drawdown_pct(equity: list[Decimal]) -> Decimal:
    """Largest peak-to-trough drawdown as a positive % (0 if monotonic up)."""
    if not equity:
        return Decimal("0")
    peak = equity[0]
    worst = Decimal("0")
    for v in equity:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak * 100
            if dd > worst:
                worst = dd
    return worst.quantize(_Q2, rounding=ROUND_HALF_EVEN)


def win_rate_pct(trades: list[Trade]) -> Decimal:
    """Fraction of trades with strictly positive net P&L."""
    if not trades:
        return Decimal("0")
    wins = sum(1 for t in trades if t.net_pnl > 0)
    return (Decimal(wins) / Decimal(len(trades)) * 100).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )


def cagr_pct(start: Decimal, end: Decimal, years: Decimal) -> Decimal:
    """Compound annual growth rate. Returns 0 when years <= 0 or start <= 0."""
    if start <= 0 or years <= 0:
        return Decimal("0")
    ratio = float(end / start)
    if ratio <= 0:
        return Decimal("-100").quantize(_Q2, rounding=ROUND_HALF_EVEN)
    cagr = (ratio ** (1.0 / float(years)) - 1.0) * 100
    return Decimal(str(cagr)).quantize(_Q2, rounding=ROUND_HALF_EVEN)


# ---------------------------------------------------------------------------
# Risk/return metrics (Chunk 5.2 enhancement). Stats use float internally (same
# precedent as cagr_pct) and return Decimal. None signals "undefined" (e.g. zero
# variance, no downside, no losses) so the caller can render n/a honestly.
# ---------------------------------------------------------------------------
def period_returns(values: list[Decimal]) -> list[Decimal]:
    """Successive simple returns of an equity/value series (fraction, 6 dp)."""
    out: list[Decimal] = []
    for i in range(1, len(values)):
        prev = values[i - 1]
        if prev == 0:
            out.append(Decimal("0.000000"))
        else:
            out.append(
                ((values[i] - prev) / prev).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_EVEN
                )
            )
    return out


def beta(asset: list[Decimal], market: list[Decimal]) -> Decimal | None:
    """CAPM beta = cov(asset, market) / var(market). None if undefined.

    Population cov/var (the 1/n cancels in the ratio). Requires aligned,
    length>=2 series and non-zero market variance.
    """
    n = len(market)
    if n < 2 or len(asset) != n:
        return None
    a = [float(x) for x in asset]
    m = [float(x) for x in market]
    mean_a = sum(a) / n
    mean_m = sum(m) / n
    var_m = sum((x - mean_m) ** 2 for x in m) / n
    if var_m == 0:
        return None
    cov = sum((a[i] - mean_a) * (m[i] - mean_m) for i in range(n)) / n
    return Decimal(str(cov / var_m)).quantize(_Q2, rounding=ROUND_HALF_EVEN)


def _sample_std(xs: list[float], mean: float) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1))


def sharpe_ratio(
    returns: list[Decimal], rf_annual: Decimal, periods_per_year: Decimal
) -> Decimal | None:
    """Annualized Sharpe. None if <2 returns or zero volatility.

    Excess = mean(return) - rf_per_period; rf_per_period = rf_annual /
    periods_per_year. Annualized by sqrt(periods_per_year).
    """
    n = len(returns)
    if n < 2 or periods_per_year <= 0:
        return None
    r = [float(x) for x in returns]
    ppy = float(periods_per_year)
    rf_per = float(rf_annual) / ppy
    mean_r = sum(r) / n
    std = _sample_std(r, mean_r)
    if std == 0:
        return None
    sharpe = (mean_r - rf_per) / std * math.sqrt(ppy)
    return Decimal(str(sharpe)).quantize(_Q2, rounding=ROUND_HALF_EVEN)


def sortino_ratio(
    returns: list[Decimal], rf_annual: Decimal, periods_per_year: Decimal
) -> Decimal | None:
    """Annualized Sortino. None if <2 returns or no downside vs the rf target."""
    n = len(returns)
    if n < 2 or periods_per_year <= 0:
        return None
    r = [float(x) for x in returns]
    ppy = float(periods_per_year)
    rf_per = float(rf_annual) / ppy
    mean_r = sum(r) / n
    downside = [min(x - rf_per, 0.0) ** 2 for x in r]
    dd = math.sqrt(sum(downside) / n)
    if dd == 0:
        return None
    sortino = (mean_r - rf_per) / dd * math.sqrt(ppy)
    return Decimal(str(sortino)).quantize(_Q2, rounding=ROUND_HALF_EVEN)


def profit_factor(trades: list[Trade]) -> Decimal | None:
    """Gross winning P&L / gross losing P&L. None when there are no losses."""
    gross_win = sum((t.net_pnl for t in trades if t.net_pnl > 0), Decimal("0"))
    gross_loss = sum((-t.net_pnl for t in trades if t.net_pnl < 0), Decimal("0"))
    if gross_loss == 0:
        return None
    return (gross_win / gross_loss).quantize(_Q2, rounding=ROUND_HALF_EVEN)


def avg_win_pct(trades: list[Trade]) -> Decimal:
    """Mean gross_return_pct of net-winning trades (0 if none)."""
    wins = [t.gross_return_pct for t in trades if t.net_pnl > 0]
    if not wins:
        return Decimal("0")
    return (sum(wins, Decimal("0")) / Decimal(len(wins))).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )


def avg_loss_pct(trades: list[Trade]) -> Decimal:
    """Mean gross_return_pct of net-losing trades (0 if none)."""
    losses = [t.gross_return_pct for t in trades if t.net_pnl < 0]
    if not losses:
        return Decimal("0")
    return (sum(losses, Decimal("0")) / Decimal(len(losses))).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )
