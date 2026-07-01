"""Step 14 — Caption Desk (reel caption + hashtags)."""
from __future__ import annotations

import re

from . import compliance_util as _c
from . import state
from .config import BRAND_NAME, BRAND_SITE, DISCLAIMER

CORE_TAGS = ["#IndianStockMarket", "#Nifty50", "#Sensex", "#BankNifty",
             "#StockMarketIndia", "#InvestingIndia", "#MarketNews",
             "#FinanceIndia", "#MavenResearch", "#TryMaven", "#StockMarketReels",
             "#FinanceReels"]

SECTOR_TAGS = {"it": "#ITStocks", "bank": "#BankingStocks", "auto": "#AutoStocks",
               "pharma": "#PharmaStocks", "energy": "#EnergyStocks",
               "metal": "#MetalStocks", "realty": "#RealtyStocks"}


def run(date: str, story: dict, hooks: dict, angle: dict) -> dict:
    hook = hooks["chosen"]["text"]
    why = " ".join(str(story.get("why_it_matters", "")).split()[:34])
    caption = (
        f"{hook}\n\n{why}\n\n"
        f"Follow {BRAND_NAME} for clean Indian market research → {BRAND_SITE}\n\n"
        f"{DISCLAIMER}"
    )
    blob = " ".join(story.get("affected_sectors", [])).lower()
    tags = list(CORE_TAGS)
    for key, tag in SECTOR_TAGS.items():
        if key in blob and tag not in tags:
            tags.append(tag)
    seen, deduped = set(), []
    for t in tags:
        if t.lower() not in seen and re.fullmatch(r"#\w+", t):
            seen.add(t.lower()); deduped.append(t)
    deduped = deduped[:18]

    comp = _c.evaluate({"caption": caption}, require_disclaimer_in=caption)
    cap_payload = {"date": date, "caption": caption, "hook": hook,
                   "cta": f"Follow {BRAND_NAME} → {BRAND_SITE}", "disclaimer": DISCLAIMER,
                   "char_count": len(caption),
                   "_compliance": {"ok": comp.ok, "violations": comp.violations, "score": comp.score}}
    state.save_artifact(date, "caption", cap_payload)
    state.save_artifact(date, "hashtags", {"date": date, "hashtags": deduped, "count": len(deduped)})
    return cap_payload
