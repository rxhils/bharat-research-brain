"""Walk-forward backtest runner (Chunk 5.2 STEP 3) — READ-ONLY against the DB.

NEVER writes to live signal tables. Streams per-stock price history bounded by
`trade_date <= D` so the score reconstructor cannot see future bars. The Nifty
benchmark is computed from the same `prices_eod_adjusted` table over the exact
same rebalance window (operator's large-cap proxy basket).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

import structlog
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.technical_indicators import ema
from backend.backtest.engine import (
    BacktestConfig,
    DayResult,
    Trade,
    avg_loss_pct,
    avg_win_pct,
    beta,
    cagr_pct,
    max_drawdown_pct,
    period_returns,
    profit_factor,
    select_top_n,
    sharpe_ratio,
    simulate_day,
    simulate_day_d,
    sortino_ratio,
    win_rate_pct,
)
from backend.backtest.scores import (
    compute_full_composite,
    compute_score_from_history,
    reconstruct_macro_score,
)

# India risk-free rate for Sharpe/Sortino (operator-specified).
_RISK_FREE_ANNUAL = Decimal("0.07")

log = structlog.get_logger()

_Q2 = Decimal("0.01")

# Operator-specified large-cap proxy basket for the Nifty benchmark (10 ISINs
# confirmed present in `stocks` via STEP 0).
_NIFTY_PROXY_ISINS = (
    "INE002A01018",  # RELIANCE
    "INE467B01029",  # TCS
    "INE040A01034",  # HDFCBANK
    "INE009A01021",  # INFY
    "INE090A01021",  # ICICIBANK
    "INE030A01027",  # HINDUNILVR
    "INE238A01034",  # AXISBANK
    "INE237A01036",  # KOTAKBANK
    "INE296A01032",  # BAJFINANCE
    "INE062A01020",  # SBIN
)

# Nifty 200 proxy: 39 sector-diverse large + mid caps present in the DB. EQUAL-
# WEIGHTED, NOT market-cap-weighted — `stocks.mcap_inr_cr` is 0/507 populated, so
# honest weighting is impossible; an equal-weight broad basket is the best
# available approximation (and matches how the Nifty 50 proxy is computed).
_NIFTY_200_PROXY_ISINS = (
    "INE423A01024", "INE208A01029", "INE021A01026", "INE238A01034",
    "INE296A01032", "INE465A01025", "INE397D01024", "INE522F01014",
    "INE591G01025", "INE484J01027", "INE860A01027", "INE040A01034",
    "INE030A01027", "INE090A01021", "INE009A01021", "INE154A01025",
    "INE019A01038", "INE237A01036", "INE018A01030", "INE326A01037",
    "INE634S01028", "INE585B01010", "INE101A01026", "INE239A01024",
    "INE733E01010", "INE093I01010", "INE213A01029", "INE262H01021",
    "INE603J01030", "INE752E01010", "INE002A01018", "INE062A01020",
    "INE044A01036", "INE081A01020", "INE467B01029", "INE280A01028",
    "INE494B01023", "INE481G01011", "INE075A01022",
)

# Need ~1y of bars to seed EMA200 + a 252d window before the first rebalance.
_WARMUP_DAYS = 260


def _compute_breadth(closes: dict[str, list[float]]) -> Decimal | None:
    """% of stocks whose yesterday's close is above their 200-day EMA.

    Uses series[-2] (yesterday's close) so the breadth decision never peeks
    at the rebalance day's close. Returns None when there's no data to
    compute from. Only stocks with enough history (>= 200 bars) are counted.
    """
    above = 0
    total = 0
    for series in closes.values():
        if len(series) < 200:
            continue
        total += 1
        e = ema(series, 200)
        if e is not None and series[-2] > e:
            above += 1
    if total == 0:
        return None
    return (Decimal(above) / Decimal(total) * 100).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_EVEN
    )


@dataclass
class BacktestResult:
    config: BacktestConfig
    start_value: Decimal
    end_value: Decimal
    total_return_pct: Decimal
    cagr_pct: Decimal
    max_drawdown_pct: Decimal
    win_rate_pct: Decimal
    total_trades: int
    total_costs_paid: Decimal
    equity_curve: list[tuple[date, Decimal]] = field(default_factory=list)
    # Nifty 50 proxy (the existing fields keep their names for back-compat).
    nifty_benchmark_return_pct: Decimal = Decimal("0")
    alpha_vs_nifty_pct: Decimal = Decimal("0")
    nifty50_cagr_pct: Decimal = Decimal("0")
    beta_vs_nifty50: Decimal | None = None
    # Nifty 200 proxy (broader large+mid basket).
    nifty200_return_pct: Decimal = Decimal("0")
    nifty200_cagr_pct: Decimal = Decimal("0")
    alpha_vs_nifty200_pct: Decimal = Decimal("0")
    beta_vs_nifty200: Decimal | None = None
    # Nifty 500 TRI (REAL published index — no proxy lookahead). n/a if unloaded.
    nifty500_tri_return_pct: Decimal | None = None
    nifty500_tri_cagr_pct: Decimal | None = None
    alpha_vs_nifty500_tri_pct: Decimal | None = None
    beta_vs_nifty500_tri: Decimal | None = None
    # Risk-adjusted metrics.
    sharpe: Decimal | None = None
    sortino: Decimal | None = None
    profit_factor: Decimal | None = None
    avg_win_pct: Decimal = Decimal("0")
    avg_loss_pct: Decimal = Decimal("0")
    sector_exposure: list[tuple[str, Decimal]] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    day_results: list[DayResult] = field(default_factory=list)
    skipped_dates: int = 0


# ---------------------------------------------------------------------------
# SQL — every read uses `trade_date <= :as_of` or a bounded BETWEEN window.
# ---------------------------------------------------------------------------
_SQL_TRADING_DAYS = text(
    "SELECT DISTINCT trade_date FROM prices_eod_adjusted "
    "WHERE trade_date BETWEEN :start AND :end ORDER BY trade_date"
)

_SQL_HISTORY_CLOSE = text(
    """
    SELECT isin, trade_date, adj_close
    FROM prices_eod_adjusted
    WHERE trade_date BETWEEN :start AND :as_of
      AND adj_close IS NOT NULL
      AND isin = ANY(:isins)
    ORDER BY isin, trade_date
    """
).bindparams(bindparam("isins"))

_SQL_HISTORY_VOLUME = text(
    """
    SELECT isin, trade_date, volume
    FROM prices_eod
    WHERE trade_date BETWEEN :start AND :as_of
      AND volume IS NOT NULL
      AND isin = ANY(:isins)
    ORDER BY isin, trade_date
    """
).bindparams(bindparam("isins"))

_SQL_PRICES_ON_DATE = text(
    """
    SELECT isin, adj_close
    FROM prices_eod_adjusted
    WHERE trade_date = :as_of
      AND adj_close IS NOT NULL
      AND isin = ANY(:isins)
    """
).bindparams(bindparam("isins"))

_SQL_ACTIVE_ISINS = text(
    "SELECT isin FROM stocks WHERE delisted_on IS NULL"
)


async def _trading_days(
    session: AsyncSession, start: date, end: date
) -> list[date]:
    rows = (
        await session.execute(_SQL_TRADING_DAYS, {"start": start, "end": end})
    ).all()
    return [r[0] for r in rows]


async def _active_isins(session: AsyncSession) -> list[str]:
    rows = (await session.execute(_SQL_ACTIVE_ISINS)).all()
    return [r[0] for r in rows]


# Latest sector-momentum class per sector as-of a date — ONE DISTINCT ON query
# for all 19 sectors, not one per stock (postgres-patterns: no N identical reads).
_SQL_SECTOR_CLASS_ASOF = text(
    """
    SELECT DISTINCT ON (sector) sector, classification, computed_date
    FROM sector_signals_historical
    WHERE computed_date <= :as_of
    ORDER BY sector, computed_date DESC
    """
)


async def _sector_signals_on(
    session: AsyncSession, isins: list[str], as_of: date
) -> dict[str, str]:
    """{isin: 'leading'|'neutral'|'lagging'} from the latest sector class <= as_of.

    Two batched queries (sector classes + isin->sector), never one per stock. The
    DISTINCT ON guarantees `computed_date <= as_of`; asserted defensively.
    """
    class_rows = (
        await session.execute(_SQL_SECTOR_CLASS_ASOF, {"as_of": as_of})
    ).all()
    class_by_sector: dict[str, str] = {}
    for sec, classification, cd in class_rows:
        assert cd <= as_of, f"lookahead: sector {sec} {cd} > as_of {as_of}"
        class_by_sector[sec] = classification or "neutral"
    sector_rows = (
        await session.execute(_SQL_SECTORS, {"isins": list(isins)})
    ).all()
    return {isin: class_by_sector.get(sec, "neutral") for isin, sec in sector_rows}


async def _fetch_history(
    session: AsyncSession,
    isins: list[str],
    *,
    start: date,
    as_of: date,
) -> tuple[dict[str, list[float]], dict[str, list[int]]]:
    """Per-isin (closes_series, volumes_series) ending at as_of inclusive.

    Both series are filtered with `trade_date <= as_of` so no future bar leaks.
    """
    closes: dict[str, list[float]] = {}
    vols: dict[str, list[int]] = {}
    close_rows = (
        await session.execute(
            _SQL_HISTORY_CLOSE,
            {"start": start, "as_of": as_of, "isins": list(isins)},
        )
    ).all()
    for isin, _td, ac in close_rows:
        closes.setdefault(isin, []).append(float(ac))
    vol_rows = (
        await session.execute(
            _SQL_HISTORY_VOLUME,
            {"start": start, "as_of": as_of, "isins": list(isins)},
        )
    ).all()
    for isin, _td, v in vol_rows:
        vols.setdefault(isin, []).append(int(v))
    return closes, vols


async def _adj_close_on(
    session: AsyncSession, isins: list[str], as_of: date
) -> dict[str, Decimal]:
    rows = (
        await session.execute(
            _SQL_PRICES_ON_DATE, {"as_of": as_of, "isins": list(isins)}
        )
    ).all()
    return {i: c for i, c in rows}


# Config D: post-entry daily closes per stock (for trailing stops) + sector map.
_SQL_DAILY_PATHS = text(
    """
    SELECT isin, trade_date, adj_close
    FROM prices_eod_adjusted
    WHERE trade_date > :start AND trade_date <= :end
      AND adj_close IS NOT NULL
      AND isin = ANY(:isins)
    ORDER BY isin, trade_date
    """
).bindparams(bindparam("isins"))


async def _daily_paths(
    session: AsyncSession, isins: list[str], start: date, end: date
) -> dict[str, list[tuple[date, Decimal]]]:
    """{isin: [(date, close)...]} for closes strictly AFTER `start` up to `end`."""
    if not isins:
        return {}
    rows = (
        await session.execute(
            _SQL_DAILY_PATHS, {"start": start, "end": end, "isins": list(isins)}
        )
    ).all()
    out: dict[str, list[tuple[date, Decimal]]] = {}
    for isin, td, ac in rows:
        out.setdefault(isin, []).append((td, ac))
    return out


async def _sectors_map(session: AsyncSession, isins: list[str]) -> dict[str, str]:
    rows = (await session.execute(_SQL_SECTORS, {"isins": list(isins)})).all()
    return {i: (s or "(unknown)") for i, s in rows}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def run_backtest(session: AsyncSession, cfg: BacktestConfig) -> BacktestResult:
    """Walk-forward backtest. Returns aggregated metrics + the equity curve.

    Read-only: every SQL has `trade_date <= as_of` or BETWEEN(start, as_of).
    Writes nothing to stock_rankings, outcome_log, or any live table.
    """
    if cfg.end_date <= cfg.start_date:
        raise ValueError("end_date must be > start_date")

    days = await _trading_days(session, cfg.start_date, cfg.end_date)
    if len(days) < cfg.hold_days + 1:
        raise ValueError(
            f"not enough trading days ({len(days)}) for hold={cfg.hold_days}"
        )

    # Rebalance every N days; last rebalance must allow a full hold window forward.
    rebalance_idx = list(range(0, len(days), cfg.rebalance_every))
    rebalance_idx = [i for i in rebalance_idx if i + cfg.hold_days < len(days)]

    history_start = _history_start(days[0])
    isins = await _active_isins(session)
    # Config D path: sector-capped selection + score-weighted sizing + trailing
    # stops. Off by default -> A/B/C take the original simulate_day path.
    advanced = (
        cfg.max_per_sector is not None
        or cfg.trailing_stop_pct is not None
        or cfg.position_sizing != "equal"
    )
    sector_by = await _sectors_map(session, isins) if advanced else {}
    log.info(
        "backtest.run.start",
        start=cfg.start_date.isoformat(),
        end=cfg.end_date.isoformat(),
        trading_days=len(days),
        rebalances=len(rebalance_idx),
        active_isins=len(isins),
    )

    equity = cfg.starting_capital
    curve: list[tuple[date, Decimal]] = [(days[0], equity)]
    all_trades: list[Trade] = []
    all_days: list[DayResult] = []
    total_costs = Decimal("0")
    skipped = 0

    for i in rebalance_idx:
        rebalance_date = days[i]
        exit_date = days[i + cfg.hold_days]
        closes, vols = await _fetch_history(
            session, isins, start=history_start, as_of=rebalance_date
        )

        # ---- FIX 2: Market breadth regime filter ---------------------------
        # Compute % of stocks above their 200-day EMA. If breadth < 40%,
        # skip this rebalance entirely (move to cash). This avoids major
        # drawdowns during bear markets, crashes, and corrections.
        pct_above_ema200 = _compute_breadth(closes)
        if (
            cfg.apply_breadth_filter
            and pct_above_ema200 is not None
            and pct_above_ema200 < Decimal("40")
        ):
            skipped += 1
            log.info(
                "backtest.skipped.bearish",
                date=str(rebalance_date),
                pct_above_ema200=str(pct_above_ema200),
            )
            continue
        # ---------------------------------------------------------------------

        scores: dict[str, Decimal] = {}
        if cfg.use_full_composite:
            # Per-date inputs fetched ONCE (macro is isin-independent; sector
            # classes batched) — only fundamentals are read per stock.
            macro_score = await reconstruct_macro_score(session, rebalance_date)
            sector_sig = await _sector_signals_on(session, isins, rebalance_date)
            for isin in isins:
                score = await compute_full_composite(
                    session,
                    isin,
                    rebalance_date,
                    closes.get(isin, []),
                    vols.get(isin),
                    macro_score=macro_score,
                    sector_signal=sector_sig.get(isin, "neutral"),
                )
                if score is not None:
                    scores[isin] = score
        else:
            for isin in isins:
                score = compute_score_from_history(
                    closes.get(isin, []), vols.get(isin),
                    all_closes=closes,
                )
                if score is not None:
                    scores[isin] = score
        if not scores:
            skipped += 1
            continue

        if advanced:
            picks = select_top_n(
                scores, cfg.top_n, cfg.min_score,
                sector_by=sector_by, max_per_sector=cfg.max_per_sector,
            )
            entry_prices = await _adj_close_on(session, picks, rebalance_date)
            paths = await _daily_paths(session, picks, rebalance_date, exit_date)
            day_result = simulate_day_d(
                rebalance_date,
                exit_date,
                scores,
                entry_prices,
                paths,
                sector_by,
                n=cfg.top_n,
                capital=equity,
                min_score=cfg.min_score,
                max_per_sector=cfg.max_per_sector,
                position_sizing=cfg.position_sizing,
                max_position_weight=cfg.max_position_weight,
                trailing_stop_pct=cfg.trailing_stop_pct,
            )
        else:
            entry_prices = await _adj_close_on(session, isins, rebalance_date)
            exit_prices = await _adj_close_on(session, isins, exit_date)
            day_result = simulate_day(
                rebalance_date,
                exit_date,
                scores,
                entry_prices,
                exit_prices,
                n=cfg.top_n,
                capital=equity,
                min_score=cfg.min_score,
            )
        all_days.append(day_result)
        all_trades.extend(day_result.trades)
        total_costs += day_result.costs_paid

        equity += day_result.net_pnl
        curve.append((exit_date, equity))

    # ---- Summary + benchmarks + risk metrics -------------------------------
    years = Decimal((cfg.end_date - cfg.start_date).days) / Decimal("365.25")
    total_return = ((equity / cfg.starting_capital - 1) * 100).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )
    bot_cagr = cagr_pct(cfg.starting_capital, equity, years)

    curve_dates = [d for d, _ in curve]
    bot_values = [v for _, v in curve]
    bot_returns = period_returns(bot_values)

    # Benchmarks sampled at the SAME curve dates so returns/alpha/beta align.
    # Chunk 5.2c: mcap-weighted (default) selects top-N by CURRENT market cap and
    # weights by mcap; equal uses the fixed proxy baskets, equal-weight. If mcap
    # is unpopulated, fall back to the equal proxies (with a warning), never crash.
    if cfg.benchmark_weighting == "mcap":
        n50_isins, n50_w = await _top_by_mcap(session, 50)
        n200_isins, n200_w = await _top_by_mcap(session, 200)
        if not n50_isins or not n200_isins:
            log.warning(
                "backtest.benchmark.mcap_unpopulated",
                n50=len(n50_isins),
                n200=len(n200_isins),
            )
            n50_isins, n50_w = list(_NIFTY_PROXY_ISINS), None
            n200_isins, n200_w = list(_NIFTY_200_PROXY_ISINS), None
    else:
        n50_isins, n50_w = list(_NIFTY_PROXY_ISINS), None
        n200_isins, n200_w = list(_NIFTY_200_PROXY_ISINS), None
    n50 = await _benchmark_curve(
        session, n50_isins, curve_dates, cfg.starting_capital, weights=n50_w
    )
    n200 = await _benchmark_curve(
        session, n200_isins, curve_dates, cfg.starting_capital, weights=n200_w
    )
    n50_ret, n50_cagr, n50_returns = _bench_stats(n50, years)
    n200_ret, n200_cagr, n200_returns = _bench_stats(n200, years)
    # Nifty 500 TRI — REAL published index (no proxy lookahead). n/a if unloaded.
    n500 = await _index_curve(
        session, "nifty500_tri", curve_dates, cfg.starting_capital
    )
    if n500 is not None:
        n500_ret, n500_cagr, n500_returns = _bench_stats(n500, years)
        n500_alpha: Decimal | None = (total_return - n500_ret).quantize(
            _Q2, rounding=ROUND_HALF_EVEN
        )
        n500_beta = beta(bot_returns, n500_returns)
    else:
        n500_ret = n500_cagr = n500_alpha = None
        n500_beta = None

    ppy = (
        Decimal(len(bot_returns)) / years if years > 0 else Decimal("0")
    )

    result = BacktestResult(
        config=cfg,
        start_value=cfg.starting_capital,
        end_value=equity.quantize(_Q2, rounding=ROUND_HALF_EVEN),
        total_return_pct=total_return,
        cagr_pct=bot_cagr,
        max_drawdown_pct=max_drawdown_pct(bot_values),
        win_rate_pct=win_rate_pct(all_trades),
        total_trades=len(all_trades),
        total_costs_paid=total_costs.quantize(_Q2, rounding=ROUND_HALF_EVEN),
        equity_curve=curve,
        nifty_benchmark_return_pct=n50_ret,
        alpha_vs_nifty_pct=(total_return - n50_ret).quantize(_Q2),
        nifty50_cagr_pct=n50_cagr,
        beta_vs_nifty50=beta(bot_returns, n50_returns),
        nifty200_return_pct=n200_ret,
        nifty200_cagr_pct=n200_cagr,
        alpha_vs_nifty200_pct=(total_return - n200_ret).quantize(_Q2),
        beta_vs_nifty200=beta(bot_returns, n200_returns),
        nifty500_tri_return_pct=n500_ret,
        nifty500_tri_cagr_pct=n500_cagr,
        alpha_vs_nifty500_tri_pct=n500_alpha,
        beta_vs_nifty500_tri=n500_beta,
        sharpe=sharpe_ratio(bot_returns, _RISK_FREE_ANNUAL, ppy),
        sortino=sortino_ratio(bot_returns, _RISK_FREE_ANNUAL, ppy),
        profit_factor=profit_factor(all_trades),
        avg_win_pct=avg_win_pct(all_trades),
        avg_loss_pct=avg_loss_pct(all_trades),
        sector_exposure=await _sector_exposure(session, all_trades),
        trades=all_trades,
        day_results=all_days,
        skipped_dates=skipped,
    )
    log.info(
        "backtest.run.done",
        rebalances=len(rebalance_idx),
        trades=len(all_trades),
        total_return_pct=str(total_return),
        nifty50_pct=str(n50_ret),
        nifty200_pct=str(n200_ret),
        alpha50_pct=str(result.alpha_vs_nifty_pct),
        sharpe=str(result.sharpe),
    )
    return result


def _history_start(first_rebalance: date) -> date:
    """A buffer-comfortable start for the history SQL — at least 1 year prior."""
    return first_rebalance - timedelta(days=_WARMUP_DAYS * 2)


_SQL_PRICES_ON_DATES = text(
    """
    SELECT isin, trade_date, adj_close
    FROM prices_eod_adjusted
    WHERE trade_date = ANY(:dates)
      AND adj_close IS NOT NULL
      AND isin = ANY(:isins)
    """
).bindparams(bindparam("isins"), bindparam("dates"))

_SQL_SECTORS = text(
    "SELECT isin, sector FROM stocks WHERE isin = ANY(:isins)"
).bindparams(bindparam("isins"))

# Top-N stocks by CURRENT market cap (Chunk 5.2c). mcap is point-in-time-as-of-
# today, NOT historical — a mild selection+weighting lookahead, flagged in the
# lesson; still far fairer than equal-weight in a broad mid-cap rally.
_SQL_TOP_BY_MCAP = text(
    "SELECT isin, mcap_inr_cr FROM stocks "
    "WHERE mcap_inr_cr IS NOT NULL AND delisted_on IS NULL "
    "ORDER BY mcap_inr_cr DESC LIMIT :n"
)


async def _top_by_mcap(
    session: AsyncSession, n: int
) -> tuple[list[str], dict[str, Decimal]]:
    """(top-n ISINs by mcap, {isin: mcap_cr}). Empty if mcap is unpopulated."""
    rows = (await session.execute(_SQL_TOP_BY_MCAP, {"n": n})).all()
    return [r[0] for r in rows], {r[0]: Decimal(r[1]) for r in rows}


def _weighted_ratio(
    base: dict[str, Decimal],
    prices: dict[str, Decimal],
    weights: dict[str, Decimal] | None,
) -> Decimal | None:
    """Basket value multiplier vs base, over names present in BOTH base and prices.

    `weights is None` -> equal weight (mean of price/base ratios, matching the
    original equal-weight benchmark). `weights` given -> cap-weighted: each present
    name's ratio is scaled by its weight renormalized over the present set, so a
    stock 10x another's mcap drives ~10/11 of the move. None if no name overlaps.
    """
    present = [i for i in base if base[i] > 0 and i in prices]
    if not present:
        return None
    if weights is None:
        return sum((prices[i] / base[i] for i in present), Decimal("0")) / Decimal(
            len(present)
        )
    wsum = sum((weights.get(i, Decimal("0")) for i in present), Decimal("0"))
    if wsum <= 0:
        return sum((prices[i] / base[i] for i in present), Decimal("0")) / Decimal(
            len(present)
        )
    return sum(
        (
            (weights.get(i, Decimal("0")) / wsum) * (prices[i] / base[i])
            for i in present
        ),
        Decimal("0"),
    )


async def _benchmark_curve(
    session: AsyncSession,
    isins: list[str],
    curve_dates: list[date],
    starting_capital: Decimal,
    *,
    weights: dict[str, Decimal] | None = None,
) -> list[Decimal]:
    """Basket value normalized to `starting_capital`, sampled at each curve date.

    `weights is None` -> equal-weight (the original behavior). `weights` given ->
    market-cap-weighted (Chunk 5.2c). Only ISINs with a base-date price are
    included; per date, only those with a price that day contribute (graceful on a
    missing bar). Buy-and-hold — no rebalancing, no costs (it's the benchmark).
    """
    if len(curve_dates) < 2:
        return [starting_capital] * len(curve_dates)
    rows = (
        await session.execute(
            _SQL_PRICES_ON_DATES, {"isins": isins, "dates": curve_dates}
        )
    ).all()
    by_date: dict[date, dict[str, Decimal]] = {}
    for isin, td, ac in rows:
        by_date.setdefault(td, {})[isin] = ac
    base_day = by_date.get(curve_dates[0], {})
    base = {i: base_day[i] for i in isins if i in base_day and base_day[i] > 0}
    if not base:
        return [starting_capital] * len(curve_dates)

    out: list[Decimal] = []
    for d in curve_dates:
        ratio = _weighted_ratio(base, by_date.get(d, {}), weights)
        if ratio is None:
            out.append(out[-1] if out else starting_capital)
        else:
            out.append(starting_capital * ratio)
    return out


_SQL_INDEX_SERIES = text(
    "SELECT trade_date, index_value FROM benchmark_index "
    "WHERE index_name = :name ORDER BY trade_date"
)


async def _index_curve(
    session: AsyncSession,
    index_name: str,
    curve_dates: list[date],
    starting_capital: Decimal,
) -> list[Decimal] | None:
    """Value curve from a REAL published index (e.g. Nifty 500 TRI), normalized to
    `starting_capital`, sampled at each curve date by the value on-or-before it.

    No proxy, no current-mcap lookahead — published index closes. Returns None if
    the index is not loaded (graceful 'n/a'). Both `curve_dates` and the DB series
    are ascending, so a single forward two-pointer pass resolves on-or-before.
    """
    rows = (await session.execute(_SQL_INDEX_SERIES, {"name": index_name})).all()
    if not rows or len(curve_dates) < 2:
        return None
    series = [(d, Decimal(v)) for d, v in rows]
    values_on: list[Decimal | None] = []
    j = 0
    last: Decimal | None = None
    for cd in curve_dates:
        while j < len(series) and series[j][0] <= cd:
            last = series[j][1]
            j += 1
        values_on.append(last)
    base = values_on[0]
    if base is None or base <= 0:
        return None
    return [
        (starting_capital * (v / base)) if v is not None else starting_capital
        for v in values_on
    ]


def _bench_stats(
    curve: list[Decimal], years: Decimal
) -> tuple[Decimal, Decimal, list[Decimal]]:
    """(total_return_pct, cagr_pct, period_returns) for a benchmark value curve."""
    if len(curve) < 2 or curve[0] <= 0:
        return Decimal("0"), Decimal("0"), []
    total = ((curve[-1] / curve[0] - 1) * 100).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )
    return total, cagr_pct(curve[0], curve[-1], years), period_returns(curve)


async def _sector_exposure(
    session: AsyncSession, trades: list[Trade]
) -> list[tuple[str, Decimal]]:
    """% of holdings by sector (each trade = one equal-weight position-hold).

    Trade-count share approximates time-held share since every position is held
    for the same fixed window. Sorted descending; '(unknown)' for unmapped ISINs.
    """
    if not trades:
        return []
    isins = list({t.isin for t in trades})
    rows = (await session.execute(_SQL_SECTORS, {"isins": isins})).all()
    sector_by = {i: (s or "(unknown)") for i, s in rows}
    counts: dict[str, int] = {}
    for t in trades:
        sec = sector_by.get(t.isin, "(unknown)")
        counts[sec] = counts.get(sec, 0) + 1
    total = Decimal(len(trades))
    out = [
        (sec, (Decimal(c) / total * 100).quantize(_Q2, rounding=ROUND_HALF_EVEN))
        for sec, c in counts.items()
    ]
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def summarize(result: BacktestResult) -> dict[str, Any]:
    """Render a small dict for the CLI table (decimals stringified)."""
    return {
        "period": (
            f"{result.config.start_date.isoformat()} → "
            f"{result.config.end_date.isoformat()}"
        ),
        "start_value": str(result.start_value),
        "end_value": str(result.end_value),
        "total_return_pct": str(result.total_return_pct),
        "cagr_pct": str(result.cagr_pct),
        "max_drawdown_pct": str(result.max_drawdown_pct),
        "win_rate_pct": str(result.win_rate_pct),
        "total_trades": result.total_trades,
        "total_costs_paid": str(result.total_costs_paid),
        "nifty_pct": str(result.nifty_benchmark_return_pct),
        "alpha_pct": str(result.alpha_vs_nifty_pct),
        "skipped": result.skipped_dates,
    }
