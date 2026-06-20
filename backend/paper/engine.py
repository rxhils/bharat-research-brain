"""Multi-portfolio forward paper-trading engine.

Each portfolio is a separate book in ONE shared database, separated by
`portfolio_id` (the tag IS the separation — not a separate DB). The flagship
"Quant" book runs ENHANCED F+ (commit 6ced078) forward at real prices: it calls
the validated decision functions verbatim (`_quality_set`, `compute_full_composite`
with vol-adjusted momentum, `_select_target_f`, `target_exposure_for_regime`,
`breaks_down`, `split_capital`) once per real calendar day, and credits idle cash at
6.5%/yr. F+ classic remains the preserved fallback (backend/backtest/configs.py).

NO LOOKAHEAD: every decision on date D reads only data with trade_date/computed_date
<= D. The track record starts at inception and only grows forward; nothing is
backfilled.

Lifecycle per portfolio:
  create_book        -> empty-cash account (capital in cash, 0 holdings, no curve)
  first_allocation   -> the FIRST real picks at/after inception (Monday for Quant)
  daily_mark         -> mark-to-market + cut-on-breakdown (every trading day)
  weekly_exposure    -> regime -> exposure rescale (every 5 trading days)
  quarterly_rebalance-> full Enhanced-F+ re-pick (every 63 trading days)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

import structlog
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.backtest import runner as R
from backend.backtest.cost_model import cost_on_notional
from backend.backtest.engine import (
    BacktestConfig,
    breaks_down,
    split_capital,
    target_exposure_for_regime,
)
from backend.backtest.scores import compute_full_composite, reconstruct_macro_score

log = structlog.get_logger()

_Q2 = Decimal("0.01")
_Q4 = Decimal("0.0001")
STARTING_CAPITAL = Decimal("1000000")
EXPOSURE_CHECK_DAYS = 5
REBALANCE_DAYS = 63
BREAKDOWN_PCT = Decimal("0.15")
# Enhanced-F+ adoption (commit 6ced078): the two gauntlet winners, applied live.
MOMENTUM_MODE = "voladj"               # vol-adjusted 52w momentum in the composite
CASH_YIELD_ANNUAL = Decimal("0.065")   # idle cash earns 6.5%/yr, accrued daily

# ENHANCED F+ parameters — F+ classic skeleton (== commit 6417a74) + vol-adjusted
# momentum. Cash yield is applied in daily_mark (the engine hand-rolls cash, so it
# is NOT auto-read from cfg). F+ classic stays available in backend/backtest/configs.py.
_FPLUS = dict(
    top_n=25, hold_days=REBALANCE_DAYS, rebalance_every=REBALANCE_DAYS,
    min_score=Decimal("0"), use_full_composite=True, benchmark_weighting="equal",
    apply_breadth_filter=False, quality_gate=True, graded_exposure=True,
    hold_buffer_rank=40, max_per_sector=4, turnover_mode="low",
    exposure_check_days=EXPOSURE_CHECK_DAYS, breakdown_exit_pct=BREAKDOWN_PCT,
    momentum_mode=MOMENTUM_MODE, cash_yield_annual=CASH_YIELD_ANNUAL,
)


def fplus_cfg(as_of: date) -> BacktestConfig:
    """An Enhanced-F+ BacktestConfig for single-date scoring (start/end are nominal)."""
    return BacktestConfig(
        start_date=as_of - timedelta(days=1), end_date=as_of,
        starting_capital=STARTING_CAPITAL, **_FPLUS,
    )


# ---------------------------------------------------------------------------
# Pure accounting helpers (unit-tested) — UNCHANGED. Component 0 of F+.
# ---------------------------------------------------------------------------
def size_book(
    equity: Decimal, exposure: Decimal, prices: dict[str, Decimal]
) -> tuple[dict[str, tuple[Decimal, Decimal]], Decimal]:
    """Equal-weight the invested sleeve (exposure*equity) across the priced names;
    the rest is cash. Returns ({isin: (shares, value)}, cash). Uses frozen
    split_capital so the cash sleeve matches F+ exactly."""
    invested, _cash = split_capital(equity, exposure)
    names = [i for i, p in prices.items() if p and p > 0]
    if not names:
        return {}, equity
    per = (invested / Decimal(len(names))).quantize(_Q2, rounding=ROUND_HALF_EVEN)
    book = {i: (per / prices[i], per) for i in names}
    return book, equity - per * Decimal(len(names))


def scale_to_exposure(
    invested: Decimal, cash: Decimal, new_exposure: Decimal
) -> tuple[Decimal, Decimal, Decimal]:
    """Scale the invested sleeve toward new_exposure of total equity; move the diff
    to/from cash. Returns (share_factor, traded_notional, new_cash). factor=1 and no
    trade if there is nothing invested to scale."""
    total = invested + cash
    target, _ = split_capital(total, new_exposure)
    if invested <= 0:
        return Decimal("1"), Decimal("0"), cash
    return (target / invested), abs(target - invested), total - target


@dataclass(frozen=True)
class Snapshot:
    """Enhanced-F+ decision for one calendar day (all from data <= as_of)."""
    as_of: date
    target: list[str]
    scores: dict[str, Decimal]
    exposure: Decimal
    prices: dict[str, Decimal]
    sector_by: dict[str, str]


async def compute_fplus_snapshot(
    session: AsyncSession, as_of: date, current_isins: set[str]
) -> Snapshot:
    """Run the ENHANCED F+ selection + exposure for `as_of` (mechanical composite,
    vol-adjusted momentum ON). Reuses the runner's F+ helpers verbatim. NO LOOKAHEAD:
    every fetch is bounded <= as_of. (Reads price/index tables only — not paper_*.)"""
    cfg = fplus_cfg(as_of)
    isins = await R._active_isins(session)
    sector_by = await R._sectors_map(session, isins)
    hist_start = R._history_start(as_of, None)  # forward dates: native, no seam
    closes, vols = await R._fetch_history(session, isins, start=hist_start, as_of=as_of)
    # Enhanced F+: vol-adjusted 52w momentum metric, precomputed once per snapshot.
    mom_metric = (
        R._momentum_metric(closes, MOMENTUM_MODE) if MOMENTUM_MODE != "off" else None
    )
    quality, _qvols = await R._quality_set(session, isins, as_of, closes, cfg)
    macro = await reconstruct_macro_score(session, as_of)
    sector_sig = await R._sector_signals_on(session, isins, as_of)
    scores: dict[str, Decimal] = {}
    for isin in quality:
        sc = await compute_full_composite(
            session, isin, as_of, closes.get(isin, []), vols.get(isin),
            macro_score=macro, sector_signal=sector_sig.get(isin, "neutral"),
            mom_metric=mom_metric,
        )
        if sc is not None:
            scores[isin] = sc
    ranked = [k for k, _v in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))]
    rank_of = {isin: r for r, isin in enumerate(ranked)}
    keep = sorted(
        (h for h in current_isins if h in rank_of and rank_of[h] < cfg.hold_buffer_rank),
        key=lambda h: rank_of[h],
    )
    target = list(R._select_target_f(keep, ranked, sector_by, cfg))
    idx_closes = await R._index_closes_asof(
        session, "nifty500_tri", as_of, max(cfg.beta_window + 5, 260)
    )
    exposure = target_exposure_for_regime(idx_closes)
    prices = await R._adj_close_on(session, target, as_of)
    return Snapshot(as_of, target, scores, exposure, prices, sector_by)


# ---------------------------------------------------------------------------
# Portfolio registry + persistence (raw SQL; all paper_* scoped by portfolio_id)
# ---------------------------------------------------------------------------
_SQL_PORTFOLIO_BY_NAME = text(
    "SELECT id, name, status, inception_date, starting_capital FROM portfolios "
    "WHERE name = :name"
)
_SQL_PORTFOLIOS_LIVE = text(
    "SELECT id, name, inception_date, starting_capital FROM portfolios "
    "WHERE status = 'live' ORDER BY name"
)
_SQL_ACCOUNT = text(
    "SELECT id, inception_date, current_cash, current_equity FROM paper_account "
    "WHERE portfolio_id = :pid LIMIT 1"
)
_SQL_OPEN = text(
    "SELECT id, isin, entry_date, entry_price, shares, exposure_at_entry "
    "FROM paper_position WHERE status='open' AND portfolio_id = :pid"
)
_SQL_INS_ACCOUNT = text(
    "INSERT INTO paper_account (portfolio_id, inception_date, starting_capital, "
    "current_cash, current_equity, engine_version, score_source) "
    "VALUES (:pid, :d, :cap, :cash, :eq, :ev, :src) RETURNING id"
)
_SQL_INS_POS = text(
    "INSERT INTO paper_position (portfolio_id, isin, entry_date, entry_price, shares, "
    "exposure_at_entry) VALUES (:pid, :isin, :d, :px, :sh, :exp)"
)
_SQL_CLOSE_POS = text(
    "UPDATE paper_position SET status='closed', exit_date=:d, exit_price=:px, "
    "exit_reason=:r WHERE id=:id"
)
_SQL_RESIZE = text("UPDATE paper_position SET shares=:sh WHERE id=:id")
_SQL_RESIZE_EXP = text(
    "UPDATE paper_position SET shares=:sh, exposure_at_entry=:e WHERE id=:id"
)
_SQL_UPD_ACCOUNT = text(
    "UPDATE paper_account SET current_cash=:cash, current_equity=:eq, "
    "last_updated=now() WHERE id=:id"
)
_SQL_INS_CURVE = text(
    "INSERT INTO paper_equity_curve (portfolio_id, trade_date, total_equity, "
    "invested_value, cash_value, exposure_level, nifty500_tri, drawdown_pct) "
    "VALUES (:pid, :d, :eq, :inv, :cash, :exp, :tri, :dd) "
    "ON CONFLICT (portfolio_id, trade_date) DO UPDATE SET total_equity=:eq, "
    "invested_value=:inv, cash_value=:cash, exposure_level=:exp, nifty500_tri=:tri, "
    "drawdown_pct=:dd"
)
_SQL_EVENT = text(
    "INSERT INTO paper_event_log (portfolio_id, trade_date, event_type, detail) "
    "VALUES (:pid, :d, :t, :detail)"
)
_SQL_PEAK = text(
    "SELECT MAX(total_equity) FROM paper_equity_curve WHERE portfolio_id = :pid"
)
_SQL_CURVE_COUNT = text(
    "SELECT COUNT(*) FROM paper_equity_curve WHERE portfolio_id = :pid"
)
_SQL_TRI_ASOF = text(
    "SELECT index_value FROM benchmark_index WHERE index_name='nifty500_tri' "
    "AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1"
)
_SQL_PRICES = text(
    "SELECT isin, adj_close FROM prices_eod_adjusted WHERE trade_date=:d "
    "AND adj_close IS NOT NULL AND isin = ANY(:isins)"
).bindparams(bindparam("isins"))


async def get_portfolio(session: AsyncSession, name: str) -> dict | None:
    row = (await session.execute(_SQL_PORTFOLIO_BY_NAME, {"name": name})).first()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "status": row[2],
            "inception_date": row[3],
            "starting_capital": Decimal(row[4]) if row[4] is not None else None}


async def live_portfolios(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(_SQL_PORTFOLIOS_LIVE)).all()
    return [{"id": r[0], "name": r[1], "inception_date": r[2],
             "starting_capital": Decimal(r[3]) if r[3] is not None else STARTING_CAPITAL}
            for r in rows]


async def _log_event(session: AsyncSession, pid: int, d: date, t: str, detail: str) -> None:
    await session.execute(_SQL_EVENT, {"pid": pid, "d": d, "t": t, "detail": detail})


async def get_account(session: AsyncSession, portfolio_id: int) -> dict | None:
    row = (await session.execute(_SQL_ACCOUNT, {"pid": portfolio_id})).first()
    if row is None:
        return None
    return {"id": row[0], "inception_date": row[1], "cash": Decimal(row[2]),
            "equity": Decimal(row[3]), "portfolio_id": portfolio_id}


async def has_started(session: AsyncSession, portfolio_id: int) -> bool:
    """True once the book has at least one equity-curve row (i.e. first_allocation ran)."""
    n = (await session.execute(_SQL_CURVE_COUNT, {"pid": portfolio_id})).scalar_one()
    return n > 0


async def _open_positions(session: AsyncSession, pid: int) -> list[dict]:
    return [{"id": r[0], "isin": r[1], "entry_date": r[2], "entry_price": Decimal(r[3]),
             "shares": Decimal(r[4]), "exposure": Decimal(r[5])}
            for r in (await session.execute(_SQL_OPEN, {"pid": pid})).all()]


async def _prices_on(session: AsyncSession, isins: list[str], d: date) -> dict[str, Decimal]:
    if not isins:
        return {}
    rows = (await session.execute(_SQL_PRICES, {"d": d, "isins": isins})).all()
    return {i: Decimal(c) for i, c in rows}


async def _write_curve(
    session: AsyncSession, pid: int, d: date, invested: Decimal, cash: Decimal,
    exposure: Decimal,
) -> None:
    total = invested + cash
    peak = (await session.execute(_SQL_PEAK, {"pid": pid})).scalar()
    peak = max(Decimal(peak), total) if peak is not None else total
    dd = ((peak - total) / peak * 100).quantize(_Q2) if peak > 0 else Decimal("0")
    tri = (await session.execute(_SQL_TRI_ASOF, {"d": d})).scalar()
    await session.execute(_SQL_INS_CURVE, {
        "pid": pid, "d": d, "eq": total.quantize(_Q2), "inv": invested.quantize(_Q2),
        "cash": cash.quantize(_Q2), "exp": exposure,
        "tri": Decimal(tri).quantize(_Q4) if tri is not None else None, "dd": dd})


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
async def create_book(
    session: AsyncSession, portfolio_id: int, inception_date: date,
    starting_capital: Decimal = STARTING_CAPITAL, *, dry_run: bool = False,
) -> dict:
    """Create an EMPTY-CASH book: full capital in cash, 0 holdings, NO curve row yet.
    The first real picks happen at first_allocation on/after inception_date. Refuses
    to double-create (idempotent per portfolio)."""
    if await get_account(session, portfolio_id) is not None and not dry_run:
        raise RuntimeError(f"paper_account already exists for portfolio {portfolio_id}")
    result = {"portfolio_id": portfolio_id, "inception_date": inception_date,
              "cash": starting_capital, "holdings": 0}
    if dry_run:
        return result
    acct_id = (await session.execute(_SQL_INS_ACCOUNT, {
        "pid": portfolio_id, "d": inception_date, "cap": starting_capital.quantize(_Q2),
        "cash": starting_capital.quantize(_Q2), "eq": starting_capital.quantize(_Q2),
        "ev": "Enhanced F+ 6ced078", "src": "mechanical"})).scalar_one()
    await _log_event(session, portfolio_id, inception_date, "book_created",
                     f"Empty-cash book created: Rs {starting_capital:.0f}, 0 holdings, "
                     f"inception {inception_date} (Enhanced F+ 6ced078). Awaiting first run.")
    await session.commit()
    return result | {"account_id": acct_id}


async def first_allocation(
    session: AsyncSession, portfolio_id: int, as_of: date, *, dry_run: bool = False,
) -> dict:
    """The FIRST real picks: deploy the empty-cash book into the Enhanced-F+ book at
    `as_of` EOD prices. Writes the first equity-curve row. NO LOOKAHEAD / NO backfill."""
    acct = await get_account(session, portfolio_id)
    if acct is None:
        raise RuntimeError(f"no book for portfolio {portfolio_id} — run create_book first")
    if await has_started(session, portfolio_id) and not dry_run:
        raise RuntimeError(f"portfolio {portfolio_id} already started (has a curve)")
    snap = await compute_fplus_snapshot(session, as_of, current_isins=set())
    book, cash = size_book(acct["cash"], snap.exposure, snap.prices)
    rows = [{"isin": isin, "px": snap.prices[isin], "shares": shares, "value": value,
             "sector": snap.sector_by.get(isin, "?")}
            for isin, (shares, value) in book.items()]
    result = {"as_of": as_of, "exposure": snap.exposure, "cash": cash,
              "invested": acct["cash"] - cash, "n": len(rows), "rows": rows,
              "scoreable": len(snap.scores)}
    if dry_run:
        return result
    for isin, (shares, _value) in book.items():
        await session.execute(_SQL_INS_POS, {
            "pid": portfolio_id, "isin": isin, "d": as_of,
            "px": snap.prices[isin].quantize(_Q4), "sh": shares, "exp": snap.exposure})
    invested = acct["cash"] - cash
    await session.execute(_SQL_UPD_ACCOUNT, {
        "cash": cash.quantize(_Q2), "eq": acct["cash"].quantize(_Q2), "id": acct["id"]})
    await _write_curve(session, portfolio_id, as_of, invested, cash, snap.exposure)
    await _log_event(session, portfolio_id, as_of, "first_allocation",
                     f"Enhanced F+ first picks: {len(rows)} names, exposure {snap.exposure}, "
                     f"cash {cash:.0f}, Rs {acct['cash']:.0f} (commit 6ced078)")
    log.info("paper.first_allocation", pid=portfolio_id, as_of=str(as_of),
             names=len(rows), exposure=str(snap.exposure))
    await session.commit()
    return result | {"account_id": acct["id"]}


async def daily_mark(session: AsyncSession, portfolio_id: int, as_of: date) -> dict:
    """EOD: credit idle cash (6.5%/yr, one day), mark open positions to `as_of`
    close, apply cut-on-breakdown (-15% from entry), update the equity curve."""
    acct = await get_account(session, portfolio_id)
    if acct is None:
        raise RuntimeError(f"no book for portfolio {portfolio_id}")
    positions = await _open_positions(session, portfolio_id)
    prices = await _prices_on(session, [p["isin"] for p in positions], as_of)
    cash = acct["cash"]
    if CASH_YIELD_ANNUAL:
        cash = (cash * (Decimal("1") + CASH_YIELD_ANNUAL / Decimal("252"))).quantize(
            _Q2, rounding=ROUND_HALF_EVEN)
    cuts = 0
    for p in positions:
        px = prices.get(p["isin"])
        if px is None:
            continue
        assert as_of >= p["entry_date"], "lookahead: mark date before entry"
        if breaks_down(px, p["entry_price"], BREAKDOWN_PCT, False):
            proceeds = p["shares"] * px
            cash += proceeds - cost_on_notional(proceeds)
            await session.execute(_SQL_CLOSE_POS, {
                "d": as_of, "px": px.quantize(_Q4), "r": "breakdown", "id": p["id"]})
            await _log_event(session, portfolio_id, as_of, "breakdown",
                             f"{p['isin']} cut at {px:.2f} (entry {p['entry_price']:.2f})")
            cuts += 1
    open_now = await _open_positions(session, portfolio_id)
    prices2 = await _prices_on(session, [p["isin"] for p in open_now], as_of)
    invested = sum((p["shares"] * prices2.get(p["isin"], p["entry_price"]) for p in open_now),
                   Decimal("0"))
    exposure = open_now[0]["exposure"] if open_now else Decimal("0")
    await _write_curve(session, portfolio_id, as_of, invested, cash, exposure)
    await session.execute(_SQL_UPD_ACCOUNT, {
        "cash": cash.quantize(_Q2), "eq": (invested + cash).quantize(_Q2), "id": acct["id"]})
    await session.commit()
    return {"date": as_of, "breakdown_cuts": cuts, "equity": invested + cash, "cash": cash}


async def weekly_exposure(session: AsyncSession, portfolio_id: int, as_of: date) -> dict:
    """Weekly: re-check regime; scale the invested sleeve to the new target exposure,
    moving the diff to/from cash (cost on the resized portion)."""
    acct = await get_account(session, portfolio_id)
    positions = await _open_positions(session, portfolio_id)
    idx = await R._index_closes_asof(session, "nifty500_tri", as_of, 260)
    new_exp = target_exposure_for_regime(idx)
    prices = await _prices_on(session, [p["isin"] for p in positions], as_of)
    invested = sum((p["shares"] * prices.get(p["isin"], p["entry_price"]) for p in positions),
                   Decimal("0"))
    cash = acct["cash"]
    cur_exp = positions[0]["exposure"] if positions else new_exp
    if new_exp != cur_exp and invested > 0:
        factor, traded, new_cash = scale_to_exposure(invested, cash, new_exp)
        cash = new_cash - cost_on_notional(traded)
        for p in positions:
            await session.execute(_SQL_RESIZE_EXP,
                                  {"sh": p["shares"] * factor, "e": new_exp, "id": p["id"]})
        await _log_event(session, portfolio_id, as_of, "exposure_change",
                         f"exposure {cur_exp} -> {new_exp} (factor {factor:.3f}, "
                         f"traded {traded:.0f})")
        await session.execute(_SQL_UPD_ACCOUNT, {
            "cash": cash.quantize(_Q2), "eq": (invested * factor + cash).quantize(_Q2),
            "id": acct["id"]})
        await session.commit()
    return {"date": as_of, "exposure": new_exp, "changed": new_exp != cur_exp}


async def quarterly_rebalance(session: AsyncSession, portfolio_id: int, as_of: date) -> dict:
    """Quarterly: full Enhanced-F+ re-pick of the 25 names (hold-winners buffer),
    redeploy cash at the current exposure. Sells names that dropped out; buys new ones."""
    acct = await get_account(session, portfolio_id)
    positions = await _open_positions(session, portfolio_id)
    held = {p["isin"] for p in positions}
    snap = await compute_fplus_snapshot(session, as_of, current_isins=held)
    target = set(snap.target)
    prices = await _prices_on(session, list(held | target), as_of)
    cash = acct["cash"]
    for p in positions:
        if p["isin"] not in target:
            px = prices.get(p["isin"], p["entry_price"])
            proceeds = p["shares"] * px
            cash += proceeds - cost_on_notional(proceeds)
            await session.execute(_SQL_CLOSE_POS, {
                "d": as_of, "px": px.quantize(_Q4), "r": "rebalance", "id": p["id"]})
    survivors = {p["isin"]: p for p in positions if p["isin"] in target}
    invested_val = sum((p["shares"] * prices.get(p["isin"], p["entry_price"])
                        for p in survivors.values()), Decimal("0"))
    total = invested_val + cash
    target_invested, _ = split_capital(total, snap.exposure)
    tradeable = [t for t in snap.target if prices.get(t, Decimal("0")) > 0]
    per = (target_invested / Decimal(len(tradeable))).quantize(_Q2) if tradeable else Decimal("0")
    for isin in tradeable:
        px = prices[isin]
        if isin in survivors:
            await session.execute(_SQL_RESIZE, {"sh": per / px, "id": survivors[isin]["id"]})
        else:
            await session.execute(_SQL_INS_POS, {
                "pid": portfolio_id, "isin": isin, "d": as_of, "px": px.quantize(_Q4),
                "sh": per / px, "exp": snap.exposure})
    cash = total - per * Decimal(len(tradeable))
    await session.execute(_SQL_UPD_ACCOUNT, {
        "cash": cash.quantize(_Q2), "eq": total.quantize(_Q2), "id": acct["id"]})
    await _log_event(session, portfolio_id, as_of, "rebalance",
                     f"quarterly Enhanced-F+ rebalance: {len(tradeable)} names, "
                     f"exposure {snap.exposure}")
    await session.commit()
    return {"date": as_of, "names": len(tradeable), "exposure": snap.exposure}
