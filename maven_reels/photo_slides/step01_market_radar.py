"""Agent 1 — Market Radar.

Finds India finance / AI / tech / sector stories suitable for a 5-image
native photo Reel, plus the day's top sectors/themes. Uses the same FREE
live research providers as the legacy pipeline (read-only import). Never
fabricates: with no reachable provider it returns zero candidates and a
clear error — unless the caller explicitly asks for labelled simulation
data (used only for offline framework tests, flagged on every story).
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from urllib.parse import urlparse

# Read-only reuse of the free research providers + IST market-window logic.
from maven_reels.pipeline.research_providers import fetch_all
from maven_reels.pipeline.step1_research_backend import data_mode

from . import config, state

_NUM = re.compile(
    r"(?:₹|Rs\.?\s?)?\d[\d,]*(?:\.\d+)?"
    r"\s?(?:%|crore|cr|lakh|bn|billion|mn|million|bps)?", re.IGNORECASE)

_SECTOR_HINTS = {
    "Banking": ["bank", "hdfc", "icici", "sbi", "kotak", "axis", "nbfc", "psu bank"],
    "IT & AI": ["it ", "tcs", "infosys", "wipro", "hcl", "tech", " ai ",
                "artificial intelligence", "software"],
    "Auto": ["auto", "maruti", "tata motors", "mahindra", "ev ",
             "electric vehicle", "two-wheeler"],
    "Energy": ["oil", "gas", "reliance", "ongc", "power", "coal", "solar", "renewable"],
    "Pharma": ["pharma", "sun pharma", "cipla", "dr reddy", "healthcare", "hospital"],
    "FMCG": ["fmcg", "hul", "itc", "nestle", "consumer"],
    "Metals": ["steel", "metal", "tata steel", "jsw", "hindalco", "copper", "aluminium"],
    "Realty & Infra": ["realty", "real estate", "infra", "construction",
                       "cement", "l&t"],
    "Markets & Index": ["nifty", "sensex", "bank nifty", "index", "fii", "dii",
                        "smallcap", "midcap"],
    "Policy & Macro": ["rbi", "sebi", "budget", "gdp", "inflation", "cpi",
                       "repo", "policy", "gst", "tariff"],
    "IPO & Deals": ["ipo", "listing", "acquisition", "merger", "stake", "funding"],
}


def _sectors_of(text: str) -> list[str]:
    t = f" {text.lower()} "
    hits = [s for s, kws in _SECTOR_HINTS.items() if any(k in t for k in kws)]
    return hits or ["Markets & Index"]


def _visual_potential(sectors: list[str], text: str) -> str:
    if _NUM.search(text):
        return "strong — a single clear number can carry the hook slide"
    if "Policy & Macro" in sectors:
        return ("good — institution + decision framing works as clean "
                "editorial cards")
    return "moderate — needs a sharp headline treatment; no obvious number"


def _photo_reel_score(c: dict) -> int:
    """Deterministic 0-100: sourcing, numbers, simplicity, retail pull."""
    score = 40
    score += min(len(c["sources"]), 3) * 10                 # sourced + cross-checked
    if _NUM.search(f"{c['headline']} {c['summary']}"):
        score += 15                                          # has a concrete number
    if len(c["headline"].split()) <= 12:
        score += 10                                          # simple enough for a slide
    if set(c["sector_or_theme"].split(" & ")) & {"Banking", "Markets", "Policy"}:
        score += 5
    return min(score, 100)


def _sim_candidates(market_date: str) -> list[dict]:
    """Labelled SIMULATION stories for offline framework tests only.

    Every field says so — these must never be treated as real news and the
    QA gate refuses to pass a simulated package for publishing.
    """
    base = [
        ("SIMULATION: Index closes higher on broad buying interest",
         "Markets & Index",
         "Simulated sample story used to test the photo-reel framework "
         "offline. Not real market data."),
        ("SIMULATION: Policy review keeps rates unchanged",
         "Policy & Macro",
         "Simulated sample story used to test the photo-reel framework "
         "offline. Not real market data."),
    ]
    out = []
    for i, (h, s, m) in enumerate(base, start=1):
        out.append({
            "story_id": f"sim-{market_date}-{i}", "headline": h,
            "sector_or_theme": s, "summary": m,
            "sources": [{"name": "SIMULATION (no real source)", "url": ""}],
            "why_it_matters": "Framework test only — replace with a live run before review.",
            "visual_potential": "n/a (simulation)",
            "photo_reel_score": 0, "simulated": True,
        })
    return out


def _is_stale(published_at: str, max_age_days: int = 3) -> bool:
    """True when the story is clearly older than the reel window."""
    if not published_at:
        return False                    # no timestamp -> keep, fact check gates it
    try:
        dt = datetime.fromisoformat(published_at)
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=config.IST)
    return (config.now_ist() - dt).days > max_age_days


def run(job_id: str, *, allow_simulation: bool = False) -> dict:
    window, mkt_status = data_mode()
    market_date = config.now_ist().strftime("%Y-%m-%d")
    stories, used, errors = fetch_all()

    candidates: list[dict] = []
    seen: set[frozenset[str]] = set()
    for s in stories:
        headline = (s.get("headline") or "").strip()
        summary = (s.get("summary") or "").strip()
        url = (s.get("source_url") or "").strip()
        if not headline or not url:
            continue
        if _is_stale(s.get("published_at") or ""):
            continue                                        # old news is not today's reel
        key = frozenset(w for w in re.findall(r"[a-z]{4,}", headline.lower()))
        if any(len(key & k) >= max(3, int(len(key) * 0.7)) for k in seen):
            continue                                        # near-duplicate headline
        seen.add(key)
        text = f"{headline} {summary}"
        sectors = _sectors_of(text)
        cand = {
            "story_id": f"story-{len(candidates) + 1:02d}",
            "headline": headline,
            "sector_or_theme": sectors[0],
            "summary": summary or headline,
            "sources": [{"name": s.get("source_name") or urlparse(url).netloc,
                         "url": url}],
            "why_it_matters": (f"A {sectors[0]} development the kind of thing retail "
                               "investors track daily; sourced, not speculation."),
            "visual_potential": _visual_potential(sectors, text),
            "published_at": s.get("published_at"),
            "key_numbers": _NUM.findall(text)[:4],
        }
        cand["photo_reel_score"] = _photo_reel_score(
            {**cand, "sector_or_theme": " & ".join(sectors)})
        candidates.append(cand)

    data_mode_label = window
    if not candidates:
        if allow_simulation:
            candidates = _sim_candidates(market_date)
            data_mode_label = "simulation"
        else:
            data_mode_label = "unavailable"

    theme_counts = Counter(c["sector_or_theme"] for c in candidates
                           if not c.get("simulated"))
    candidates.sort(key=lambda c: c["photo_reel_score"], reverse=True)

    payload = {
        "market_date": market_date,
        "data_mode": data_mode_label,
        "market_status": mkt_status,
        "sources_used": used,
        "provider_errors": errors,
        "top_sectors_or_themes": [t for t, _ in theme_counts.most_common(5)],
        "candidate_stories": candidates[:12],
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "market_radar", payload)
    return payload
