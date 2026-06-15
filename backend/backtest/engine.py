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
    top_n: int = 15
    hold_days: int = 20
    rebalance_every: int = 20
    starting_capital: Decimal = Decimal("1000000")
    min_score: Decimal = Decimal("55")
    # Week 2 (Chunk 5.2b): score each stock with the full F+T+M composite
    # (fundamentals/macro/sector reconstructed no-lookahead) instead of the
    # technical-only proxy. Default False preserves the Chunk 5.2 baseline.
    use_full_composite: bool = False
    # Chunk 5.2c: benchmark construction — "mcap" (top-N by market cap, weighted
    # by mcap; the fair bar) or "equal" (fixed proxy baskets, equal-weight).
    benchmark_weighting: str = "mcap"
    # FIX 2 breadth regime filter (skip rebalance / go to cash when <40% of stocks
    # are above EMA200). True = current behavior; False = always-invested A/B test.
    apply_breadth_filter: bool = True
    # Config D (consistency) — all default to OFF so A/B/C are byte-identical.
    # max stocks from one sector held at once (None = uncapped).
    max_per_sector: int | None = None
    # "equal" | "score_weighted" (weight by composite score, single-name cap).
    position_sizing: str = "equal"
    # single-position cap as a FRACTION of capital for score_weighted (10%).
    max_position_weight: Decimal = Decimal("0.10")
    # trailing stop: exit intra-hold if a name falls this % from its post-entry
    # peak close (None = off, hold to scheduled exit).
    trailing_stop_pct: Decimal | None = None
    # Config E (regime switching) — all default OFF so A/B/C/D are unchanged.
    # When True, RISK-OFF rebalances rotate the book to the low-beta defensive pool;
    # RISK-ON rebalances behave exactly like Config C (full universe).
    regime_switching: bool = False
    # fraction of the scoreable universe (lowest beta) forming the defensive pool.
    defensive_pool_pct: Decimal = Decimal("0.40")
    # trailing trading-day window for the per-stock beta-vs-index estimate.
    beta_window: int = 252
    # Config F (quality-momentum allocator with cash exposure) — all default OFF
    # so A/B/C/D/E are byte-identical. Dispatch to the cash-aware portfolio path is
    # keyed on `graded_exposure` in the runner.
    # quality screen before ranking (low-vol proxy pre-2024 / ROE+debt post-2024).
    quality_gate: bool = False
    # graded cash exposure by regime (1.0 / 0.5 / 0.25) — drives the cash sleeve.
    graded_exposure: bool = False
    # a current holding is kept while its momentum rank stays within this buffer band.
    hold_buffer_rank: int = 40
    # "standard" (A-E: fresh top-N each rebalance) | "low" (F: hold winners in band).
    turnover_mode: str = "standard"
    # Config F+ — both default OFF so A/B/C/D/E/F are byte-identical.
    # check regime/exposure every N trading days, decoupled from the name rebalance
    # (None = exposure only moves at the quarterly name rebalance, i.e. plain F).
    exposure_check_days: int | None = None
    # cut a holding the day it falls this FRACTION below entry (or fails quality);
    # freed capital sits in cash until the next quarterly rebalance. None = off (F).
    breakdown_exit_pct: Decimal | None = None
    # data-integrity floor for the history fetch: never read price history before
    # this date (used to keep 2021-2026 warmup native-only, off the yfinance seam).
    # None = no floor (A-F unchanged).
    history_floor: date | None = None


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
    # "rebalance" (held to scheduled exit) or "trailing-stop" (Config D early cut).
    exit_reason: str = "rebalance"


@dataclass
class DayResult:
    date: date
    trades: list[Trade] = field(default_factory=list)
    gross_pnl: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")
    costs_paid: Decimal = Decimal("0")
    positions: list[str] = field(default_factory=list)


def select_top_n(
    scores: dict[str, Decimal],
    n: int,
    min_score: Decimal = Decimal("0"),
    *,
    sector_by: dict[str, str] | None = None,
    max_per_sector: int | None = None,
) -> list[str]:
    """ISINs scoring >= min_score, highest first.

    `n <= 0` means NO cap — return every eligible ISIN (the threshold-portfolio
    mode: hold all stocks above the score floor). `n > 0` caps at the top n.
    Deterministic tiebreak by ISIN ascending so the engine is reproducible.

    Config D: when `sector_by` + `max_per_sector` are given, a stock is skipped if
    its sector already holds `max_per_sector` picks (the next eligible name fills
    the slot) — this caps single-sector concentration. Defaults (None) reproduce
    the original behavior exactly.
    """
    eligible = [(s, isin) for isin, s in scores.items() if s >= min_score]
    eligible.sort(key=lambda x: (-x[0], x[1]))
    if sector_by is None or max_per_sector is None:
        ordered = [isin for _, isin in eligible]
        return ordered if n <= 0 else ordered[:n]

    picked: list[str] = []
    per_sector: dict[str, int] = {}
    for _s, isin in eligible:
        sec = sector_by.get(isin, "(unknown)")
        if per_sector.get(sec, 0) >= max_per_sector:
            continue
        picked.append(isin)
        per_sector[sec] = per_sector.get(sec, 0) + 1
        if n > 0 and len(picked) >= n:
            break
    return picked


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
# Config D consistency techniques (Chunk 5.2c) — pure.
# ---------------------------------------------------------------------------
def position_weights(
    picks: list[str],
    scores: dict[str, Decimal],
    sizing: str,
    max_weight: Decimal,
) -> dict[str, Decimal]:
    """Capital weights for `picks`, summing to 1.0.

    "equal" -> 1/n each. "score_weighted" -> proportional to composite score with
    any single name capped at `max_weight`; the capped excess is redistributed
    proportionally over the uncapped names so the book stays fully invested. Falls
    back to equal when scores are non-positive or the cap is infeasible.
    """
    n = len(picks)
    if n == 0:
        return {}
    equal = Decimal(1) / Decimal(n)
    if sizing != "score_weighted":
        return {p: equal for p in picks}
    pos = {p: max(scores.get(p, Decimal(0)), Decimal(0)) for p in picks}
    total = sum(pos.values(), Decimal(0))
    if total <= 0 or max_weight * Decimal(n) < 1:
        return {p: equal for p in picks}
    raw = {p: pos[p] / total for p in picks}
    over = [p for p in picks if raw[p] > max_weight]
    if not over:
        return raw
    under = [p for p in picks if p not in over]
    under_raw = sum(raw[p] for p in under)
    remaining = Decimal(1) - max_weight * Decimal(len(over))
    w: dict[str, Decimal] = dict.fromkeys(over, max_weight)
    for p in under:
        w[p] = (
            remaining * raw[p] / under_raw
            if under_raw > 0
            else remaining / Decimal(len(under))
        )
    return w


def apply_trailing_stop(
    entry: Decimal,
    path: list[tuple[date, Decimal]],
    stop_pct: Decimal,
) -> tuple[date, Decimal, bool]:
    """Walk post-entry daily closes; exit the first day a close is >= stop_pct
    below the running peak (peak starts at entry). Returns (exit_date,
    exit_price, stopped). If never triggered, exits at the last close. `path`
    must be non-empty (the caller appends the scheduled-exit close)."""
    peak = entry
    threshold = Decimal(1) - stop_pct / Decimal(100)
    for d, px in path:
        if px > peak:
            peak = px
        if px <= peak * threshold:
            return d, px, True
    return path[-1][0], path[-1][1], False


def simulate_day_d(
    rebalance_date: date,
    exit_date: date,
    scores: dict[str, Decimal],
    entry_prices: dict[str, Decimal],
    daily_paths: dict[str, list[tuple[date, Decimal]]],
    sector_by: dict[str, str],
    *,
    n: int,
    capital: Decimal,
    min_score: Decimal,
    max_per_sector: int | None,
    position_sizing: str,
    max_position_weight: Decimal,
    trailing_stop_pct: Decimal | None,
) -> DayResult:
    """Config-D day: sector-capped selection + score-weighted sizing + trailing
    stops. Each pick exits at the trailing stop or the scheduled exit, whichever
    first. Pure given pre-fetched daily paths (closes AFTER entry up to exit_date
    inclusive). Lookahead guard: exit_date > rebalance_date (assert)."""
    if exit_date <= rebalance_date:
        raise AssertionError(
            f"lookahead: exit_date {exit_date} must be > rebalance_date {rebalance_date}"
        )
    picks = select_top_n(
        scores, n, min_score, sector_by=sector_by, max_per_sector=max_per_sector
    )
    tradeable = [p for p in picks if entry_prices.get(p, Decimal(0)) > 0]
    result = DayResult(date=rebalance_date, positions=tradeable)
    if not tradeable:
        return result
    weights = position_weights(tradeable, scores, position_sizing, max_position_weight)
    for isin in tradeable:
        entry = entry_prices[isin]
        alloc = capital * weights[isin]
        path = daily_paths.get(isin, [])
        if trailing_stop_pct is not None and path:
            ex_date, exit_p, stopped = apply_trailing_stop(
                entry, path, trailing_stop_pct
            )
            reason = "trailing-stop" if stopped else "rebalance"
        elif path:
            ex_date, exit_p, reason = path[-1][0], path[-1][1], "rebalance"
        else:
            ex_date, exit_p, reason = exit_date, entry, "rebalance"
        qty = alloc / entry
        gross = (alloc * (exit_p - entry) / entry).quantize(
            _Q4, rounding=ROUND_HALF_EVEN
        )
        cost = cost_on_notional(alloc)
        net = (gross - cost).quantize(_Q4, rounding=ROUND_HALF_EVEN)
        result.trades.append(
            Trade(
                isin=isin,
                entry_date=rebalance_date,
                exit_date=ex_date,
                entry_price=entry,
                exit_price=exit_p,
                qty=qty,
                gross_pnl=gross,
                net_pnl=net,
                gross_return_pct=compute_trade_return(entry, exit_p),
                score=scores.get(isin, Decimal("0")),
                exit_reason=reason,
            )
        )
        result.gross_pnl += gross
        result.net_pnl += net
        result.costs_paid += cost
    return result


# ---------------------------------------------------------------------------
# Config E regime switching (Chunk 5.2c) — pure.
# ---------------------------------------------------------------------------
def trailing_window(
    series: list[tuple[date, Decimal]], as_of: date, n: int
) -> list[tuple[date, Decimal]]:
    """Last `n` (date, value) pairs with date <= as_of (the no-lookahead guard).

    Any bar dated AFTER `as_of` is dropped before slicing, so a regime/beta window
    can never peek at a future bar even if the caller passes a longer series.
    `n <= 0` returns the full past series.
    """
    past = [(d, v) for d, v in series if d <= as_of]
    return past[-n:] if n > 0 else past


def detect_regime(
    index_closes: list[Decimal] | list[float],
    *,
    dma_window: int = 200,
    mom_window: int = 50,
) -> str:
    """Market regime from a trend filter on the index close series ENDING at the
    decision date (the caller guarantees no future bars). Returns "risk_on" when
    the last close is above its `dma_window`-day moving average AND the
    `mom_window`-day return is >= 0; otherwise "risk_off".

    Reactive, not predictive: it confirms a sustained trend, so it will NOT dodge
    the first leg of a sudden crash. Warmup (fewer than `dma_window` closes, or no
    momentum reference) defaults to "risk_on" (full participation) — never
    fabricate a regime from thin history.
    """
    n = len(index_closes)
    if n < dma_window or n <= mom_window:
        return "risk_on"
    closes = [float(x) for x in index_closes]
    dma = sum(closes[-dma_window:]) / dma_window
    last = closes[-1]
    ref = closes[-mom_window - 1]
    mom_ok = ref > 0 and (last - ref) / ref >= 0
    return "risk_on" if (last > dma and mom_ok) else "risk_off"


def classify_defensive_pool(
    betas: dict[str, Decimal], defensive_pct: Decimal
) -> set[str]:
    """The lowest-beta `defensive_pct` fraction of names — the defensive pool.

    Ties broken by ISIN for determinism. At least one name is returned when betas
    are present; an empty set when no beta could be estimated (e.g. thin history).
    """
    if not betas:
        return set()
    ordered = sorted(betas.items(), key=lambda kv: (kv[1], kv[0]))
    k = max(1, int(len(ordered) * float(defensive_pct)))
    return {isin for isin, _b in ordered[:k]}


# ---------------------------------------------------------------------------
# Config F: cash exposure (Component 0/5) + low-vol quality (Component 1) — pure.
# ---------------------------------------------------------------------------
def split_capital(total: Decimal, exposure: Decimal) -> tuple[Decimal, Decimal]:
    """(invested_capital, cash_capital) for a target exposure in [0, 1].

    invested = exposure * total; cash = the rest. Exposure 1.0 -> all invested
    (cash 0), reproducing the always-invested book. Cash earns nothing here (an
    honest, conservative assumption — see lesson). This is the core of Component 0:
    the blended equity = invested-sleeve value + cash, so a fall only hits the
    invested fraction.
    """
    exposure = max(Decimal("0"), min(Decimal("1"), exposure))
    invested = (total * exposure).quantize(_Q4, rounding=ROUND_HALF_EVEN)
    return invested, total - invested


def target_exposure_for_regime(
    index_closes: list[Decimal] | list[float],
    *,
    dma_window: int = 200,
    mom_window: int = 50,
    deep_pct: Decimal = Decimal("-8"),
) -> Decimal:
    """Graded target exposure from a trend filter on the index closes ENDING at the
    decision date (caller guarantees no future bars):

      above DMA AND 50-day return >= 0          -> 1.00 (healthy, fully invested)
      below DMA                                 -> 0.50 (mild risk-off, half cash)
      below DMA AND 50-day return < deep_pct    -> 0.25 (deep risk-off, 75% cash)
      above DMA but 50-day return < 0           -> 0.50 (not fully healthy)

    REACTIVE (200-DMA/50-day): it confirms downtrends, so it cannot dodge the first
    leg of a sudden crash. Warmup (< dma_window closes) defaults to 1.00 (full) —
    never fabricate a regime from thin history.
    """
    n = len(index_closes)
    if n < dma_window or n <= mom_window:
        return Decimal("1.00")
    closes = [float(x) for x in index_closes]
    dma = sum(closes[-dma_window:]) / dma_window
    last = closes[-1]
    ref = closes[-mom_window - 1]
    mom_pct = (last - ref) / ref * 100 if ref > 0 else 0.0
    below = last < dma
    if below and mom_pct < float(deep_pct):
        return Decimal("0.25")
    if below:
        return Decimal("0.50")
    if mom_pct >= 0:
        return Decimal("1.00")
    return Decimal("0.50")


def realized_vol(returns: list[float]) -> float | None:
    """Sample standard deviation of daily returns (None if < 2 points)."""
    n = len(returns)
    if n < 2:
        return None
    mean = sum(returns) / n
    return math.sqrt(sum((r - mean) ** 2 for r in returns) / (n - 1))


def low_vol_pass(vols: dict[str, float], exclude_top_frac: float = 1.0 / 3.0) -> set[str]:
    """Quality proxy when fundamentals are absent: the names NOT in the highest-
    volatility tertile. Lowest-vol first, ties by ISIN. Empty if no vols."""
    if not vols:
        return set()
    ordered = sorted(vols.items(), key=lambda kv: (kv[1], kv[0]))
    keep_n = max(1, round(len(ordered) * (1.0 - exclude_top_frac)))
    return {isin for isin, _v in ordered[:keep_n]}


def low_vol_cutoff(vols: dict[str, float], exclude_top_frac: float = 1.0 / 3.0) -> float | None:
    """Boundary vol of the low-vol-kept set (the highest vol still 'quality'). A
    held name whose trailing vol later exceeds this has broken down on quality.
    None if no vols."""
    if not vols:
        return None
    ordered = sorted(vols.values())
    keep_n = max(1, round(len(ordered) * (1.0 - exclude_top_frac)))
    return ordered[keep_n - 1]


def breaks_down(
    close: Decimal, entry: Decimal, pct_frac: Decimal, fails_quality: bool
) -> bool:
    """Config F+ cut-on-breakdown predicate. Sell a holding when it FAILS the
    quality gate OR has fallen >= `pct_frac` (a fraction, e.g. 0.15) below its
    ENTRY price. Pure on (close, entry) — uses only the current close and the known
    entry price, never any future bar (no-lookahead by construction)."""
    if fails_quality:
        return True
    if entry <= 0:
        return False
    return close <= entry * (Decimal("1") - pct_frac)


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
