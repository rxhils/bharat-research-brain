"""Agent — Location Scout (Maven Reels Newsroom). Local, free, deterministic.

The heart of the rework: instead of abstract AI dashboards, choose a realistic
FOOTAGE WORLD (real newsroom, investor-on-phone, banking hall, sector b-roll,
policy, market stress/rally) that matches the actual story, and set the shot
style (lighting/camera/mood/palette/realism). Writes location_scout.json.

Does NOT generate anything or spend credits — it produces creative direction the
Shot Planner / Prompt Bible / Camera Router consume.
"""
from __future__ import annotations

import re

from . import state

# story signal -> footage world
_WORLDS = {
    "banking_financial_system": {
        "keywords": {"bank", "banks", "banking", "bank nifty", "banknifty", "hdfc", "icici",
                     "sbi", "axis", "kotak", "lender", "lenders", "credit", "loan", "loans",
                     "nbfc", "financials", "psu bank"},
        "why": "The story is driven by banks/financials — show the banking system, not a generic chart.",
        "refs": ["modern Indian bank branch interior", "finance desk with blurred non-readable screens",
                 "banking hall with soft motion", "credit/loan flow metaphor through a clean data corridor"],
        "rules": ["no readable account data", "no real bank logos", "premium, calm, institutional"],
        "shot_style": {"lighting": "clean cool institutional", "camera": "slow dolly / glide",
                       "mood": "steady, credible", "color_palette": "navy + teal + soft white",
                       "realism_level": "photoreal finance environment"},
    },
    "policy_institutional": {
        "keywords": {"rbi", "sebi", "policy", "repo", "rate", "rates", "mpc", "budget",
                     "regulation", "regulator", "government", "ministry", "circular", "inflation", "cpi"},
        "why": "A policy/regulatory story — show an institutional, official-but-not-fake-logo world.",
        "refs": ["institutional office corridor", "policy signal pulsing through a finance system",
                 "official document mood without readable text", "central-bank-style architecture at dusk"],
        "rules": ["no fake RBI/SEBI logos", "no readable policy text", "authoritative, restrained"],
        "shot_style": {"lighting": "warm institutional", "camera": "measured push-in",
                       "mood": "authoritative, weighty", "color_palette": "amber + deep blue",
                       "realism_level": "photoreal institutional"},
    },
    "sector_broll": {
        "keywords": {"it", "tech", "technology", "infosys", "tcs", "energy", "power", "oil",
                     "auto", "automobile", "pharma", "pharmaceutical", "defence", "defense",
                     "metal", "metals", "steel", "realty", "real estate", "fmcg", "cement"},
        "why": "A single-sector story — show that sector's real world, not an index dashboard.",
        "refs": ["server room (IT)", "energy grid / power lines (energy)", "auto production line (auto)",
                 "pharma lab (pharma)", "defence manufacturing (defence)", "construction site (realty)"],
        "rules": ["match the b-roll to the actual sector", "no fake tickers", "premium industrial realism"],
        "shot_style": {"lighting": "sector-appropriate practical", "camera": "smooth tracking",
                       "mood": "purposeful", "color_palette": "sector-tinted with teal accent",
                       "realism_level": "photoreal industrial"},
    },
    "market_stress": {
        "keywords": {"fall", "fell", "drop", "dropped", "crash", "slump", "plunge", "sell-off",
                     "selloff", "volatility", "risk-off", "correction", "decline", "declined", "red"},
        "why": "A down/volatile session — cinematic tension, not a cheerful dashboard.",
        "refs": ["dark finance office, monitors reflecting movement", "investor watching a screen, tense",
                 "cinematic low-key newsroom", "red/amber light accents on glass"],
        "rules": ["tension without fearmongering", "no crash-porn", "no fake red numbers"],
        "shot_style": {"lighting": "low-key, high contrast", "camera": "slow creeping push-in",
                       "mood": "tense, serious", "color_palette": "charcoal + amber/red accent",
                       "realism_level": "cinematic photoreal"},
    },
    "market_rally": {
        "keywords": {"rise", "rose", "rally", "rallied", "surge", "surged", "gain", "gains", "record",
                     "high", "highs", "outperform", "outperformed", "green", "up", "jumped"},
        "why": "An up session — brighter, confident, optimistic realism.",
        "refs": ["bright modern trading floor", "confident analyst desk, morning light",
                 "smooth camera over a clean market wall", "green highlights on glass"],
        "rules": ["confident not hype", "no fake green numbers", "premium optimism"],
        "shot_style": {"lighting": "bright, airy", "camera": "smooth rising glide",
                       "mood": "confident, optimistic", "color_palette": "deep blue + green accent",
                       "realism_level": "cinematic photoreal"},
    },
    "investor_phone_pov": {
        "keywords": {"retail", "investor", "investors", "app", "sip", "portfolio", "beginner",
                     "how to", "explained", "demat", "mutual fund"},
        "why": "A retail-education angle — show a real investor's POV, relatable and premium.",
        "refs": ["person checking a market app on phone (screen blurred)", "hands + phone at a cafe desk",
                 "clean Indian finance lifestyle", "closeup of a phone with abstract non-readable UI"],
        "rules": ["no readable fake app data", "relatable, aspirational", "clean lifestyle realism"],
        "shot_style": {"lighting": "soft natural", "camera": "intimate handheld-stable",
                       "mood": "relatable, calm", "color_palette": "warm neutral + teal",
                       "realism_level": "photoreal lifestyle"},
    },
    "finance_newsroom": {  # default
        "keywords": {"nifty", "sensex", "market", "markets", "index", "indices", "wrap",
                     "close", "closing", "session", "benchmark", "sentiment", "fii", "dii"},
        "why": "A broad-market story — a premium finance newsroom is the safe, credible default.",
        "refs": ["premium finance newsroom monitors", "analyst desk with blurred non-readable data",
                 "business-media environment", "market screen wall with soft motion"],
        "rules": ["no readable fake data", "premium business-media look", "no cartoon bull/bear"],
        "shot_style": {"lighting": "clean broadcast", "camera": "controlled dolly/glide",
                       "mood": "credible, premium", "color_palette": "navy + teal + white",
                       "realism_level": "photoreal broadcast"},
    },
}

_GLOBAL_AVOID = [
    "abstract AI dashboards as the only visual", "fake readable text", "fake numbers",
    "fake stock tickers", "fake company logos", "buy/sell arrows", "cartoon bull or bear",
    "meme style", "cheap AI look", "generic purple gradient finance background",
]


def _story_text(story: dict) -> str:
    return " ".join(str(story.get(k, "")) for k in
                    ("headline", "summary", "what_happened", "why_it_matters", "category",
                     "affected_sectors", "affected_companies")).lower()


def classify(story: dict) -> str:
    """Return the best footage world for a story (finance_newsroom default)."""
    text = _story_text(story)
    best, best_hits = "finance_newsroom", 0
    # sentiment/sector worlds win over the newsroom default when they clearly hit
    order = ["banking_financial_system", "policy_institutional", "sector_broll",
             "market_stress", "market_rally", "investor_phone_pov", "finance_newsroom"]
    for world in order:
        hits = sum(1 for kw in _WORLDS[world]["keywords"] if kw in text)
        if hits > best_hits:
            best, best_hits = world, hits
    return best


def run(date: str, *, story: dict | None = None) -> dict:
    story = story or _load_story(date)
    world = classify(story or {})
    w = _WORLDS[world]
    payload = {
        "date": date,
        "selected_footage_world": world,
        "why_this_world_fits": w["why"],
        "realistic_visual_references": w["refs"],
        "scene_environment_rules": w["rules"],
        "avoid": _GLOBAL_AVOID,
        "shot_style": w["shot_style"],
    }
    state.save_artifact(date, "location_scout", payload)
    return payload


def _load_story(date: str) -> dict:
    for key in ("viral_fit", "research"):
        try:
            art = state.load_artifact(date, key)
        except Exception:
            continue
        if key == "viral_fit":
            st = (art.get("chosen") or {}).get("story") or art.get("selected_story")
            if st:
                return st
        else:
            stories = art.get("top_3_stories") or art.get("stories") or []
            if stories:
                return stories[0]
    return {}
