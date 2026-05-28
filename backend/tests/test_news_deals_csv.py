"""Tests for NSE bulk/block deal CSV ingest (Build B).

Pure parsing only — synthetic CSV strings, no network, no DB, no files. The
operator downloads NSE bulk/block-deal CSVs (permitted file-ingest; NSE website
scraping is barred by CLAUDE.md §2 rule 5 / §12) and the agent parses them into
`RawArticle` rows keyed by a slugified `source_url` dedup key.
"""
from __future__ import annotations

from datetime import UTC, datetime

from backend.agents.news import parse_block_deals_csv, parse_bulk_deals_csv

_KNOWN = {"RELIANCE": "INE002A01018", "TCS": "INE467B01029"}

# Real NSE deal-file header (note the price column name + trailing REMARKS).
_HEADER = (
    "DATE,SYMBOL,SECURITY NAME,CLIENT NAME,BUY/SELL,QUANTITY TRADED,"
    "TRADE PRICE/ WEIGHTED. AVG. PRICE,REMARKS\n"
)


def test_parse_bulk_three_rows() -> None:
    csv_text = _HEADER + (
        '26-May-2026,RELIANCE,Reliance Industries Ltd,SOME FUND,BUY,"1,00,000",2890.50,-\n'
        '26-May-2026,TCS,Tata Consultancy Services,OTHER FUND,SELL,"50,000","1,225.00",-\n'
        '26-May-2026,UNKNOWNX,Unknown Co Ltd,XYZ CAP,BUY,"10,000",100.00,-\n'
    )
    arts = parse_bulk_deals_csv(csv_text, _KNOWN)
    # Unknown symbol (row 3) is skipped -> 2 articles.
    assert len(arts) == 2
    assert arts[0].isin == "INE002A01018"
    assert arts[0].source_name == "nse_bulk_deal"
    assert arts[1].isin == "INE467B01029"
    assert arts[0].published_at == datetime(2026, 5, 26, tzinfo=UTC)


def test_headline_format_exact() -> None:
    csv_text = _HEADER + (
        '26-May-2026,RELIANCE,Reliance Industries Ltd,SOME FUND,BUY,"1,00,000",2890.50,-\n'
    )
    arts = parse_bulk_deals_csv(csv_text, _KNOWN)
    assert arts[0].headline == "SOME FUND BUY deal in RELIANCE — 100,000 shares @ ₹2,890.50"


def test_source_url_unique_per_deal() -> None:
    csv_text = _HEADER + (
        '26-May-2026,RELIANCE,Reliance,FUND A,BUY,"1,00,000",2890.50,-\n'
        '26-May-2026,TCS,Tata,FUND B,SELL,"50,000",1225.00,-\n'
    )
    arts = parse_bulk_deals_csv(csv_text, _KNOWN)
    urls = [a.source_url for a in arts]
    assert len(set(urls)) == len(urls) == 2
    assert urls[0] == "nse-bulk-reliance-2026-05-26-fund-a"


def test_unknown_symbol_skipped_not_crashed() -> None:
    csv_text = _HEADER + '26-May-2026,NOTLISTED,Some Co,FUND,BUY,"1,000",10.00,-\n'
    assert parse_bulk_deals_csv(csv_text, _KNOWN) == []


def test_blank_price_skipped_not_crashed() -> None:
    csv_text = _HEADER + '26-May-2026,RELIANCE,Reliance,FUND,BUY,"1,00,000",,-\n'
    assert parse_bulk_deals_csv(csv_text, _KNOWN) == []


def test_block_deals_source_name_and_url_prefix() -> None:
    csv_text = _HEADER + '26-May-2026,TCS,Tata,FUND,BUY,"50,000",1225.00,-\n'
    arts = parse_block_deals_csv(csv_text, _KNOWN)
    assert len(arts) == 1
    assert arts[0].source_name == "nse_block_deal"
    assert arts[0].source_url.startswith("nse-block-tcs-2026-05-26-")
