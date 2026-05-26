"""Tests for the News Agent (Chunk 3.2) — matching + RSS parse, offline.

Stock matching is pure (in-memory). RSS fetch is exercised with respx mocking
the HTTP layer; feedparser parses the returned XML. No DB.
"""
from __future__ import annotations

import httpx
import respx

from backend.agents.news import (
    KnownStock,
    NewsAgent,
    RawArticle,
    dedup_by_url,
    match_to_isin,
)

KNOWN = [
    KnownStock("INE002A01018", "RELIANCE", "Reliance Industries Limited"),
    KnownStock("INE040A01034", "HDFCBANK", "HDFC Bank Limited"),
    KnownStock("INE467B01029", "TCS", "Tata Consultancy Services Limited"),
]

# Three-letter symbols that are also common English words — the 3.2
# false-positive trap ("Cooling Oil" -> OIL).
BLOCKLISTED = [
    KnownStock("INE274J01014", "OIL", "Oil India Limited"),
    KnownStock("INE079A01024", "SUN", "Sun Pharmaceutical Industries Limited"),
    KnownStock("INE176A01028", "YES", "Yes Bank Limited"),
]


# ---------------------------------------------------------------------------
# Stock matching
# ---------------------------------------------------------------------------
def test_match_exact_symbol() -> None:
    assert match_to_isin("RELIANCE shares jump 3%", None, KNOWN) == "INE002A01018"


def test_match_short_name_token() -> None:
    # "Reliance" (the symbol) appears even without the full company name
    assert match_to_isin("Reliance posts record profit", None, KNOWN) == "INE002A01018"


def test_match_full_company_name() -> None:
    assert (
        match_to_isin("Tata Consultancy Services wins deal", None, KNOWN)
        == "INE467B01029"
    )


def test_match_in_summary() -> None:
    assert (
        match_to_isin("Q4 results today", "HDFC Bank beats estimates", KNOWN)
        == "INE040A01034"
    )


def test_match_none_for_market_wide() -> None:
    assert match_to_isin("Nifty ends higher amid global cues", None, KNOWN) is None


def test_symbol_takes_priority() -> None:
    assert match_to_isin("RELIANCE Industries gains", None, KNOWN) == "INE002A01018"


# ---------------------------------------------------------------------------
# Short-symbol blocklist (Chunk 3.3 fix) — common English words that collide
# with 3-letter NSE symbols must NOT match without context confirmation.
# ---------------------------------------------------------------------------
def test_blocklisted_word_does_not_falsely_match() -> None:
    # "Oil" the commodity, not OIL India
    assert match_to_isin("Cooling oil prices ease pressure", None, BLOCKLISTED) is None
    assert match_to_isin("Sun shines on monsoon outlook", None, BLOCKLISTED) is None
    assert match_to_isin("He said yes to the merger talks", None, BLOCKLISTED) is None


def test_blocklisted_symbol_matches_with_context_word() -> None:
    assert (
        match_to_isin("OIL shares jump on results", None, BLOCKLISTED)
        == "INE274J01014"
    )
    assert (
        match_to_isin("NSE: YES rallies 5%", None, BLOCKLISTED) == "INE176A01028"
    )


def test_blocklisted_symbol_matches_with_company_name() -> None:
    assert (
        match_to_isin("Oil India Limited posts higher output", None, BLOCKLISTED)
        == "INE274J01014"
    )


# ---------------------------------------------------------------------------
# Dedup by source_url
# ---------------------------------------------------------------------------
def test_dedup_by_url() -> None:
    a = RawArticle("H1", None, "ET", "https://x.com/1", None)
    b = RawArticle("H1 dup", None, "MC", "https://x.com/1", None)
    c = RawArticle("H2", None, "ET", "https://x.com/2", None)
    out = dedup_by_url([a, b, c])
    assert len(out) == 2
    assert {r.source_url for r in out} == {"https://x.com/1", "https://x.com/2"}


# ---------------------------------------------------------------------------
# RSS fetch + parse (respx-mocked HTTP, feedparser parse)
# ---------------------------------------------------------------------------
_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>ET Markets</title>
<item><title>Reliance shares jump 3%</title><description>RIL gains on earnings</description>
<link>https://et.example/a1</link><pubDate>Mon, 25 May 2026 10:00:00 +0530</pubDate></item>
<item><title>Nifty ends higher</title><description>broad market rally</description>
<link>https://et.example/a2</link><pubDate>Mon, 25 May 2026 11:00:00 +0530</pubDate></item>
</channel></rss>"""


@respx.mock
async def test_fetch_rss_parses_items() -> None:
    url = "https://et.example/rss"
    respx.get(url).mock(
        return_value=httpx.Response(200, content=_RSS.encode("utf-8"))
    )
    articles = await NewsAgent().fetch_rss(url, "ET Markets")
    assert len(articles) == 2
    first = articles[0]
    assert first.headline == "Reliance shares jump 3%"
    assert first.source_url == "https://et.example/a1"
    assert first.source_name == "ET Markets"
    assert first.published_at is not None
