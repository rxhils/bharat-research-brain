"""Tests for the Outcome Agent (Phase 5, Chunk 5.1).

Pure functions (return math, signal encoders, accuracy, memory rendering) are
tested with synthetic data — no DB, no network. The two async behaviours that the
spec calls out (no rankings -> 0 picks; missing exit price -> skip, no crash) use
unittest.mock to stand in for the session + repo, so still no real I/O.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from backend.agents.outcome import (
    OutcomeAgent,
    compute_accuracy,
    compute_return,
    encode_fii_signal,
    encode_macro_regime,
    render_memory,
)
from backend.db.repositories.outcome import OutcomeRow


# ---------------------------------------------------------------------------
# compute_return — (return_pct, direction_correct)
# ---------------------------------------------------------------------------
def test_compute_return_positive() -> None:
    ret, correct = compute_return(Decimal("100"), Decimal("105"))
    assert ret == Decimal("5.0000")
    assert correct is True


def test_compute_return_negative() -> None:
    ret, correct = compute_return(Decimal("100"), Decimal("95"))
    assert ret == Decimal("-5.0000")
    assert correct is False


def test_compute_return_zero() -> None:
    # a flat move is NOT directionally correct (return must be strictly > 0)
    ret, correct = compute_return(Decimal("100"), Decimal("100"))
    assert ret == Decimal("0.0000")
    assert correct is False


# ---------------------------------------------------------------------------
# signal encoders
# ---------------------------------------------------------------------------
def test_fii_signal_encoding() -> None:
    assert encode_fii_signal("strong_buy") == 2
    assert encode_fii_signal("buy") == 1
    assert encode_fii_signal("neutral") == 0
    assert encode_fii_signal("sell") == -1
    assert encode_fii_signal("strong_sell") == -2
    assert encode_fii_signal("unknown") == 0
    assert encode_fii_signal(None) == 0


def test_macro_regime_encoding() -> None:
    assert encode_macro_regime("risk-on") == 1
    assert encode_macro_regime("risk-off") == -1
    assert encode_macro_regime("neutral") == 0
    assert encode_macro_regime(None) == 0


# ---------------------------------------------------------------------------
# compute_accuracy
# ---------------------------------------------------------------------------
def _row(
    correct_1d: bool | None,
    correct_5d: bool | None,
    label: str = "bullish-watch",
) -> OutcomeRow:
    return OutcomeRow(
        isin="INE000000000",
        pick_date=date(2026, 5, 20),
        signal_label=label,
        composite_score=Decimal("70"),
        entry_price=Decimal("100"),
        exit_price_1d=Decimal("101") if correct_1d is not None else None,
        exit_price_5d=Decimal("102") if correct_5d is not None else None,
        return_1d_pct=Decimal("1") if correct_1d is not None else None,
        return_5d_pct=Decimal("2") if correct_5d is not None else None,
        direction_correct_1d=correct_1d,
        direction_correct_5d=correct_5d,
        technical_score=None,
        fundamental_score=None,
        macro_score=None,
        macro_regime=None,
        india_vix=None,
        sector=None,
        vcp_detected=None,
        delivery_pct=None,
    )


def test_accuracy_summary_calculation() -> None:
    # 10 rows with a 1d direction; 7 correct_1d, 6 correct_5d (1 has no 5d yet)
    rows = (
        [_row(True, True) for _ in range(6)]
        + [_row(True, None)]  # 7th correct_1d, no 5d verdict
        + [_row(False, False) for _ in range(3)]
    )
    summary = compute_accuracy(rows)
    assert summary.total_picks == 10
    assert summary.correct_1d == 7
    assert summary.correct_5d == 6
    assert summary.accuracy_1d_pct == Decimal("70.00")  # 7/10 with a 1d verdict
    assert summary.accuracy_5d_pct == Decimal("60.00")  # 6/10 with a 5d verdict


# ---------------------------------------------------------------------------
# render_memory
# ---------------------------------------------------------------------------
def test_write_memory_content() -> None:
    summary = compute_accuracy(
        [_row(True, True) for _ in range(7)] + [_row(False, False) for _ in range(3)]
    )
    md = render_memory("technical", summary, as_of=date(2026, 5, 29))
    assert "Technical Memory" in md
    assert "2026-05-29" in md
    assert "70" in md  # 1d accuracy percentage appears
    assert "Total picks tracked: 10" in md


# ---------------------------------------------------------------------------
# async behaviours (mocked session + repo — no real I/O)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_rankings_for_date() -> None:
    agent = OutcomeAgent()
    with patch(
        "backend.db.repositories.outcome.fetch_rankings_for_picks",
        new=AsyncMock(return_value=[]),
    ):
        n = await agent.record_picks(session=object(), pick_date=date(2026, 5, 29))
    assert n == 0


@pytest.mark.asyncio
async def test_missing_exit_price_skipped() -> None:
    agent = OutcomeAgent()
    pending = [_row(None, None)]
    with (
        patch(
            "backend.db.repositories.outcome.fetch_pending_1d",
            new=AsyncMock(return_value=pending),
        ),
        patch(
            "backend.db.repositories.outcome.fetch_pending_5d",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "backend.db.repositories.outcome.fetch_adj_close",
            new=AsyncMock(return_value={}),  # price not in DB
        ),
        patch(
            "backend.db.repositories.outcome.upsert_outcome",
            new=AsyncMock(),
        ) as mock_upsert,
    ):
        n = await agent.fill_exits(session=object(), as_of=date(2026, 5, 29))
    assert n == 0
    mock_upsert.assert_not_called()
