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
    sharpe_ratio,
    simulate_day,
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
                    closes.get(isin, []), vols.get(isin)
                )
                if score is not None:
                    scores[isin] = score
        if not scores:
            skipped += 1
            continue

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
    n50 = await _benchmark_curve(
        session, list(_NIFTY_PROXY_ISINS), curve_dates, cfg.starting_capital
    )
    n200 = await _benchmark_curve(
        session, list(_NIFTY_200_PROXY_ISINS), curve_dates, cfg.starting_capital
    )
    n50_ret, n50_cagr, n50_returns = _bench_stats(n50, years)
    n200_ret, n200_cagr, n200_returns = _bench_stats(n200, years)

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


async def _benchmark_curve(
    session: AsyncSession,
    isins: list[str],
    curve_dates: list[date],
    starting_capital: Decimal,
) -> list[Decimal]:
    """Equal-weighted basket value normalized to `starting_capital`, sampled at
    each curve date. value(d) = capital × mean_i(price[i,d] / price[i,base]).

    Only ISINs with a base-date price are included; per date, only those with a
    price that day contribute (graceful on the odd missing bar). Buy-and-hold —
    no rebalancing, no costs (it's the benchmark).
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
    base = by_date.get(curve_dates[0], {})
    based_isins = [i for i in isins if i in base and base[i] > 0]
    if not based_isins:
        return [starting_capital] * len(curve_dates)

    out: list[Decimal] = []
    for d in curve_dates:
        prices = by_date.get(d, {})
        ratios = [prices[i] / base[i] for i in based_isins if i in prices]
        if not ratios:
            out.append(out[-1] if out else starting_capital)
            continue
        mean_ratio = sum(ratios, Decimal("0")) / Decimal(len(ratios))
        out.append(starting_capital * mean_ratio)
    return out


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
