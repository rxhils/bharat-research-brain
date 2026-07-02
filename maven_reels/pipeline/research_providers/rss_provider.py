"""RSS provider — zero-key, always available.

Pulls the latest Indian market headlines from trusted finance RSS feeds
(Tier A/B of the project whitelist). Individual feed failures are tolerated;
the provider fails only if EVERY feed fails.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .base import Story, http_get

NAME = "rss"

FEEDS = [
    ("Moneycontrol Markets", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Moneycontrol Buzzing", "https://www.moneycontrol.com/rss/buzzingstocks.xml"),
    ("Economic Times Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("LiveMint Markets", "https://www.livemint.com/rss/markets"),
    ("Business Standard Markets", "https://www.business-standard.com/rss/markets-106.rss"),
]


def configured() -> bool:
    return True


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _iso(pubdate: str) -> str:
    try:
        return parsedate_to_datetime(pubdate).isoformat(timespec="seconds")
    except Exception:
        return ""


def fetch(max_items: int = 25) -> list[Story]:
    out: list[Story] = []
    failures = 0
    per_feed = max(3, max_items // len(FEEDS))
    for name, url in FEEDS:
        try:
            root = ET.fromstring(http_get(url))
            items = root.findall(".//item")[:per_feed]
            for it in items:
                title = _text(it.find("title"))
                if not title:
                    continue
                out.append(Story.make(
                    headline=title,
                    summary=_text(it.find("description")) or title,
                    source_name=name,
                    source_url=_text(it.find("link")),
                    published_at=_iso(_text(it.find("pubDate"))),
                    provider=NAME))
        except Exception:
            failures += 1
    if failures == len(FEEDS):
        raise RuntimeError("all RSS feeds unreachable")
    return out
