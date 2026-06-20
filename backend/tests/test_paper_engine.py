"""Pure tests for the forward paper-trading engine (no DB).

Covers the cash-accounting decision math that the live engine applies on top of the
FROZEN F+ rules: book sizing at a given exposure, exposure rescaling to/from cash,
the cut-on-breakdown predicate (reused from F+), and a regression that the paper
config IS the frozen F+ parameter set (so F+ is untouched).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.backtest.engine import breaks_down
from backend.paper.engine import (
    BREAKDOWN_PCT,
    fplus_cfg,
    scale_to_exposure,
    size_book,
)


def _prices(n: int, px: str = "100") -> dict[str, Decimal]:
    return {f"INE{i:09d}": Decimal(px) for i in range(n)}


# --- Component 0: book sizing at the regime exposure ------------------------
def test_size_book_full_exposure_25_names() -> None:
    # Rs 10L at exposure 1.0 across 25 names @ 100 -> Rs 40,000 each, ~0 cash.
    book, cash = size_book(Decimal("1000000"), Decimal("1.0"), _prices(25))
    assert len(book) == 25
    shares, value = book["INE000000000"]
    assert value == Decimal("40000.00")
    assert shares == Decimal("400")
    assert cash == Decimal("0.00")


def test_size_book_half_exposure_holds_cash() -> None:
    # exposure 0.5 -> only Rs 5L invested (Rs 20k x 25), Rs 5L stays in cash.
    book, cash = size_book(Decimal("1000000"), Decimal("0.5"), _prices(25))
    _shares, value = book["INE000000000"]
    assert value == Decimal("20000.00")
    assert cash == Decimal("500000.00")


def test_size_book_no_priced_names_all_cash() -> None:
    book, cash = size_book(Decimal("1000000"), Decimal("1.0"), {})
    assert book == {}
    assert cash == Decimal("1000000")


# --- Component 0: weekly exposure rescaling ---------------------------------
def test_scale_to_exposure_halves_book_to_cash() -> None:
    # fully invested -> 0.5: half the book sold to cash.
    factor, traded, new_cash = scale_to_exposure(
        Decimal("1000000"), Decimal("0"), Decimal("0.5")
    )
    assert factor == Decimal("0.5")
    assert traded == Decimal("500000.0000")
    assert new_cash == Decimal("500000.0000")


def test_scale_to_exposure_redeploys_cash_on_recovery() -> None:
    # 0.5 invested + 0.5 cash -> 1.0: cash redeployed, book doubles.
    factor, _traded, new_cash = scale_to_exposure(
        Decimal("500000"), Decimal("500000"), Decimal("1.0")
    )
    assert factor == Decimal("2")
    assert new_cash == Decimal("0.0000")


def test_scale_to_exposure_no_invested_is_noop() -> None:
    factor, traded, new_cash = scale_to_exposure(
        Decimal("0"), Decimal("1000000"), Decimal("0.5")
    )
    assert factor == Decimal("1")
    assert traded == Decimal("0")
    assert new_cash == Decimal("1000000")


# --- Cut-on-breakdown (reused frozen predicate) -----------------------------
def test_breakdown_closes_position_at_minus16() -> None:
    assert breaks_down(Decimal("84"), Decimal("100"), BREAKDOWN_PCT, False) is True


def test_breakdown_holds_position_at_minus8() -> None:
    assert breaks_down(Decimal("92"), Decimal("100"), BREAKDOWN_PCT, False) is False


# --- Regression: the paper engine runs the ENHANCED F+ parameter set --------
# Same F+ skeleton (so the validated structure is intact) PLUS the two adopted
# gauntlet winners: vol-adjusted momentum + idle-cash yield @ 6.5%/yr.
def test_paper_config_is_enhanced_fplus() -> None:
    c = fplus_cfg(date(2026, 6, 15))
    # F+ skeleton unchanged
    assert c.graded_exposure is True
    assert c.quality_gate is True
    assert c.breakdown_exit_pct == Decimal("0.15")
    assert c.exposure_check_days == 5
    assert c.top_n == 25
    assert c.max_per_sector == 4
    assert c.hold_buffer_rank == 40
    assert c.turnover_mode == "low"
    # Enhanced adoptions
    assert c.momentum_mode == "voladj"
    assert c.cash_yield_annual == Decimal("0.065")
