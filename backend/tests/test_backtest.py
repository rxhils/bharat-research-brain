"""Pure tests for the walk-forward backtest (Chunk 5.2). No DB.

Cost-model tests pin the round-trip cost band, the profit reduction, and the
small-move-eaten-by-costs case the spec calls out. Engine tests cover top-N
selection (with min_score), per-trade return math, equal-weight allocation, and
the lookahead guard (`exit_date > entry_date`). Metrics tests cover the three
MVP-kept aggregations: max drawdown, win rate, and CAGR.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.backtest import scores as _scores
from backend.backtest.cost_model import (
    apply_costs,
    cost_on_notional,
    round_trip_cost_pct,
)
from backend.backtest.engine import (
    BacktestConfig,
    Trade,
    apply_trailing_stop,
    avg_loss_pct,
    avg_win_pct,
    beta,
    breaks_down,
    cagr_pct,
    classify_defensive_pool,
    compute_trade_return,
    detect_regime,
    low_vol_cutoff,
    low_vol_pass,
    max_drawdown_pct,
    period_returns,
    position_weights,
    profit_factor,
    realized_vol,
    select_top_n,
    sharpe_ratio,
    simulate_day,
    sortino_ratio,
    split_capital,
    target_exposure_for_regime,
    trailing_window,
    win_rate_pct,
)
from backend.backtest.runner import _weighted_ratio
from backend.backtest.scores import (
    compute_full_composite,
    reconstruct_fundamental_score,
    reconstruct_macro_score,
    reconstruct_sector_signal,
)


# ---------------------------------------------------------------------------
# Cost model
# ---------------------------------------------------------------------------
def test_round_trip_cost_in_range() -> None:
    pct = round_trip_cost_pct()
    assert Decimal("0.003") <= pct <= Decimal("0.005"), pct


def test_apply_costs_profit_reduces_gross() -> None:
    # 100 -> 110 on 100 qty: gross 1000; costs > 0, so net < gross but > 0.
    net = apply_costs(Decimal("100"), Decimal("110"), 100)
    assert net > 0
    assert net < Decimal("1000")


def test_apply_costs_small_move_eaten_by_costs() -> None:
    # 100 -> 100.30 on 1 qty: gross 0.30, round-trip cost ~0.40% of 200 ≈ 0.80,
    # so net is NEGATIVE.
    net = apply_costs(Decimal("100"), Decimal("100.30"), 1)
    assert net < 0


# ---------------------------------------------------------------------------
# select_top_n + min_score
# ---------------------------------------------------------------------------
def test_select_top_n_picks_highest() -> None:
    scores = {
        "A": Decimal("50"),
        "B": Decimal("80"),
        "C": Decimal("65"),
        "D": Decimal("75"),
    }
    assert select_top_n(scores, 3) == ["B", "D", "C"]


def test_select_top_n_respects_min_score() -> None:
    scores = {"A": Decimal("30"), "B": Decimal("60"), "C": Decimal("90")}
    assert select_top_n(scores, 5, min_score=Decimal("50")) == ["C", "B"]


# ---------------------------------------------------------------------------
# Trade-level math
# ---------------------------------------------------------------------------
def test_compute_trade_return_positive() -> None:
    assert compute_trade_return(Decimal("100"), Decimal("110")) == Decimal("10.0000")


def test_compute_trade_return_negative() -> None:
    assert compute_trade_return(Decimal("100"), Decimal("90")) == Decimal("-10.0000")


# ---------------------------------------------------------------------------
# simulate_day
# ---------------------------------------------------------------------------
def _entry_exit(
    syms: list[str], entry: float, exit_p: float
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    return (
        {s: Decimal(str(entry)) for s in syms},
        {s: Decimal(str(exit_p)) for s in syms},
    )


def test_simulate_day_applies_costs_net_lt_gross() -> None:
    syms = ["A", "B"]
    scores = {"A": Decimal("80"), "B": Decimal("75")}
    e, x = _entry_exit(syms, 100.0, 110.0)
    r = simulate_day(
        date(2024, 1, 1),
        date(2024, 1, 8),
        scores,
        e,
        x,
        n=2,
        capital=Decimal("1000000"),
    )
    assert r.gross_pnl > r.net_pnl
    assert r.costs_paid > 0
    assert len(r.trades) == 2


def test_simulate_day_equal_weight_allocation() -> None:
    # 1,000,000 capital / 2 positions = 500,000 each; @ entry 100 -> 5000 frac shares.
    syms = ["A", "B"]
    scores = {"A": Decimal("80"), "B": Decimal("75")}
    e, x = _entry_exit(syms, 100.0, 110.0)
    r = simulate_day(
        date(2024, 1, 1),
        date(2024, 1, 8),
        scores,
        e,
        x,
        n=2,
        capital=Decimal("1000000"),
    )
    assert {t.qty for t in r.trades} == {Decimal("5000")}


def test_select_top_n_zero_means_all_eligible() -> None:
    # n <= 0 -> threshold portfolio: every stock >= min_score, no cap.
    scores = {"A": Decimal("40"), "B": Decimal("90"), "C": Decimal("65")}
    assert select_top_n(scores, 0, min_score=Decimal("50")) == ["B", "C"]
    assert select_top_n(scores, 0) == ["B", "C", "A"]


def test_cost_on_notional_not_doubled() -> None:
    # BUG 2 lock: cost is the round-trip % of POSITION notional, applied ONCE.
    # round_trip_cost_pct ~0.49%; on 100,000 deployed -> ~490, NOT ~980.
    cost = cost_on_notional(Decimal("100000"))
    assert Decimal("300") <= cost <= Decimal("500"), cost
    # apply_costs on a flat trade loses exactly cost_on_notional(entry*qty).
    flat = apply_costs(Decimal("100"), Decimal("100"), 1000)
    assert flat == -cost_on_notional(Decimal("100000"))


def test_simulate_day_lookahead_guard() -> None:
    # exit_date <= entry_date must raise — defensive guard regardless of caller.
    with pytest.raises(AssertionError):
        simulate_day(
            date(2024, 1, 5),
            date(2024, 1, 5),  # same day -> lookahead violation
            {"A": Decimal("80")},
            {"A": Decimal("100")},
            {"A": Decimal("105")},
            n=1,
            capital=Decimal("100000"),
        )


# ---------------------------------------------------------------------------
# Metrics (the three MVP kept)
# ---------------------------------------------------------------------------
def test_max_drawdown_calculation() -> None:
    # [100,120,90,110] -> peak 120, trough 90 -> dd = 25%
    eq = [Decimal(v) for v in [100, 120, 90, 110]]
    assert max_drawdown_pct(eq) == Decimal("25.00")


def test_win_rate_calculation() -> None:
    # 6 winning trades + 4 losing -> 60%
    def _t(net: Decimal) -> Trade:
        return Trade(
            isin="X",
            entry_date=date(2024, 1, 1),
            exit_date=date(2024, 1, 8),
            entry_price=Decimal("100"),
            exit_price=Decimal("101"),
            qty=1,
            gross_pnl=Decimal("1"),
            net_pnl=net,
            gross_return_pct=Decimal("1"),
            score=Decimal("70"),
        )

    trades = [_t(Decimal("1")) for _ in range(6)] + [
        _t(Decimal("-1")) for _ in range(4)
    ]
    assert win_rate_pct(trades) == Decimal("60.00")


def test_cagr_doubles_in_one_year() -> None:
    # 1.0 -> 2.0 in 1 year -> 100% CAGR
    assert cagr_pct(Decimal("100"), Decimal("200"), Decimal("1")) == Decimal("100.00")


def test_cagr_flat() -> None:
    assert cagr_pct(Decimal("100"), Decimal("100"), Decimal("2")) == Decimal("0.00")


# ---------------------------------------------------------------------------
# Risk/return metrics (Chunk 5.2 enhancement)
# ---------------------------------------------------------------------------
def _trade(net: Decimal, ret_pct: Decimal) -> Trade:
    return Trade(
        isin="X",
        entry_date=date(2024, 1, 1),
        exit_date=date(2024, 1, 8),
        entry_price=Decimal("100"),
        exit_price=Decimal("100"),
        qty=Decimal("1"),
        gross_pnl=net,
        net_pnl=net,
        gross_return_pct=ret_pct,
        score=Decimal("70"),
    )


def test_period_returns() -> None:
    pr = period_returns([Decimal("100"), Decimal("110"), Decimal("99")])
    assert pr[0] == Decimal("0.100000")
    assert pr[1] == Decimal("-0.100000")


def test_beta_identical_series_is_one() -> None:
    m = [Decimal("0.01"), Decimal("-0.02"), Decimal("0.03"), Decimal("-0.01")]
    assert beta(m, m) == Decimal("1.00")


def test_beta_double_series_is_two() -> None:
    m = [Decimal("0.01"), Decimal("-0.02"), Decimal("0.03"), Decimal("-0.01")]
    a = [x * 2 for x in m]
    assert beta(a, m) == Decimal("2.00")


def test_sharpe_constant_returns_is_none() -> None:
    # zero variance -> undefined Sharpe -> None
    assert sharpe_ratio([Decimal("0.02")] * 4, Decimal("0.07"), Decimal("4")) is None


def test_sharpe_positive_when_excess_positive() -> None:
    r = [Decimal("0.05"), Decimal("0.03"), Decimal("0.04"), Decimal("0.06")]
    s = sharpe_ratio(r, Decimal("0.07"), Decimal("4"))
    assert s is not None and s > 0


def test_sortino_no_downside_is_none() -> None:
    # all returns above the per-period risk-free target -> no downside -> None
    assert sortino_ratio([Decimal("0.05"), Decimal("0.06")], Decimal("0.07"), Decimal("4")) is None


def test_sortino_finite_with_downside() -> None:
    r = [Decimal("0.05"), Decimal("-0.02"), Decimal("0.04"), Decimal("0.03")]
    s = sortino_ratio(r, Decimal("0.07"), Decimal("4"))
    assert s is not None


def test_profit_factor() -> None:
    trades = [_trade(Decimal("10"), Decimal("10")) for _ in range(3)] + [
        _trade(Decimal("-5"), Decimal("-5")) for _ in range(2)
    ]
    # gross win 30 / gross loss 10 = 3.0
    assert profit_factor(trades) == Decimal("3.00")


def test_profit_factor_no_losses_is_none() -> None:
    assert profit_factor([_trade(Decimal("10"), Decimal("10"))]) is None


def test_avg_win_and_loss_pct() -> None:
    trades = [
        _trade(Decimal("1"), Decimal("10")),
        _trade(Decimal("1"), Decimal("5")),
        _trade(Decimal("1"), Decimal("6")),
        _trade(Decimal("-1"), Decimal("-3")),
        _trade(Decimal("-1"), Decimal("-4")),
    ]
    assert avg_win_pct(trades) == Decimal("7.00")
    assert avg_loss_pct(trades) == Decimal("-3.50")


# ---------------------------------------------------------------------------
# Week 2 — full-composite reconstruction (Chunk 5.2b). Pure: a fake async
# session returns canned rows shaped like the historical tables; the four
# component functions are monkeypatched for the orchestrator tests. No DB.
# The no-lookahead asserts live inside the functions; here we only check the
# scoring/mapping/fallback logic.
# ---------------------------------------------------------------------------
class _FakeResult:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def first(self) -> tuple | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[tuple]:
        return self._rows


class _FakeSession:
    """Async session stub. `single` answers isin/sector queries; `by_indicator`
    answers the per-indicator macro queries (dispatched on params['indicator'])."""

    def __init__(
        self,
        *,
        single: list[tuple] | None = None,
        by_indicator: dict[str, list[tuple]] | None = None,
    ) -> None:
        self._single = single or []
        self._by_indicator = by_indicator or {}

    async def execute(self, _query: object, params: dict | None = None) -> _FakeResult:
        ind = (params or {}).get("indicator")
        if ind is not None:
            return _FakeResult(self._by_indicator.get(ind, []))
        return _FakeResult(self._single)


_ASOF = date(2025, 6, 1)
_PRIOR = date(2025, 1, 1)  # a publication/computed date safely <= _ASOF


async def test_reconstruct_fundamental_score_with_data() -> None:
    # Stored units: roe/rev are FRACTIONS, debt_to_equity a RATIO, pe absolute.
    # PE 15, ROE 22%, D/E 0.5, rev 15%, FCF positive, sector IT -> very strong;
    # the reused live score_fundamental saturates to 100 on inputs this good.
    row = (_PRIOR, Decimal("15"), Decimal("0.22"), Decimal("0.5"),
           Decimal("1000"), Decimal("0.15"), "IT")
    sess = _FakeSession(single=[row])
    score = await reconstruct_fundamental_score(sess, "INE0", _ASOF)
    assert score is not None and score >= Decimal("70")


async def test_reconstruct_fundamental_score_no_data() -> None:
    sess = _FakeSession(single=[])
    assert await reconstruct_fundamental_score(sess, "INE0", _ASOF) is None


async def test_reconstruct_macro_score_strong_breadth() -> None:
    sess = _FakeSession(by_indicator={
        "advance_decline_ratio": [(_PRIOR, Decimal("2.5"))],
        "pct_above_ema200": [(_PRIOR, Decimal("70"))],
        "new_high_low_ratio": [(_PRIOR, Decimal("5"))],
    })
    score = await reconstruct_macro_score(sess, _ASOF)
    assert score > Decimal("60")


async def test_reconstruct_macro_score_weak_breadth() -> None:
    sess = _FakeSession(by_indicator={
        "advance_decline_ratio": [(_PRIOR, Decimal("0.5"))],
        "pct_above_ema200": [(_PRIOR, Decimal("30"))],
        "new_high_low_ratio": [(_PRIOR, Decimal("0.3"))],
    })
    score = await reconstruct_macro_score(sess, _ASOF)
    assert score < Decimal("40")


async def test_reconstruct_sector_signal_leading() -> None:
    sess = _FakeSession(single=[(_PRIOR, "leading")])
    assert await reconstruct_sector_signal(sess, "INE0", _ASOF) == "leading"


async def test_reconstruct_sector_signal_no_data() -> None:
    sess = _FakeSession(single=[])
    assert await reconstruct_sector_signal(sess, "INE0", _ASOF) == "neutral"


def _patch_components(
    monkeypatch: pytest.MonkeyPatch,
    *,
    t: Decimal,
    f: Decimal | None,
    m: Decimal,
    sector: str,
) -> None:
    monkeypatch.setattr(_scores, "compute_score_from_history", lambda _c, _v=None: t)

    async def _f(*_a: object, **_k: object) -> Decimal | None:
        return f

    async def _m(*_a: object, **_k: object) -> Decimal:
        return m

    async def _s(*_a: object, **_k: object) -> str:
        return sector

    monkeypatch.setattr(_scores, "reconstruct_fundamental_score", _f)
    monkeypatch.setattr(_scores, "reconstruct_macro_score", _m)
    monkeypatch.setattr(_scores, "reconstruct_sector_signal", _s)


async def test_compute_full_composite_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_components(monkeypatch, t=Decimal("70"), f=Decimal("80"), m=Decimal("60"),
                      sector="leading")
    out = await compute_full_composite(None, "X", _ASOF, [1.0] * 40, [1] * 40)
    # 70*0.35 + 80*0.40 + 60*0.25 + 5 (leading) = 76.5
    assert out == Decimal("76.50")


async def test_compute_full_composite_fundamentals_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_components(monkeypatch, t=Decimal("70"), f=None, m=Decimal("60"),
                      sector="neutral")
    out = await compute_full_composite(None, "X", _ASOF, [1.0] * 40, [1] * 40)
    # F None -> re-normalize T+M (no 20-pt neutral-F ceiling):
    # 70*0.583 + 60*0.417 = 65.83
    assert out == Decimal("65.83")


async def test_compute_full_composite_lagging_sector_clamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_components(monkeypatch, t=Decimal("10"), f=Decimal("10"), m=Decimal("10"),
                      sector="lagging")
    out = await compute_full_composite(None, "X", _ASOF, [1.0] * 40, [1] * 40)
    # 10*0.35 + 10*0.40 + 10*0.25 - 5 (lagging) = 5
    assert out == Decimal("5.00")


async def test_compute_full_composite_max_clamp(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_components(monkeypatch, t=Decimal("100"), f=Decimal("100"), m=Decimal("100"),
                      sector="leading")
    out = await compute_full_composite(None, "X", _ASOF, [1.0] * 40, [1] * 40)
    # 100 + 5 = 105 -> clamped to 100
    assert out == Decimal("100.00")


# ---------------------------------------------------------------------------
# Chunk 5.2c — benchmark weighting math (_weighted_ratio). Pure: dicts in,
# Decimal basket-ratio out. mcap weighting must give larger stocks more pull.
# ---------------------------------------------------------------------------
def test_weighted_ratio_equal_is_simple_mean() -> None:
    base = {"A": Decimal("100"), "B": Decimal("100")}
    prices = {"A": Decimal("110"), "B": Decimal("100")}
    # weights None -> equal weight -> (1.1 + 1.0) / 2 = 1.05
    r = _weighted_ratio(base, prices, None)
    assert r is not None and abs(r - Decimal("1.05")) < Decimal("0.0001")


def test_weighted_ratio_mcap_favours_larger() -> None:
    # A is 10x B by mcap. A +10%, B flat. A drives 10/11 (~91%) of the basket:
    # ratio = (10/11)*1.1 + (1/11)*1.0 = 1.0909...
    base = {"A": Decimal("100"), "B": Decimal("100")}
    prices = {"A": Decimal("110"), "B": Decimal("100")}
    weights = {"A": Decimal("10"), "B": Decimal("1")}
    r = _weighted_ratio(base, prices, weights)
    assert r is not None
    assert abs(r - Decimal("1.090909")) < Decimal("0.0005")
    # far closer to A's 1.1 than the equal-weight 1.05
    assert r > Decimal("1.08")


def test_weighted_ratio_none_when_no_overlap() -> None:
    base = {"A": Decimal("100")}
    prices = {"B": Decimal("100")}  # nothing in both base and prices
    assert _weighted_ratio(base, prices, None) is None


# ---------------------------------------------------------------------------
# Composite re-normalization when fundamentals are absent (removes the
# structural 20-point neutral-F ceiling that blocked all pre-2024 trades).
# ---------------------------------------------------------------------------
async def test_composite_with_fundamentals(monkeypatch: pytest.MonkeyPatch) -> None:
    # F present -> full composite unchanged: 70*0.35 + 80*0.40 + 60*0.25 = 71.5
    _patch_components(monkeypatch, t=Decimal("70"), f=Decimal("80"), m=Decimal("60"),
                      sector="neutral")
    out = await compute_full_composite(None, "X", _ASOF, [1.0] * 40, [1] * 40)
    assert out == Decimal("71.50")


async def test_composite_without_fundamentals_renormalized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # F None -> T+M re-normalized to sum 1.0: 80*0.583 + 70*0.417 = 75.83,
    # which CLEARS the 75 floor (impossible under the old neutral-50 ceiling).
    _patch_components(monkeypatch, t=Decimal("80"), f=None, m=Decimal("70"),
                      sector="neutral")
    out = await compute_full_composite(None, "X", _ASOF, [1.0] * 40, [1] * 40)
    assert out == Decimal("75.83")


def test_composite_renorm_weights_sum_to_one() -> None:
    # 0.583 + 0.417 = 1.000 (T and M absorb the fundamentals weight exactly).
    assert Decimal("1.000") == _scores._W_TECH_ABSENT + _scores._W_MACRO_ABSENT


# ---------------------------------------------------------------------------
# Config D consistency techniques (Chunk 5.2c): sector cap, score-weighted
# sizing, trailing stop. Backward-compat defaults must leave A/B/C unchanged.
# ---------------------------------------------------------------------------
def test_max_per_sector_caps_holdings() -> None:
    scores = {f"CG{i}": Decimal(90 - i) for i in range(6)}  # 6 Capital Goods
    scores.update({f"X{i}": Decimal(80 - i) for i in range(6)})  # 6 other sectors
    sector_by = {f"CG{i}": "Capital Goods" for i in range(6)}
    sector_by.update({f"X{i}": f"S{i}" for i in range(6)})
    picks = select_top_n(
        scores, 8, Decimal("0"), sector_by=sector_by, max_per_sector=3
    )
    cg = [p for p in picks if sector_by[p] == "Capital Goods"]
    assert len(cg) == 3  # capped at 3 despite 6 top scorers being Cap Goods
    assert len(picks) == 8  # remaining slots filled from other sectors


def test_score_weighted_sizing() -> None:
    picks = [f"S{i}" for i in range(20)]
    scores = {f"S{i}": Decimal(100 - i) for i in range(20)}  # 100..81
    w = position_weights(picks, scores, "score_weighted", Decimal("0.10"))
    assert abs(sum(w.values(), Decimal(0)) - Decimal("1")) < Decimal("0.0001")
    assert max(w.values()) <= Decimal("0.10") + Decimal("0.0001")  # 10% clamp
    assert w["S0"] > w["S19"]  # higher score -> more capital


def test_trailing_stop_triggers() -> None:
    # entry 100, peak 120, then 100 = -16.7% from peak -> stop fires at 100.
    path = [(date(2024, 1, 2), Decimal("120")), (date(2024, 1, 3), Decimal("100"))]
    ed, ep, stopped = apply_trailing_stop(Decimal("100"), path, Decimal("15"))
    assert stopped is True
    assert ep == Decimal("100") and ed == date(2024, 1, 3)


def test_trailing_stop_not_triggered() -> None:
    # peak 120, dip to 110.4 = -8% from peak -> held; exit at the last close.
    path = [(date(2024, 1, 2), Decimal("120")), (date(2024, 1, 3), Decimal("110.4"))]
    ed, ep, stopped = apply_trailing_stop(Decimal("100"), path, Decimal("15"))
    assert stopped is False
    assert ep == Decimal("110.4") and ed == date(2024, 1, 3)


def test_config_abc_unchanged() -> None:
    c = BacktestConfig(start_date=date(2024, 1, 1), end_date=date(2024, 2, 1))
    assert c.max_per_sector is None
    assert c.position_sizing == "equal"
    assert c.trailing_stop_pct is None
    # select_top_n with no sector args is the original behavior.
    s = {"A": Decimal("90"), "B": Decimal("80"), "C": Decimal("70")}
    assert select_top_n(s, 2) == ["A", "B"]
    # equal sizing is the default weighting (1/n each).
    w = position_weights(["A", "B", "C", "D"], s, "equal", Decimal("0.10"))
    assert all(v == Decimal("1") / Decimal("4") for v in w.values())


# ---------------------------------------------------------------------------
# Config E — regime switching (beta classification + regime detection)
# ---------------------------------------------------------------------------
def test_beta_aggressive_stock() -> None:
    # stock moves 1.5x the index each period -> beta ~ 1.5.
    idx = [Decimal(str(x)) for x in (0.01, -0.02, 0.03, -0.01, 0.02, -0.015)]
    stk = [r * Decimal("1.5") for r in idx]
    b = beta(stk, idx)
    assert b is not None
    assert Decimal("1.45") <= b <= Decimal("1.55"), b


def test_beta_defensive_stock() -> None:
    # stock moves 0.5x the index each period -> beta ~ 0.5 (low-beta defensive).
    idx = [Decimal(str(x)) for x in (0.01, -0.02, 0.03, -0.01, 0.02, -0.015)]
    stk = [r * Decimal("0.5") for r in idx]
    b = beta(stk, idx)
    assert b is not None
    assert Decimal("0.45") <= b <= Decimal("0.55"), b


def test_beta_insufficient_returns() -> None:
    assert beta([Decimal("0.01")], [Decimal("0.01")]) is None  # <2 points


def test_detect_regime_risk_on_uptrend() -> None:
    # rising series: last close above its 200-DMA AND 50-day return >= 0.
    closes = [Decimal(str(100 + i)) for i in range(260)]  # strictly increasing
    assert detect_regime(closes) == "risk_on"


def test_detect_regime_risk_off_downtrend() -> None:
    # falling series: last close below its 200-DMA -> risk_off.
    closes = [Decimal(str(400 - i)) for i in range(260)]  # strictly decreasing
    assert detect_regime(closes) == "risk_off"


def test_detect_regime_risk_off_negative_momentum() -> None:
    # above the 200-DMA but the recent 50-day leg is negative -> risk_off.
    closes = [Decimal(str(100 + i)) for i in range(210)]  # uptrend 100..309
    closes += [Decimal(str(309 - i)) for i in range(1, 51)]  # gentle 50-day pullback
    # last close (259) is still ABOVE the 200-DMA (~247) but 50-day return < 0.
    assert detect_regime(closes) == "risk_off"


def test_detect_regime_warmup_defaults_risk_on() -> None:
    # fewer than 200 closes -> not enough history -> default to full participation.
    assert detect_regime([Decimal("100")] * 50) == "risk_on"


def test_classify_defensive_pool_lowest_beta() -> None:
    betas = {
        "LOW1": Decimal("0.4"), "LOW2": Decimal("0.6"),
        "MID": Decimal("1.0"), "HIGH1": Decimal("1.4"), "HIGH2": Decimal("1.8"),
    }
    pool = classify_defensive_pool(betas, Decimal("0.40"))  # lowest 40% = 2 of 5
    assert pool == {"LOW1", "LOW2"}


def test_classify_defensive_pool_empty() -> None:
    assert classify_defensive_pool({}, Decimal("0.40")) == set()


def test_trailing_window_excludes_future() -> None:
    # the no-lookahead guard: bars dated after as_of must never appear.
    series = [
        (date(2020, 1, 1), Decimal("10")),
        (date(2020, 1, 2), Decimal("11")),
        (date(2020, 1, 3), Decimal("12")),  # as_of
        (date(2020, 1, 6), Decimal("99")),  # FUTURE — must be excluded
    ]
    win = trailing_window(series, date(2020, 1, 3), 2)
    assert win == [(date(2020, 1, 2), Decimal("11")), (date(2020, 1, 3), Decimal("12"))]
    assert all(d <= date(2020, 1, 3) for d, _ in win)


def test_config_e_defaults_reproduce_c() -> None:
    # regime switching is OFF by default -> A/B/C/D configs are untouched.
    c = BacktestConfig(start_date=date(2024, 1, 1), end_date=date(2024, 2, 1))
    assert c.regime_switching is False
    assert c.defensive_pool_pct == Decimal("0.40")
    assert c.beta_window == 252


# ---------------------------------------------------------------------------
# Config F — cash-aware accounting (Component 0), regime exposure (5), quality (1)
# ---------------------------------------------------------------------------
def test_split_capital_half() -> None:
    inv, cash = split_capital(Decimal("1000000"), Decimal("0.5"))
    assert inv == Decimal("500000")
    assert cash == Decimal("500000")


def test_split_capital_full_is_all_invested() -> None:
    # exposure 1.0 -> the invested sleeve IS the whole book, cash = 0 (= old engine).
    inv, cash = split_capital(Decimal("1000000"), Decimal("1.0"))
    assert inv == Decimal("1000000")
    assert cash == Decimal("0")


def test_cash_sleeve_does_not_move() -> None:
    # exposure 0.5, market -20% -> total equity -10% (cash half is protected).
    total = Decimal("1000000")
    inv, cash = split_capital(total, Decimal("0.5"))
    after = cash + inv * Decimal("0.80")  # invested sleeve falls 20%, cash flat
    assert after == Decimal("900000")  # -10%, not -20%


def test_drawdown_on_blended_curve_quarter_exposure() -> None:
    # 0.25-exposure book through a -50% crash shows ~1/4 the market drawdown.
    total = Decimal("1000000")
    inv, cash = split_capital(total, Decimal("0.25"))
    trough = cash + inv * Decimal("0.50")  # market halves
    dd = max_drawdown_pct([total, trough])
    assert Decimal("12") <= dd <= Decimal("13"), dd  # ~12.5% = 0.25 * 50%


def test_cash_moves_cost_applied() -> None:
    # going 100% -> 50% liquidates half the book; sell-side cost must be > 0.
    cost = cost_on_notional(Decimal("500000"))
    assert cost > 0


def test_target_exposure_full_when_healthy() -> None:
    closes = [Decimal(str(100 + i)) for i in range(260)]  # uptrend above 200-DMA
    assert target_exposure_for_regime(closes) == Decimal("1.00")


def test_target_exposure_half_when_below_dma() -> None:
    # below the 200-DMA but a shallow 50-day pullback -> 0.50.
    closes = [Decimal(str(300 - i)) for i in range(210)]  # 300..91 downtrend
    closes += [Decimal(str(91 + (i % 2))) for i in range(1, 51)]  # flat-ish tail
    assert target_exposure_for_regime(closes) == Decimal("0.50")


def test_target_exposure_quarter_when_deep_crash() -> None:
    # below the 200-DMA AND a steep 50-day fall (< -8%) -> 0.25.
    closes = [Decimal(str(300 - i)) for i in range(210)]  # long downtrend
    closes += [Decimal(str(90 - 1 * i)) for i in range(1, 51)]  # steep -50d leg
    assert target_exposure_for_regime(closes) == Decimal("0.25")


def test_target_exposure_warmup_defaults_full() -> None:
    assert target_exposure_for_regime([Decimal("100")] * 50) == Decimal("1.00")


def test_realized_vol_positive() -> None:
    v = realized_vol([0.01, -0.02, 0.03, -0.01, 0.02])
    assert v is not None and v > 0


def test_low_vol_pass_excludes_top_tertile() -> None:
    # 6 names; top-tertile (2 highest-vol) excluded -> 4 pass; the calm ones kept.
    vols = {"A": 0.1, "B": 0.12, "C": 0.15, "D": 0.2, "E": 0.5, "F": 0.6}
    keep = low_vol_pass(vols)
    assert "E" not in keep and "F" not in keep  # highest-vol tertile excluded
    assert "A" in keep and "B" in keep


def test_config_f_defaults_reproduce_abcde() -> None:
    # all F fields default OFF/neutral -> A/B/C/D/E configs are untouched.
    c = BacktestConfig(start_date=date(2024, 1, 1), end_date=date(2024, 2, 1))
    assert c.quality_gate is False
    assert c.graded_exposure is False
    assert c.hold_buffer_rank == 40
    assert c.turnover_mode == "standard"


# ---------------------------------------------------------------------------
# Config F+ — decoupled weekly exposure (Change 1) + cut-on-breakdown (Change 2)
# ---------------------------------------------------------------------------
def test_breaks_down_price_stop_triggers() -> None:
    # down 16% from entry (close 84 vs entry 100, 15% stop) -> cut that day.
    assert breaks_down(Decimal("84"), Decimal("100"), Decimal("0.15"), False) is True


def test_breaks_down_price_stop_held() -> None:
    # down 8% -> still held.
    assert breaks_down(Decimal("92"), Decimal("100"), Decimal("0.15"), False) is False


def test_breaks_down_quality_fail_forces_exit() -> None:
    # fails the quality gate -> cut regardless of price (even up 5%).
    assert breaks_down(Decimal("105"), Decimal("100"), Decimal("0.15"), True) is True


def test_breaks_down_no_lookahead_uses_only_close_and_entry() -> None:
    # exactly at the threshold (-15%) triggers; just above does not — pure on (close, entry).
    assert breaks_down(Decimal("85"), Decimal("100"), Decimal("0.15"), False) is True
    assert breaks_down(Decimal("85.01"), Decimal("100"), Decimal("0.15"), False) is False


def test_low_vol_cutoff_boundary() -> None:
    # 6 names, drop top tertile (2) -> keep 4 -> boundary = 4th-smallest vol (0.2).
    vols = {"A": 0.1, "B": 0.12, "C": 0.15, "D": 0.2, "E": 0.5, "F": 0.6}
    cut = low_vol_cutoff(vols)
    assert cut is not None and abs(cut - 0.2) < 1e-9, cut


def test_config_fplus_defaults_reproduce_f() -> None:
    # both F+ flags default OFF -> A/B/C/D/E/F are untouched.
    c = BacktestConfig(start_date=date(2024, 1, 1), end_date=date(2024, 2, 1))
    assert c.exposure_check_days is None
    assert c.breakdown_exit_pct is None
    assert c.history_floor is None
