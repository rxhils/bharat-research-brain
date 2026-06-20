"""Paper-trading engine — executes the FROZEN F+ strategy forward at real prices.

It does NOT reimplement F+: it calls F+'s decision functions verbatim
(`_quality_set`, `compute_full_composite`, `_select_target_f`,
`target_exposure_for_regime`, `breaks_down`, `split_capital`) and runs them once per
real calendar day against a persistent Rs 10,00,000 book.

NO LOOKAHEAD: every decision on date D reads only data with trade_date/computed_date
<= D — enforced by the runner's `<= :as_of` fetches (asserted there) and re-asserted
here. The track record starts at inception and only grows forward; nothing is
backfilled.

Score source = "mechanical" (the exact compute_full_composite signal F+ was validated
on). The agentic `stock_rankings` feed is a future swap-in once live API keys exist —
documented, not wired, because feeding F+ untested agent scores would not be the
validated engine.
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
# Pure accounting helpers (unit-tested) — Component 0 of F+, applied live.
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
    """F+ decision for one calendar day (all from data <= as_of)."""
    as_of: date
    target: list[str]
    scores: dict[str, Decimal]
    exposure: Decimal
    prices: dict[str, Decimal]
    sector_by: dict[str, str]


async def compute_fplus_snapshot(
    session: AsyncSession, as_of: date, current_isins: set[str]
) -> Snapshot:
    """Run the FROZEN F+ selection + exposure for `as_of` (mechanical composite).

    Reuses the runner's F+ helpers verbatim. `current_isins` are currently-held names
    (so the hold-winners buffer keeps them when still ranked). NO LOOKAHEAD: every
    fetch is bounded <= as_of."""
    cfg = fplus_cfg(as_of)
    isins = await R._active_isins(session)
    sector_by = await R._sectors_map(session, isins)
    hist_start = R._history_start(as_of, None)  # forward dates: native, no seam
    closes, vols = await R._fetch_history(session, isins, start=hist_start, as_of=as_of)
    # Enhanced F+: vol-adjusted 52w momentum metric, precomputed once per snapshot
    # (no-lookahead — uses closes[-2]; identical to run_backtest_f's threading).
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
# Persistence (raw SQL; paper_* tables from migration 0030)
# ---------------------------------------------------------------------------
_SQL_ACCOUNT = text(
    "SELECT id, inception_date, current_cash, current_equity FROM paper_account LIMIT 1"
)
_SQL_OPEN = text(
    "SELECT id, isin, entry_date, entry_price, shares, exposure_at_entry "
    "FROM paper_position WHERE status='open'"
)
_SQL_INS_ACCOUNT = text(
    "INSERT INTO paper_account (inception_date, starting_capital, current_cash, "
    "current_equity, score_source) VALUES (:d, :cap, :cash, :eq, :src) RETURNING id"
)
_SQL_INS_POS = text(
    "INSERT INTO paper_position (isin, entry_date, entry_price, shares, "
    "exposure_at_entry) VALUES (:isin, :d, :px, :sh, :exp)"
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
    "INSERT INTO paper_equity_curve (trade_date, total_equity, invested_value, "
    "cash_value, exposure_level, nifty500_tri, drawdown_pct) "
    "VALUES (:d, :eq, :inv, :cash, :exp, :tri, :dd) "
    "ON CONFLICT (trade_date) DO UPDATE SET total_equity=:eq, invested_value=:inv, "
    "cash_value=:cash, exposure_level=:exp, nifty500_tri=:tri, drawdown_pct=:dd"
)
_SQL_EVENT = text(
    "INSERT INTO paper_event_log (trade_date, event_type, detail) VALUES (:d, :t, :detail)"
)
_SQL_PEAK = text("SELECT MAX(total_equity) FROM paper_equity_curve")
_SQL_TRI_ASOF = text(
    "SELECT index_value FROM benchmark_index WHERE index_name='nifty500_tri' "
    "AND trade_date <= :d ORDER BY trade_date DESC LIMIT 1"
)
_SQL_PRICES = text(
    "SELECT isin, adj_close FROM prices_eod_adjusted WHERE trade_date=:d "
    "AND adj_close IS NOT NULL AND isin = ANY(:isins)"
).bindparams(bindparam("isins"))


async def _log_event(session: AsyncSession, d: date, t: str, detail: str) -> None:
    await session.execute(_SQL_EVENT, {"d": d, "t": t, "detail": detail})


async def get_account(session: AsyncSession) -> dict | None:
    row = (await session.execute(_SQL_ACCOUNT)).first()
    if row is None:
        return None
    return {"id": row[0], "inception_date": row[1], "cash": Decimal(row[2]),
            "equity": Decimal(row[3])}


async def _open_positions(session: AsyncSession) -> list[dict]:
    return [{"id": r[0], "isin": r[1], "entry_date": r[2], "entry_price": Decimal(r[3]),
             "shares": Decimal(r[4]), "exposure": Decimal(r[5])}
            for r in (await session.execute(_SQL_OPEN)).all()]


async def _prices_on(session: AsyncSession, isins: list[str], d: date) -> dict[str, Decimal]:
    if not isins:
        return {}
    rows = (await session.execute(_SQL_PRICES, {"d": d, "isins": isins})).all()
    return {i: Decimal(c) for i, c in rows}


async def _write_curve(
    session: AsyncSession, d: date, invested: Decimal, cash: Decimal, exposure: Decimal
) -> None:
    total = invested + cash
    peak = (await session.execute(_SQL_PEAK)).scalar()
    peak = max(Decimal(peak), total) if peak is not None else total
    dd = ((peak - total) / peak * 100).quantize(_Q2) if peak > 0 else Decimal("0")
    tri = (await session.execute(_SQL_TRI_ASOF, {"d": d})).scalar()
    await session.execute(_SQL_INS_CURVE, {
        "d": d, "eq": total.quantize(_Q2), "inv": invested.quantize(_Q2),
        "cash": cash.quantize(_Q2), "exp": exposure,
        "tri": Decimal(tri).quantize(_Q4) if tri is not None else None, "dd": dd})


async def inception(
    session: AsyncSession, as_of: date, *, dry_run: bool = False
) -> dict:
    """Day-zero: build the F+ book at `as_of` EOD prices with Rs 10L. dry_run returns
    the book WITHOUT persisting (preview). Refuses to re-incept (idempotent)."""
    if await get_account(session) is not None and not dry_run:
        raise RuntimeError("paper_account already exists — inception is once-only")
    snap = await compute_fplus_snapshot(session, as_of, current_isins=set())
    book, cash = size_book(STARTING_CAPITAL, snap.exposure, snap.prices)
    rows = [{"isin": isin, "px": snap.prices[isin], "shares": shares, "value": value,
             "sector": snap.sector_by.get(isin, "?")}
            for isin, (shares, value) in book.items()]
    result = {"as_of": as_of, "exposure": snap.exposure, "cash": cash,
              "invested": STARTING_CAPITAL - cash, "n": len(rows), "rows": rows,
              "scoreable": len(snap.scores)}
    if dry_run:
        return result
    acct_id = (await session.execute(_SQL_INS_ACCOUNT, {
        "d": as_of, "cap": STARTING_CAPITAL, "cash": cash.quantize(_Q2),
        "eq": STARTING_CAPITAL.quantize(_Q2), "src": "mechanical"})).scalar_one()
    for isin, (shares, _value) in book.items():
        await session.execute(_SQL_INS_POS, {
            "isin": isin, "d": as_of, "px": snap.prices[isin].quantize(_Q4),
            "sh": shares, "exp": snap.exposure})
    invested = STARTING_CAPITAL - cash
    await _write_curve(session, as_of, invested, cash, snap.exposure)
    await _log_event(session, as_of, "inception",
                     f"Enhanced F+ inception: {len(rows)} names, exposure {snap.exposure}, "
                     f"cash {cash:.0f}, Rs {STARTING_CAPITAL:.0f} "
                     f"(vol-adj momentum + 6.5% cash yield, commit 6ced078)")
    log.info("paper.inception", as_of=str(as_of), names=len(rows), exposure=str(snap.exposure))
    await session.commit()
    return result | {"account_id": acct_id}


async def daily_mark(session: AsyncSession, as_of: date) -> dict:
    """EOD: mark open positions to `as_of` close, apply cut-on-breakdown (-15% from
    entry), update the equity curve + drawdown. No lookahead (prices = as_of close)."""
    acct = await get_account(session)
    if acct is None:
        raise RuntimeError("no paper_account — run inception first")
    positions = await _open_positions(session)
    prices = await _prices_on(session, [p["isin"] for p in positions], as_of)
    cash = acct["cash"]
    # Enhanced F+: credit idle cash one trading day of interest (6.5%/yr) before
    # marking. Accrued here only (the once-per-day entry point) so weekly/quarterly
    # steps that read the account see the post-accrual balance — no double count.
    if CASH_YIELD_ANNUAL:
        cash = (cash * (Decimal("1") + CASH_YIELD_ANNUAL / Decimal("252"))).quantize(
            _Q2, rounding=ROUND_HALF_EVEN
        )
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
            await _log_event(session, as_of, "breakdown",
                             f"{p['isin']} cut at {px:.2f} (entry {p['entry_price']:.2f})")
            cuts += 1
    open_now = await _open_positions(session)
    prices2 = await _prices_on(session, [p["isin"] for p in open_now], as_of)
    invested = sum((p["shares"] * prices2.get(p["isin"], p["entry_price"]) for p in open_now),
                   Decimal("0"))
    exposure = open_now[0]["exposure"] if open_now else Decimal("0")
    await _write_curve(session, as_of, invested, cash, exposure)
    await session.execute(_SQL_UPD_ACCOUNT, {
        "cash": cash.quantize(_Q2), "eq": (invested + cash).quantize(_Q2), "id": acct["id"]})
    await session.commit()
    return {"date": as_of, "breakdown_cuts": cuts, "equity": invested + cash, "cash": cash}


async def weekly_exposure(session: AsyncSession, as_of: date) -> dict:
    """Weekly: re-check regime; scale the invested sleeve to the new target exposure,
    moving the diff to/from cash (cost on the resized portion)."""
    acct = await get_account(session)
    positions = await _open_positions(session)
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
        await _log_event(session, as_of, "exposure_change",
                         f"exposure {cur_exp} -> {new_exp} (factor {factor:.3f}, "
                         f"traded {traded:.0f})")
        await session.execute(_SQL_UPD_ACCOUNT, {
            "cash": cash.quantize(_Q2), "eq": (invested * factor + cash).quantize(_Q2),
            "id": acct["id"]})
        await session.commit()
    return {"date": as_of, "exposure": new_exp, "changed": new_exp != cur_exp}


async def quarterly_rebalance(session: AsyncSession, as_of: date) -> dict:
    """Quarterly: full F+ re-pick of the 25 names (hold-winners buffer), redeploy cash
    at the current exposure. Sells names that dropped out; buys new ones."""
    acct = await get_account(session)
    positions = await _open_positions(session)
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
                "isin": isin, "d": as_of, "px": px.quantize(_Q4), "sh": per / px,
                "exp": snap.exposure})
    cash = total - per * Decimal(len(tradeable))
    await session.execute(_SQL_UPD_ACCOUNT, {
        "cash": cash.quantize(_Q2), "eq": total.quantize(_Q2), "id": acct["id"]})
    await _log_event(session, as_of, "rebalance",
                     f"quarterly F+ rebalance: {len(tradeable)} names, exposure {snap.exposure}")
    await session.commit()
    return {"date": as_of, "names": len(tradeable), "exposure": snap.exposure}
