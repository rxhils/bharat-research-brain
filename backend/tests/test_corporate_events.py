"""Tests for the Corporate Events Agent (Chunk 1.5, yfinance edition).

yfinance provides splits + dividends only. Pure mappers (raw event -> a
corporate_actions row) are unit tested here; the agent's row-building is
tested with a fake yfinance client (no network, no DB writes via dry_run).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.corporate_events import (
    CorpActionRow,
    CorporateEventsAgent,
    dividend_to_row,
    split_to_row,
)
from backend.data_sources.yfinance_client import RawDividend, RawSplit

ISIN = "INE002A01018"


# ---------------------------------------------------------------------------
# 1-2. Split mapping
# ---------------------------------------------------------------------------
def test_split_to_row() -> None:
    row = split_to_row(ISIN, RawSplit(date(2024, 10, 28), Decimal("2")))
    assert isinstance(row, CorpActionRow)
    assert row.action_type == "split"
    assert row.isin == ISIN
    assert row.ex_date == date(2024, 10, 28)
    assert row.ratio_numerator == Decimal("2")
    assert row.ratio_denominator == Decimal("1")
    assert row.amount_inr is None
    assert row.source == "yfinance"
    assert "split" in row.description.lower()


def test_reverse_split_keeps_factor() -> None:
    # 1-for-2 reverse split shows as 0.5 in yfinance; factor preserved as-is.
    row = split_to_row(ISIN, RawSplit(date(2023, 6, 1), Decimal("0.5")))
    assert row.ratio_numerator == Decimal("0.5")
    assert row.ratio_denominator == Decimal("1")


# ---------------------------------------------------------------------------
# 3. Dividend mapping
# ---------------------------------------------------------------------------
def test_dividend_to_row() -> None:
    row = dividend_to_row(ISIN, RawDividend(date(2024, 8, 19), Decimal("5.50")))
    assert row.action_type == "dividend"
    assert row.ex_date == date(2024, 8, 19)
    assert row.amount_inr == Decimal("5.50")
    assert row.ratio_numerator is None
    assert row.ratio_denominator is None
    assert "dividend" in row.description.lower()


# ---------------------------------------------------------------------------
# Fake yfinance client for agent-level tests
# ---------------------------------------------------------------------------
class _FakeYF:
    def __init__(self, data: dict[str, tuple[list[RawSplit], list[RawDividend]]]):
        self._data = data
        self.calls: list[str] = []

    async def fetch_corporate_actions(
        self, yf_symbol: str, *, start: date, end: date
    ) -> tuple[list[RawSplit], list[RawDividend]]:
        self.calls.append(yf_symbol)
        if yf_symbol == "BOOM.NS":
            raise RuntimeError("yfinance blew up")
        return self._data.get(yf_symbol, ([], []))


# ---------------------------------------------------------------------------
# 4. Agent builds rows from fake client (dry-run, no writes)
# ---------------------------------------------------------------------------
async def test_agent_builds_rows_dry_run() -> None:
    fake = _FakeYF(
        {
            "RELIANCE.NS": (
                [RawSplit(date(2024, 10, 28), Decimal("2"))],
                [RawDividend(date(2024, 8, 19), Decimal("10"))],
            )
        }
    )
    agent = CorporateEventsAgent(client=fake)  # type: ignore[arg-type]

    async def fake_symbols(session: object) -> list[tuple[str, str]]:
        return [("INE002A01018", "RELIANCE")]

    agent._load_active_symbols = fake_symbols  # type: ignore[method-assign]
    result = await agent.backfill(years=5, dry_run=True)

    assert result.stocks_attempted == 1
    assert result.stocks_succeeded == 1
    assert result.splits == 1
    assert result.dividends == 1
    assert result.rows_ready == 2
    assert result.rows_inserted == 0  # dry-run
    assert fake.calls == ["RELIANCE.NS"]  # derived .NS symbol


# ---------------------------------------------------------------------------
# 5. A per-symbol fetch failure is counted, not fatal
# ---------------------------------------------------------------------------
async def test_agent_handles_fetch_failure() -> None:
    fake = _FakeYF({})
    agent = CorporateEventsAgent(client=fake)  # type: ignore[arg-type]

    async def fake_symbols(session: object) -> list[tuple[str, str]]:
        return [("INE002A01018", "RELIANCE"), ("INEBOOMXXXXX", "BOOM")]

    agent._load_active_symbols = fake_symbols  # type: ignore[method-assign]
    result = await agent.backfill(years=5, dry_run=True)

    assert result.stocks_attempted == 2
    assert result.stocks_failed == 1
    assert result.stocks_succeeded == 1
