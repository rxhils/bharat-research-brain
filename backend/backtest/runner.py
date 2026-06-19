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
from backend.backtest.cost_model import cost_on_notional
from backend.backtest.engine import (
    BacktestConfig,
    DayResult,
    Trade,
    avg_loss_pct,
    avg_win_pct,
    beta,
    breaks_down,
    cagr_pct,
    classify_defensive_pool,
    detect_regime,
    low_vol_cutoff,
    low_vol_pass,
    max_drawdown_pct,
    period_returns,
    profit_factor,
    realized_vol,
    select_top_n,
    sharpe_ratio,
    simulate_day,
    simulate_day_d,
    sortino_ratio,
    split_capital,
    target_exposure_for_regime,
    trailing_window,
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

# Test 1 (Phase-2 branch) — per-stock 52-week momentum metric, precomputed once
# per rebalance and threaded into compute_full_composite (frozen F+ never does
# this, so its momentum sub-signal is inert). All reads use closes[-2] (yesterday)
# to honor the no-lookahead invariant, matching the scorer.
_MOM_W52 = 252
_MOM_TYPICAL_VOL = 0.30  # annualized; keeps vol-adj momentum in return-units
_MOM_VOL_FLOOR = 0.05


def _momentum_metric(
    closes_by_isin: dict[str, list[float]], mode: str
) -> dict[str, float]:
    """Per-isin 52-week momentum metric for Test 1.

    mode "raw"    -> 52-week return (yesterday's close).
    mode "voladj" -> that return * (TYPICAL_VOL / realized annual vol): return per
                     unit of risk, kept in return-units so the scorer's existing
                     linear map is unchanged (a fair raw-vs-voladj comparison).
    Stocks without a full 52w+1 history are omitted (treated as no momentum).
    """
    out: dict[str, float] = {}
    for isin, s in closes_by_isin.items():
        if len(s) <= _MOM_W52 or s[-_MOM_W52] <= 0:
            continue
        raw = (s[-2] - s[-_MOM_W52]) / s[-_MOM_W52]
        if mode != "voladj":
            out[isin] = raw
            continue
        window = s[-(_MOM_W52 + 1):-1]  # ~252 closes ending yesterday (no lookahead)
        rets = [
            window[k] / window[k - 1] - 1.0
            for k in range(1, len(window))
            if window[k - 1] > 0
        ]
        if len(rets) < 2:
            out[isin] = raw
            continue
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        vol = (var ** 0.5) * (_MOM_W52 ** 0.5)
        out[isin] = raw * (_MOM_TYPICAL_VOL / max(vol, _MOM_VOL_FLOOR))
    return out


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
    # Config F: (rebalance_date, target_exposure) trace for the cash-exposure report.
    exposure_trace: list[tuple[date, Decimal]] = field(default_factory=list)


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
# Config E: regime detection + per-stock beta vs the REAL Nifty 500 TRI.
# Every read is bounded by `trade_date <= :as_of` (no lookahead, asserted).
# ---------------------------------------------------------------------------
_MIN_BETA_OBS = 60  # min aligned daily returns to trust a beta estimate

_SQL_INDEX_ASOF = text(
    "SELECT trade_date, index_value FROM benchmark_index "
    "WHERE index_name = :name AND trade_date <= :as_of "
    "ORDER BY trade_date DESC LIMIT :n"
)
_SQL_DATED_CLOSES = text(
    """
    SELECT isin, trade_date, adj_close
    FROM prices_eod_adjusted
    WHERE trade_date BETWEEN :start AND :as_of
      AND adj_close IS NOT NULL
      AND isin = ANY(:isins)
    ORDER BY isin, trade_date
    """
).bindparams(bindparam("isins"))


async def _index_series_asof(
    session: AsyncSession, name: str, as_of: date, n: int
) -> list[tuple[date, Decimal]]:
    """Last `n` (date, value) index rows with trade_date <= as_of, ascending."""
    rows = (
        await session.execute(_SQL_INDEX_ASOF, {"name": name, "as_of": as_of, "n": n})
    ).all()
    series = [(d, Decimal(v)) for d, v in rows][::-1]
    for d, _v in series:
        assert d <= as_of, f"lookahead: index {d} > as_of {as_of}"
    return series


async def _index_closes_asof(
    session: AsyncSession, name: str, as_of: date, n: int
) -> list[Decimal]:
    """Just the close values (ascending) of the last `n` index rows <= as_of."""
    return [v for _d, v in await _index_series_asof(session, name, as_of, n)]


async def _compute_betas(
    session: AsyncSession, isins: list[str], as_of: date, cfg: BacktestConfig
) -> dict[str, Decimal]:
    """Per-stock beta vs the Nifty 500 TRI over the trailing `cfg.beta_window` days,
    from prices/index values <= as_of (no lookahead; asserted). Stocks with fewer
    than `_MIN_BETA_OBS` aligned daily returns are omitted (insufficient history)."""
    idx = await _index_series_asof(session, "nifty500_tri", as_of, cfg.beta_window + 1)
    idx = trailing_window(idx, as_of, cfg.beta_window + 1)
    if len(idx) < _MIN_BETA_OBS + 1:
        return {}
    idx_dates = [d for d, _ in idx]
    idx_val = dict(idx)
    start = as_of - timedelta(days=int(cfg.beta_window * 1.7) + 15)
    rows = (
        await session.execute(
            _SQL_DATED_CLOSES, {"start": start, "as_of": as_of, "isins": list(isins)}
        )
    ).all()
    by_isin: dict[str, dict[date, Decimal]] = {}
    for isin, td, ac in rows:
        assert td <= as_of, f"lookahead: price {td} > as_of {as_of}"
        by_isin.setdefault(isin, {})[td] = ac
    betas: dict[str, Decimal] = {}
    for isin, dmap in by_isin.items():
        common = [d for d in idx_dates if d in dmap]
        if len(common) < _MIN_BETA_OBS + 1:
            continue
        s_returns = period_returns([dmap[d] for d in common])
        i_returns = period_returns([idx_val[d] for d in common])
        b = beta(s_returns, i_returns)
        if b is not None:
            betas[isin] = b
    return betas


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
async def run_backtest(session: AsyncSession, cfg: BacktestConfig) -> BacktestResult:
    """Walk-forward backtest. Returns aggregated metrics + the equity curve.

    Read-only: every SQL has `trade_date <= as_of` or BETWEEN(start, as_of).
    Writes nothing to stock_rankings, outcome_log, or any live table.
    """
    # Config F: cash-aware quality-momentum allocator (graded_exposure ON) uses a
    # different simulator — persistent holdings + a cash sleeve + a daily blended
    # equity curve. A/B/C/D/E (graded_exposure OFF) fall through unchanged.
    if cfg.graded_exposure:
        return await run_backtest_f(session, cfg)
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

    history_start = _history_start(days[0], cfg.history_floor)
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

        # ---- Config E: regime switch — rotate to low-beta defensives in risk-off.
        # RISK-ON leaves the full universe (= Config C); RISK-OFF restricts the
        # candidate set to the lowest-beta defensive pool. Always stays invested.
        if cfg.regime_switching:
            idx_closes = await _index_closes_asof(
                session, "nifty500_tri", rebalance_date, max(cfg.beta_window + 5, 260)
            )
            if detect_regime(idx_closes) == "risk_off":
                betas = await _compute_betas(
                    session, list(scores.keys()), rebalance_date, cfg
                )
                defensive = classify_defensive_pool(betas, cfg.defensive_pool_pct)
                if defensive:
                    scores = {i: s for i, s in scores.items() if i in defensive}
        # ------------------------------------------------------------------------

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


def _history_start(first_rebalance: date, floor: date | None = None) -> date:
    """A buffer-comfortable start for the history SQL — at least 1 year prior.

    `floor` (Config F+ history_floor) clamps the start so warmup never reads price
    history before it — used to keep 2021-2026 warmup native-only, off the
    2021-05-26 yfinance/native adjustment seam. None = no clamp (A-F unchanged).
    """
    start = first_rebalance - timedelta(days=_WARMUP_DAYS * 2)
    return max(start, floor) if floor is not None else start


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


# ===========================================================================
# Config F — cash-aware quality-momentum allocator (Components 0-5). Persistent
# low-turnover portfolio + a graded cash sleeve; metrics on the DAILY blended
# equity curve. Read-only; every DECISION uses data <= the rebalance date.
# ===========================================================================
@dataclass(frozen=True)
class _FPos:
    shares: Decimal
    entry_date: date
    entry_price: Decimal


_W52_F = 252  # trailing window for the low-vol quality proxy
_QUALITY_DE_MAX = Decimal("1.5")  # debt/equity ceiling (post-2024 fundamentals path)

_SQL_FUND_QUALITY = text(
    """
    SELECT DISTINCT ON (isin) isin, roe, debt_to_equity
    FROM fundamental_signals_historical
    WHERE publication_date <= :as_of AND isin = ANY(:isins)
    ORDER BY isin, publication_date DESC
    """
).bindparams(bindparam("isins"))


async def _quality_set(
    session: AsyncSession,
    isins: list[str],
    as_of: date,
    closes: dict[str, list[float]],
    cfg: BacktestConfig,
) -> tuple[set[str], dict[str, float]]:
    """Component 1 quality gate (data <= as_of). Post-2024: ROE > 0 AND debt/equity
    below ceiling. Pre-2024 (no fundamentals): low-volatility proxy — drop the
    highest-vol tertile by trailing-252 realized vol. All isins pass when the gate
    is off. Fundamentals are read with publication_date <= as_of (SQL-enforced).

    Returns (eligible set, no-fundamentals vols) — the vols feed the F+ quality
    breakdown cutoff."""
    if not cfg.quality_gate:
        return set(isins), {}
    rows = (
        await session.execute(_SQL_FUND_QUALITY, {"as_of": as_of, "isins": list(isins)})
    ).all()
    have_fund: set[str] = set()
    fund_pass: set[str] = set()
    for isin, roe, de in rows:
        have_fund.add(isin)
        if (
            roe is not None
            and Decimal(roe) > 0
            and (de is None or Decimal(de) < _QUALITY_DE_MAX)
        ):
            fund_pass.add(isin)
    vols: dict[str, float] = {}
    for isin in isins:
        if isin in have_fund:
            continue
        series = closes.get(isin, [])
        if len(series) < _W52_F + 1:
            continue
        window = series[-(_W52_F + 1):]
        rets = [
            (window[k] - window[k - 1]) / window[k - 1]
            for k in range(1, len(window))
            if window[k - 1] != 0
        ]
        v = realized_vol(rets)
        if v is not None:
            vols[isin] = v
    return fund_pass | low_vol_pass(vols), vols


def _select_target_f(
    keep_sorted: list[str],
    ranked: list[str],
    sector_by: dict[str, str],
    cfg: BacktestConfig,
) -> set[str]:
    """Component 3/4: hold retained winners first (rank order), then fill to top_n
    with the best new names, capping each sector at max_per_sector."""
    target: list[str] = []
    per_sec: dict[str, int] = {}

    def _add(isin: str) -> None:
        sec = sector_by.get(isin, "(unknown)")
        cap = cfg.max_per_sector
        if cap is not None and per_sec.get(sec, 0) >= cap:
            return
        target.append(isin)
        per_sec[sec] = per_sec.get(sec, 0) + 1

    for h in keep_sorted:
        if len(target) >= cfg.top_n:
            break
        _add(h)
    for isin in ranked:
        if len(target) >= cfg.top_n:
            break
        if isin not in target:
            _add(isin)
    return set(target)


def _f_trade(
    pos: _FPos, isin: str, exit_date: date, exit_price: Decimal,
    exit_reason: str = "rebalance",
) -> Trade:
    """A completed round-trip for the trade table. The headline P&L/return/DD come
    from the daily curve; this per-name record is illustrative (price return over
    the holding, P&L on the exit-date share count). exit_reason is "rebalance" or
    "breakdown" (Config F+ cut)."""
    pnl = ((exit_price - pos.entry_price) * pos.shares).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )
    ret = (
        ((exit_price - pos.entry_price) / pos.entry_price * 100).quantize(
            _Q2, rounding=ROUND_HALF_EVEN
        )
        if pos.entry_price
        else Decimal("0")
    )
    return Trade(
        isin=isin, entry_date=pos.entry_date, exit_date=exit_date,
        entry_price=pos.entry_price, exit_price=exit_price, qty=pos.shares,
        gross_pnl=pnl, net_pnl=pnl, gross_return_pct=ret, score=Decimal("0"),
        exit_reason=exit_reason,
    )


async def run_backtest_f(session: AsyncSession, cfg: BacktestConfig) -> BacktestResult:
    """Config F — cash-aware quality-momentum allocator. Persistent low-turnover
    portfolio (hold winners within a momentum-rank buffer), top_n names, sector cap;
    a graded cash sleeve (Component 5) protects capital in risk-off. All metrics are
    computed on the DAILY BLENDED equity curve (invested sleeve marked daily + flat
    cash). Read-only; every decision (exposure, quality, scores, target) uses data
    <= the rebalance date (helper-level asserts on the index/price fetches)."""
    if cfg.end_date <= cfg.start_date:
        raise ValueError("end_date must be > start_date")
    days = await _trading_days(session, cfg.start_date, cfg.end_date)
    if len(days) < 2:
        raise ValueError(f"not enough trading days ({len(days)})")
    isins = await _active_isins(session)
    sector_by = await _sectors_map(session, isins)
    history_start = _history_start(days[0], cfg.history_floor)
    rebal = [i for i in range(0, len(days), cfg.rebalance_every) if i < len(days) - 1]
    # Config F+ Change 1: full TRI series (<= end) for the decoupled WEEKLY exposure
    # check; sliced to <= each check date (no lookahead). Empty unless F+ is on.
    tri_all = (
        await _index_series_asof(session, "nifty500_tri", cfg.end_date, 10_000_000)
        if cfg.exposure_check_days is not None
        else []
    )
    log.info(
        "backtest.f.start", start=cfg.start_date.isoformat(),
        end=cfg.end_date.isoformat(), trading_days=len(days),
        rebalances=len(rebal), active_isins=len(isins),
    )

    cash = cfg.starting_capital
    positions: dict[str, _FPos] = {}
    daily: list[tuple[date, Decimal]] = [(days[0], cfg.starting_capital)]
    trades: list[Trade] = []
    total_costs = Decimal("0")
    exposure_trace: list[tuple[date, Decimal]] = []

    for ri, i in enumerate(rebal):
        rebalance_date = days[i]
        end_i = rebal[ri + 1] if ri + 1 < len(rebal) else len(days) - 1
        d_end = days[end_i]
        price_d = await _adj_close_on(session, isins, rebalance_date)
        invested_val = sum(
            (positions[h].shares * price_d[h] for h in positions if h in price_d),
            Decimal("0"),
        )
        total = invested_val + cash

        idx_closes = await _index_closes_asof(
            session, "nifty500_tri", rebalance_date, max(cfg.beta_window + 5, 260)
        )
        target_exp = (
            target_exposure_for_regime(idx_closes)
            if cfg.graded_exposure
            else Decimal("1.0")
        )
        exposure_trace.append((rebalance_date, target_exp))

        closes, vols_hist = await _fetch_history(
            session, isins, start=history_start, as_of=rebalance_date
        )
        # Test 1 (Phase-2 branch): precompute the momentum metric once per rebalance
        # (None for frozen F+ where momentum_mode == "off" -> scorer stays neutral).
        mom_metric = (
            _momentum_metric(closes, cfg.momentum_mode)
            if cfg.momentum_mode != "off"
            else None
        )
        quality, qvols = await _quality_set(session, isins, rebalance_date, closes, cfg)
        # F+ quality-breakdown cutoff: a held name whose trailing vol later exceeds
        # this rebalance-time boundary has broken down on quality (low-vol proxy).
        qual_cutoff = (
            low_vol_cutoff(qvols)
            if (cfg.breakdown_exit_pct is not None and cfg.quality_gate and qvols)
            else None
        )
        macro_score = await reconstruct_macro_score(session, rebalance_date)
        sector_sig = await _sector_signals_on(session, isins, rebalance_date)
        scores: dict[str, Decimal] = {}
        for isin in quality:
            sc = await compute_full_composite(
                session, isin, rebalance_date, closes.get(isin, []),
                vols_hist.get(isin), macro_score=macro_score,
                sector_signal=sector_sig.get(isin, "neutral"),
                mom_metric=mom_metric,
            )
            if sc is not None:
                scores[isin] = sc
        ranked = [k for k, _v in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
        rank_of = {isin: r for r, isin in enumerate(ranked)}
        keep = sorted(
            (h for h in positions if h in rank_of and rank_of[h] < cfg.hold_buffer_rank),
            key=lambda h: rank_of[h],
        )
        target = _select_target_f(keep, ranked, sector_by, cfg)

        # SELL anything not retained -> cash (record round-trip + cost)
        for h in list(positions):
            if h not in target:
                px = price_d.get(h) or positions[h].entry_price
                proceeds = positions[h].shares * px
                cost = cost_on_notional(proceeds)
                total_costs += cost
                cash += proceeds - cost
                trades.append(_f_trade(positions[h], h, rebalance_date, px))
                del positions[h]

        # resize/establish target names to equal weight of the invested sleeve
        invested_target, _cash_target = split_capital(total, target_exp)
        tradeable = [t for t in target if price_d.get(t, Decimal("0")) > 0]
        per_name = (
            invested_target / Decimal(len(tradeable)) if tradeable else Decimal("0")
        )
        for isin in tradeable:
            px = price_d[isin]
            cur_val = positions[isin].shares * px if isin in positions else Decimal("0")
            diff = per_name - cur_val
            total_costs += cost_on_notional(abs(diff))
            cash -= diff + cost_on_notional(abs(diff))
            prev = positions.get(isin)
            positions[isin] = _FPos(
                per_name / px,
                prev.entry_date if prev else rebalance_date,
                prev.entry_price if prev else px,
            )

        # daily blended curve: each trading day after D through the next rebalance
        held = list(positions.keys())
        paths = await _daily_paths(session, held, rebalance_date, d_end)
        by_date: dict[date, dict[str, Decimal]] = {}
        for isin, series in paths.items():
            for dt, px in series:
                by_date.setdefault(dt, {})[isin] = px
        last_px = {h: price_d.get(h) for h in held}

        if cfg.exposure_check_days is None and cfg.breakdown_exit_pct is None:
            # Plain F: static marking (positions + cash fixed between rebalances).
            for d in days[i + 1 : end_i + 1]:
                dmap = by_date.get(d, {})
                inv = Decimal("0")
                for h in held:
                    px = dmap.get(h) or last_px.get(h)
                    if px is not None:
                        last_px[h] = px
                        inv += positions[h].shares * px
                daily.append((d, (inv + cash).quantize(_Q2, rounding=ROUND_HALF_EVEN)))
        else:
            # Config F+: daily breakdown cuts (Change 2) + weekly exposure scaling
            # (Change 1). positions + cash mutate intra-quarter; names re-selected
            # only at the quarterly rebalance.
            cur_exp = target_exp
            hist = (
                {h: list(closes.get(h, []))[-_W52_F:] for h in held}
                if qual_cutoff is not None
                else {}
            )
            since_check = 0
            for d in days[i + 1 : end_i + 1]:
                dmap = by_date.get(d, {})
                since_check += 1
                for h in list(positions):
                    px = dmap.get(h) or last_px.get(h)
                    if px is not None:
                        last_px[h] = px
                        if h in hist:
                            hist[h].append(float(px))
                # Change 2: daily price breakdown (cut >= breakdown_exit_pct below entry)
                if cfg.breakdown_exit_pct is not None:
                    for h in list(positions):
                        px = last_px.get(h)
                        if px is not None and breaks_down(
                            px, positions[h].entry_price, cfg.breakdown_exit_pct, False
                        ):
                            proceeds = positions[h].shares * px
                            c = cost_on_notional(proceeds)
                            total_costs += c
                            cash += proceeds - c
                            trades.append(_f_trade(positions[h], h, d, px, "breakdown"))
                            del positions[h]
                # weekly cadence (Change 1): quality breakdown + exposure re-check
                if (
                    cfg.exposure_check_days is not None
                    and since_check >= cfg.exposure_check_days
                ):
                    since_check = 0
                    if qual_cutoff is not None:
                        for h in list(positions):
                            ser = hist.get(h, [])
                            if len(ser) < 30:
                                continue
                            w = ser[-(_W52_F + 1):]
                            rets = [
                                (w[k] - w[k - 1]) / w[k - 1]
                                for k in range(1, len(w))
                                if w[k - 1] != 0
                            ]
                            v = realized_vol(rets)
                            px = last_px.get(h)
                            if v is not None and v > qual_cutoff and px is not None:
                                proceeds = positions[h].shares * px
                                c = cost_on_notional(proceeds)
                                total_costs += c
                                cash += proceeds - c
                                trades.append(
                                    _f_trade(positions[h], h, d, px, "breakdown")
                                )
                                del positions[h]
                    new_exp = target_exposure_for_regime(
                        [v for dt, v in tri_all if dt <= d]
                    )
                    if new_exp != cur_exp:
                        inv = sum(
                            (positions[h].shares * last_px[h]
                             for h in positions if last_px.get(h)),
                            Decimal("0"),
                        )
                        if inv > 0:
                            total_now = inv + cash
                            target_inv, _c = split_capital(total_now, new_exp)
                            c = cost_on_notional(abs(target_inv - inv))
                            total_costs += c
                            cash += (inv - target_inv) - c
                            factor = target_inv / inv
                            for h in list(positions):
                                p = positions[h]
                                positions[h] = _FPos(
                                    p.shares * factor, p.entry_date, p.entry_price
                                )
                        cur_exp = new_exp
                        exposure_trace.append((d, new_exp))
                # daily mark on the (possibly mutated) book
                inv = sum(
                    (positions[h].shares * last_px[h]
                     for h in positions if last_px.get(h)),
                    Decimal("0"),
                )
                daily.append((d, (inv + cash).quantize(_Q2, rounding=ROUND_HALF_EVEN)))

    # mark remaining open positions to the final close for the trade table
    final_day = days[-1]
    final_px = await _adj_close_on(session, list(positions.keys()), final_day)
    for h in list(positions):
        px = final_px.get(h) or positions[h].entry_price
        trades.append(_f_trade(positions[h], h, final_day, px))

    # ---- metrics on the DAILY blended curve ----
    curve_dates = [d for d, _ in daily]
    bot_values = [v for _, v in daily]
    end_value = bot_values[-1]
    years = Decimal((cfg.end_date - cfg.start_date).days) / Decimal("365.25")
    total_return = ((end_value / cfg.starting_capital - 1) * 100).quantize(
        _Q2, rounding=ROUND_HALF_EVEN
    )
    bot_returns = period_returns(bot_values)
    ppy = Decimal("252")
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
        n500_ret = n500_cagr = n500_alpha = n500_beta = None

    result = BacktestResult(
        config=cfg,
        start_value=cfg.starting_capital,
        end_value=end_value,
        total_return_pct=total_return,
        cagr_pct=cagr_pct(cfg.starting_capital, end_value, years),
        max_drawdown_pct=max_drawdown_pct(bot_values),
        win_rate_pct=win_rate_pct(trades),
        total_trades=len(trades),
        total_costs_paid=total_costs.quantize(_Q2, rounding=ROUND_HALF_EVEN),
        equity_curve=daily,
        nifty500_tri_return_pct=n500_ret,
        nifty500_tri_cagr_pct=n500_cagr,
        alpha_vs_nifty500_tri_pct=n500_alpha,
        beta_vs_nifty500_tri=n500_beta,
        sharpe=sharpe_ratio(bot_returns, _RISK_FREE_ANNUAL, ppy),
        sortino=sortino_ratio(bot_returns, _RISK_FREE_ANNUAL, ppy),
        profit_factor=profit_factor(trades),
        avg_win_pct=avg_win_pct(trades),
        avg_loss_pct=avg_loss_pct(trades),
        sector_exposure=await _sector_exposure(session, trades),
        trades=trades,
        exposure_trace=exposure_trace,
    )
    log.info(
        "backtest.f.done", trades=len(trades), total_return_pct=str(total_return),
        maxdd=str(result.max_drawdown_pct), n500=str(n500_ret),
        sharpe=str(result.sharpe),
    )
    return result
