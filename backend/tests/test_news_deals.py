"""Tests for the News Agent deal/announcement extension (Chunk 3.2 extension).

Sources are locally-downloaded published files (NSE bulk/block deals, BSE
announcements) — NSE/BSE website scraping is barred by CLAUDE.md §2 rule 5 / §12.
The parsers + article builders are pure; ISIN matching is a dict lookup
(nse_symbol -> isin for deals, BSE scrip code -> isin for announcements). No
network, no DB.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

from backend.agents.news import (
    AnnItem,
    DealItem,
    announcement_to_article,
    deal_to_article,
    parse_bse_announcements_json,
    parse_deals_json,
)

BULK_JSON = (
    '{"data":[{"BD_DT_DATE":"26-May-2026","BD_SYMBOL":"RELIANCE",'
    '"BD_CLIENT_NAME":"ABC Fund","BD_BUY_SELL":"BUY","BD_QTY_TRD":"500000",'
    '"BD_TP_WATP":"1350.50"}]}'
)

BSE_JSON = (
    '{"Table":[{"SCRIP_CD":"500325","HEADLINE":"Board Meeting Intimation",'
    '"DT_TM":"2026-05-26T10:30:00","ATTACHMENTNAME":"abc.pdf"}]}'
)


# ---------------------------------------------------------------------------
# parse_deals_json — NSE bulk/block deal file
# ---------------------------------------------------------------------------
def test_parse_deals_json_data_wrapper() -> None:
    items = parse_deals_json(BULK_JSON)
    assert len(items) == 1
    it = items[0]
    assert it.symbol == "RELIANCE"
    assert it.client_name == "ABC Fund"
    assert it.buy_sell == "BUY"
    assert it.qty == "500000"
    assert it.deal_date == date(2026, 5, 26)


def test_parse_deals_json_bare_array_generic_keys() -> None:
    items = parse_deals_json(
        '[{"symbol":"TCS","name":"XYZ Cap","qty":"100","BD_DT_DATE":"01-Apr-2026"}]'
    )
    assert items[0].symbol == "TCS"
    assert items[0].client_name == "XYZ Cap"
    assert items[0].deal_date == date(2026, 4, 1)


def test_parse_deals_json_empty() -> None:
    assert parse_deals_json('{"data":[]}') == []


# ---------------------------------------------------------------------------
# deal_to_article — headline, source_url, isin lookup, published_at
# ---------------------------------------------------------------------------
def test_deal_to_article_matched() -> None:
    it = DealItem("RELIANCE", "ABC Fund", "BUY", "500000", "1350.50", date(2026, 5, 26))
    art = deal_to_article(it, "nse_bulk_deal", "bulk", {"RELIANCE": "INE002A01018"})
    assert art.headline == "ABC Fund bulk deal in RELIANCE — 500000 shares"
    assert art.source_name == "nse_bulk_deal"
    assert art.isin == "INE002A01018"
    assert art.published_at == datetime(2026, 5, 26, tzinfo=UTC)
    assert "RELIANCE" in art.source_url
    assert "nse_bulk_deal" in art.source_url


def test_deal_to_article_unmatched_symbol() -> None:
    it = DealItem("UNKNOWN", "Foo", "SELL", "10", None, date(2026, 5, 26))
    art = deal_to_article(it, "nse_block_deal", "block", {"RELIANCE": "INE002A01018"})
    assert art.isin is None
    assert art.headline == "Foo block deal in UNKNOWN — 10 shares"


# ---------------------------------------------------------------------------
# parse_bse_announcements_json + announcement_to_article
# ---------------------------------------------------------------------------
def test_parse_bse_announcements_json() -> None:
    items = parse_bse_announcements_json(BSE_JSON)
    assert len(items) == 1
    it = items[0]
    assert it.scrip_cd == "500325"
    assert it.headline == "Board Meeting Intimation"
    assert it.dt_tm == datetime(2026, 5, 26, 10, 30, 0)
    assert it.attachment == "abc.pdf"


def test_announcement_to_article_matched_via_bse_code() -> None:
    it = AnnItem(
        "500325", "Board Meeting Intimation", datetime(2026, 5, 26, 10, 30), "abc.pdf"
    )
    art = announcement_to_article(it, {"500325": "INE002A01018"})
    assert art.headline == "Board Meeting Intimation"
    assert art.source_name == "bse_announcement"
    assert art.isin == "INE002A01018"
    assert "500325" in art.source_url


def test_announcement_to_article_unmatched() -> None:
    it = AnnItem("999999", "Some filing", None, None)
    art = announcement_to_article(it, {"500325": "INE002A01018"})
    assert art.isin is None
    assert art.source_name == "bse_announcement"
