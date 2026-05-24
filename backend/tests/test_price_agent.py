"""Tests for the Price Agent + NSE bhavcopy client (Chunk 1.3).

Parsing / filtering tests are pure. HTTP tests use respx against the real
fetch path. Orchestration tests monkeypatch the calendar/prices repos so no
real DB is touched, and run the agent in dry-run mode (no inserts). One
repo-level idempotency test hits the live DB inside a rolled-back transaction.
"""
from __future__ import annotations

import uuid
import zipfile
from datetime import date
from decimal import Decimal
from io import BytesIO

import httpx
import pytest
import respx
from sqlalchemy import select

from backend.agents.price import PriceAgent, PriceResult
from backend.data_sources.nse_bhavcopy import (
    BhavRow,
    NSEBhavcopyClient,
    filter_rows,
    new_format_url,
    old_format_url,
    parse_new_format,
    parse_old_format,
)
from backend.db.repositories import calendar as calendar_repo
from backend.db.repositories import prices as prices_repo
from backend.errors import DataSourceError

KNOWN = "INE040A01034"  # HDFCBANK — present in the live universe


# ---------------------------------------------------------------------------
# Fixtures: in-memory bhavcopy CSV + ZIP builders
# ---------------------------------------------------------------------------
# UDiFF format (current): TtlTradgVol / TtlTrfVal (rupees) / TtlNbOfTxsExctd,
# no delivery columns. TtlTrfVal=15000000 rupees → 1.5 crore.
NEW_CSV = (
    "TradDt,SctySrs,ISIN,OpnPric,HghPric,LwPric,ClsPric,TtlTradgVol,TtlTrfVal,"
    "TtlNbOfTxsExctd\n"
    "24-Jan-2024,EQ,INE040A01034,100.5,105.0,99.0,103.2,1000,15000000,50\n"
)

# Old historical format: TOTTRDVAL in rupees. 15000000 rupees → 1.5 crore.
OLD_CSV = (
    "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,"
    "TIMESTAMP,TOTALTRADES,ISIN,DELIV_QTY,DELIV_PER\n"
    "HDFCBANK,EQ,100.5,105.0,99.0,103.2,103.0,100.0,1000,15000000,24-Jan-2020,"
    "50,INE040A01034,600,60.0\n"
)


def _zip(csv_text: str, name: str = "data.csv") -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, csv_text)
    return buf.getvalue()


def _row(
    isin: str = KNOWN,
    series: str = "EQ",
    open_: str = "100",
    high: str = "110",
    low: str = "95",
    close: str = "105",
) -> BhavRow:
    return BhavRow(
        isin=isin,
        trade_date=date(2024, 1, 24),
        series=series,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=1000,
        value_inr_cr=Decimal("1.5"),
        trades_count=50,
        delivery_qty=600,
        delivery_pct=Decimal("60.0"),
    )


async def _fake_known(session: object) -> set[str]:
    return {KNOWN}


# ---------------------------------------------------------------------------
# 1-2. CSV parsing
# ---------------------------------------------------------------------------
def test_parse_new_format_csv() -> None:
    rows = parse_new_format(NEW_CSV)
    assert len(rows) == 1
    r = rows[0]
    assert r.isin == "INE040A01034"
    assert r.trade_date == date(2024, 1, 24)
    assert r.series == "EQ"
    assert r.open == Decimal("100.5")
    assert r.high == Decimal("105.0")
    assert r.low == Decimal("99.0")
    assert r.close == Decimal("103.2")
    assert r.volume == 1000
    assert r.value_inr_cr == Decimal("1.5")  # 15,000,000 rupees → 1.5 cr
    assert r.delivery_qty is None  # UDiFF carries no delivery columns
    assert r.delivery_pct is None


def test_parse_old_format_csv() -> None:
    rows = parse_old_format(OLD_CSV)
    assert len(rows) == 1
    r = rows[0]
    assert r.isin == "INE040A01034"
    assert r.trade_date == date(2020, 1, 24)
    # 15,000,000 rupees / 1e7 → 1.5 crores
    assert r.value_inr_cr == Decimal("1.5")


# ---------------------------------------------------------------------------
# 3. Series filter (EQ kept, SM dropped)
# ---------------------------------------------------------------------------
def test_series_filter() -> None:
    rows = [_row(isin="INE111A01011", series="SM"), _row(isin=KNOWN, series="EQ")]
    good, _warnings = filter_rows(rows, {"INE111A01011", KNOWN})
    assert len(good) == 1
    assert good[0].series == "EQ"


# ---------------------------------------------------------------------------
# 4. Zero / negative close → skipped + warned
# ---------------------------------------------------------------------------
def test_zero_price_skipped_and_warned() -> None:
    good, warnings = filter_rows([_row(close="0")], {KNOWN})
    assert good == []
    assert any(w.code == "ZERO_OR_NEGATIVE_PRICE" and w.isin == KNOWN for w in warnings)


# ---------------------------------------------------------------------------
# 5. OHLC violation (close below low) → skipped + warned
# ---------------------------------------------------------------------------
def test_ohlc_violation_skipped_and_warned() -> None:
    good, warnings = filter_rows(
        [_row(open_="115", high="120", low="110", close="103")], {KNOWN}
    )
    assert good == []
    assert any(w.code == "OHLC_VIOLATION" for w in warnings)


# ---------------------------------------------------------------------------
# 6. ISIN outside our universe → silently skipped (no warning)
# ---------------------------------------------------------------------------
def test_universe_filter() -> None:
    good, warnings = filter_rows([_row(isin="INE999X01019")], {KNOWN})
    assert good == []
    assert warnings == []


# ---------------------------------------------------------------------------
# 7. Soft-404 (HTTP 200 + HTML body) on both URLs → DataSourceError
# ---------------------------------------------------------------------------
@respx.mock
async def test_soft_404_detection() -> None:
    d = date(2024, 1, 24)
    html = b"<!DOCTYPE html><html><title>Error 404</title></html>"
    respx.get(new_format_url(d)).mock(return_value=httpx.Response(200, content=html))
    respx.get(old_format_url(d)).mock(return_value=httpx.Response(200, content=html))
    client = NSEBhavcopyClient()
    with pytest.raises(DataSourceError) as exc:
        await client.fetch_for_date(d, cache_ttl=0)
    assert exc.value.reason_code == "soft_404_html_body"


# ---------------------------------------------------------------------------
# 8. Backfill skips dates already present (no download attempted)
# ---------------------------------------------------------------------------
@respx.mock
async def test_backfill_skips_present_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    d1, d2 = date(2024, 1, 2), date(2024, 1, 3)

    async def fake_open(session, start, end, exchange="NSE"):  # noqa: ANN001
        return [d1, d2]

    async def fake_present(session, start, end):  # noqa: ANN001
        return {d1}

    monkeypatch.setattr(calendar_repo, "get_open_dates", fake_open)
    monkeypatch.setattr(prices_repo, "get_dates_present", fake_present)

    route1 = respx.get(new_format_url(d1)).mock(
        return_value=httpx.Response(200, content=_zip(NEW_CSV))
    )
    route2 = respx.get(new_format_url(d2)).mock(
        return_value=httpx.Response(200, content=_zip(NEW_CSV))
    )

    agent = PriceAgent()
    agent._load_known_isins = _fake_known  # type: ignore[method-assign]
    result = await agent.backfill(start=d1, end=d2, dry_run=True, cache_ttl=0)

    assert route1.called is False  # already present → never downloaded
    assert route2.called is True
    assert result.dates_attempted == 1


# ---------------------------------------------------------------------------
# 9. New URL 404 → falls back to old URL successfully
# ---------------------------------------------------------------------------
@respx.mock
async def test_backfill_missing_date_404_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d = date(2020, 1, 24)

    async def fake_open(session, start, end, exchange="NSE"):  # noqa: ANN001
        return [d]

    async def fake_present(session, start, end):  # noqa: ANN001
        return set()

    monkeypatch.setattr(calendar_repo, "get_open_dates", fake_open)
    monkeypatch.setattr(prices_repo, "get_dates_present", fake_present)

    respx.get(new_format_url(d)).mock(return_value=httpx.Response(404))
    respx.get(old_format_url(d)).mock(
        return_value=httpx.Response(200, content=_zip(OLD_CSV))
    )

    agent = PriceAgent()
    agent._load_known_isins = _fake_known  # type: ignore[method-assign]
    result = await agent.backfill(start=d, end=d, dry_run=True, cache_ttl=0)

    assert result.dates_succeeded == 1
    assert result.rows_ready == 1


# ---------------------------------------------------------------------------
# 10. Both URLs 404 → BHAVCOPY_MISSING warning, no crash, continues
# ---------------------------------------------------------------------------
@respx.mock
async def test_backfill_both_urls_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    d = date(2020, 1, 24)

    async def fake_open(session, start, end, exchange="NSE"):  # noqa: ANN001
        return [d]

    async def fake_present(session, start, end):  # noqa: ANN001
        return set()

    monkeypatch.setattr(calendar_repo, "get_open_dates", fake_open)
    monkeypatch.setattr(prices_repo, "get_dates_present", fake_present)

    respx.get(new_format_url(d)).mock(return_value=httpx.Response(404))
    respx.get(old_format_url(d)).mock(return_value=httpx.Response(404))

    agent = PriceAgent()
    agent._load_known_isins = _fake_known  # type: ignore[method-assign]
    result = await agent.backfill(start=d, end=d, dry_run=True, cache_ttl=0)

    assert result.dates_failed == 1
    assert result.dates_succeeded == 0
    assert any(w.code == "BHAVCOPY_MISSING" for w in result.warnings)


# ---------------------------------------------------------------------------
# 11. Idempotency — second bulk_insert of the same rows inserts 0 (live DB)
# ---------------------------------------------------------------------------
async def test_idempotency() -> None:
    from backend.db.models import Stock
    from backend.db.session import SessionLocal
    from backend.services.runs import open_run

    async with SessionLocal() as session:
        isin = (await session.execute(select(Stock.isin).limit(1))).scalar_one()
        run_pk = await open_run(session, agent_name="prices-test", run_id=uuid.uuid4())
        await session.flush()
        row = BhavRow(
            isin=isin,
            trade_date=date(2099, 1, 1),  # far future — never collides with backfill
            series="EQ",
            open=Decimal("1"),
            high=Decimal("2"),
            low=Decimal("1"),
            close=Decimal("1.5"),
            volume=1,
            value_inr_cr=Decimal("0.0001"),
            trades_count=1,
            delivery_qty=0,
            delivery_pct=Decimal("0"),
        )
        n1 = await prices_repo.bulk_insert(session, [row], ingestion_run_id=run_pk)
        n2 = await prices_repo.bulk_insert(session, [row], ingestion_run_id=run_pk)
        assert n1 == 1
        assert n2 == 0
        await session.rollback()


# ---------------------------------------------------------------------------
# 12. Dry-run performs no inserts
# ---------------------------------------------------------------------------
@respx.mock
async def test_dry_run_no_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    d = date(2024, 1, 24)
    calls = {"n": 0}

    async def fake_open(session, start, end, exchange="NSE"):  # noqa: ANN001
        return [d]

    async def fake_present(session, start, end):  # noqa: ANN001
        return set()

    async def spy_bulk(session, rows, *, ingestion_run_id, **kw):  # noqa: ANN001
        calls["n"] += 1
        return len(rows)

    monkeypatch.setattr(calendar_repo, "get_open_dates", fake_open)
    monkeypatch.setattr(prices_repo, "get_dates_present", fake_present)
    monkeypatch.setattr(prices_repo, "bulk_insert", spy_bulk)

    respx.get(new_format_url(d)).mock(
        return_value=httpx.Response(200, content=_zip(NEW_CSV))
    )

    agent = PriceAgent()
    agent._load_known_isins = _fake_known  # type: ignore[method-assign]
    result = await agent.backfill(start=d, end=d, dry_run=True, cache_ttl=0)

    assert calls["n"] == 0  # bulk_insert never called in dry-run
    assert isinstance(result, PriceResult)
    assert result.rows_inserted == 0
