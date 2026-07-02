"""Tavily provider — active only when TAVILY_API_KEY is configured."""
from __future__ import annotations

import json
import os
import urllib.request

from .base import TIMEOUT, UA, Story

NAME = "tavily"
QUERY = ("Indian stock market today Nifty Sensex close sector movers "
         "RBI SEBI FII DII news")


def configured() -> bool:
    return bool(os.getenv("TAVILY_API_KEY"))


def fetch(max_items: int = 15) -> list[Story]:
    body = json.dumps({
        "api_key": os.getenv("TAVILY_API_KEY"), "query": QUERY,
        "topic": "news", "days": 1, "max_results": min(max_items, 20),
        "search_depth": "basic",
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search", data=body,
        headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read())
    return [Story.make(headline=x.get("title", ""),
                       summary=x.get("content", "") or x.get("title", ""),
                       source_name=x.get("url", "").split("/")[2] if x.get("url") else "tavily",
                       source_url=x.get("url", ""),
                       published_at=x.get("published_date", ""),
                       provider=NAME)
            for x in data.get("results", []) if x.get("title")]
