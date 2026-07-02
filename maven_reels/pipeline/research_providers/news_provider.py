"""NewsAPI provider — active only when NEWSAPI_KEY is configured."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .base import TIMEOUT, UA, Story

NAME = "newsapi"


def configured() -> bool:
    return bool(os.getenv("NEWSAPI_KEY"))


def fetch(max_items: int = 15) -> list[Story]:
    q = urllib.parse.quote("(Nifty OR Sensex OR NSE OR BSE OR RBI OR SEBI) AND India")
    url = (f"https://newsapi.org/v2/everything?q={q}&language=en"
           f"&sortBy=publishedAt&pageSize={min(max_items, 25)}")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "X-Api-Key": os.getenv("NEWSAPI_KEY", "")})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read())
    return [Story.make(headline=a.get("title", ""),
                       summary=a.get("description", "") or a.get("title", ""),
                       source_name=(a.get("source") or {}).get("name", "newsapi"),
                       source_url=a.get("url", ""),
                       published_at=a.get("publishedAt", ""),
                       provider=NAME)
            for a in data.get("articles", []) if a.get("title")]
