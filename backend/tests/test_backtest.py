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

from backend.backtest.cost_model import (
    apply_costs,
    cost_on_notional,
    round_trip_cost_pct,
)
from backend.backtest.engine import (
    Trade,
    avg_loss_pct,
    avg_win_pct,
    beta,
    cagr_pct,
    compute_trade_return,
    max_drawdown_pct,
    period_returns,
    profit_factor,
    select_top_n,
    sharpe_ratio,
    simulate_day,
    sortino_ratio,
    win_rate_pct,
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
