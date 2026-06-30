"""Step 6 — Hashtags.

10-18 relevant, non-spammy tags: a stable core (broad Indian-market + brand) plus
a few derived from today's sectors/companies. De-duplicated, capped.
"""
from __future__ import annotations

import re

from . import schemas, state

CORE = [
    "#IndianStockMarket", "#Nifty50", "#Sensex", "#BankNifty",
    "#StockMarketIndia", "#InvestingIndia", "#IndianInvestors",
    "#MarketNews", "#FinanceIndia", "#StockMarketEducation",
    "#MavenResearch", "#TryMaven",
]

SECTOR_TAGS = {
    "auto": "#AutoStocks",
    "bank": "#BankingStocks",
    "financial": "#FinancialServices",
    "it": "#ITStocks",
    "oil": "#OilAndGas",
    "energy": "#EnergyStocks",
    "pharma": "#PharmaStocks",
    "metal": "#MetalStocks",
    "fmcg": "#FMCG",
}


def _derive_from_research(research: dict, limit: int) -> list[str]:
    found: list[str] = []
    blob = " ".join(
        " ".join(s.get("affected_sectors", [])) for s in research["top_3_stories"]
    ).lower()
    for key, tag in SECTOR_TAGS.items():
        if key in blob and tag not in found:
            found.append(tag)
        if len(found) >= limit:
            break
    return found


def run(date: str, research: dict) -> dict:
    tags = list(CORE)
    for t in _derive_from_research(research, limit=4):
        if t not in tags:
            tags.append(t)

    # De-dup case-insensitively, keep order, cap at 18.
    seen, deduped = set(), []
    for t in tags:
        key = t.lower()
        if key not in seen and re.fullmatch(r"#\w+", t):
            seen.add(key)
            deduped.append(t)
    deduped = deduped[:18]

    payload = {"date": date, "hashtags": deduped, "count": len(deduped)}
    schemas.validate_hashtags(payload)
    state.save_artifact(date, "hashtags", payload)
    return payload
