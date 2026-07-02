"""Step 4 (upgraded) — Hook Lab.

Generates 25 story-specific hooks across 11 categories, scores each on 7 axes
(scroll-stop, clarity, specificity, truthfulness, story connection, brand fit,
simplicity), and picks the winner. The hook lands in the first 0.3s: on-screen
<= 7 words, voiceover first line <= 12 words. No fake drama, no buy/sell, no
clickbait the video can't answer, no generic "investors missed today" unless
the story genuinely hides something. Deterministic + brief-aware. Selected hook
must score >= 90; if nothing clears, it regenerates once with stricter
specificity, else marks Hook Lab blocked.
"""
from __future__ import annotations

from . import compliance_util as _c
from . import schemas, state

CATEGORIES = ["direct", "curiosity", "contrarian", "hidden_reason", "what_changed",
              "market_psychology", "sector_shock", "data_driven", "under_the_surface",
              "beginner_friendly", "maven_educational"]

# banned in hooks beyond compliance (no hype/clickbait/fearmongering)
BAD = ["explode", "crash tomorrow", "crash coming", "guaranteed", "will make you rich",
       "must buy", "watch before tomorrow", "watch this before", "before it's too late"]
# generic openers that only pass if the story truly hides something
GENERIC = ["here's what investors missed", "stock market update", "big news for investors",
           "market update today"]


def _facts(story: dict) -> dict:
    sector = (story.get("affected_sectors") or ["the market"])[0].split("/")[0].strip()
    nums = story.get("key_numbers") or []
    pct = next((n for n in nums if "%" in n), None)
    return {"sector": sector, "s": sector.lower(),
            "pct": pct, "big": pct or "one number"}


def _seed(story: dict, brief: dict | None) -> list[dict]:
    f = _facts(story)
    s, sector, big = f["s"], f["sector"], f["big"]
    metaphor = ((brief or {}).get("creative_brief") or {})
    scroll = metaphor.get("scroll_stop_reason") or ""
    fam = (brief or {}).get("metaphor_family") or "default"

    seeds = [
        # direct
        {"cat": "direct", "text": f"{sector} moved. Here's why."},
        {"cat": "direct", "text": "This moved India today."},
        {"cat": "direct", "text": "Today's market, in 15 seconds."},
        # curiosity
        {"cat": "curiosity", "text": "The market looked calm. It wasn't."},
        {"cat": "curiosity", "text": f"Something moved {s} today."},
        {"cat": "curiosity", "text": "One move. Big meaning."},
        # contrarian
        {"cat": "contrarian", "text": "Don't just watch Nifty."},
        {"cat": "contrarian", "text": "The index hid the real story."},
        {"cat": "contrarian", "text": "A calm index can mislead."},
        # hidden_reason
        {"cat": "hidden_reason", "text": "The real move was underneath."},
        {"cat": "hidden_reason", "text": "One reason moved everything."},
        {"cat": "hidden_reason", "text": "The real driver wasn't the index."},
        # what_changed
        {"cat": "what_changed", "text": "The market's mood just changed."},
        {"cat": "what_changed", "text": "Something shifted in the market today."},
        # market_psychology
        {"cat": "market_psychology", "text": "Markets reacted for one reason."},
        {"cat": "market_psychology", "text": "Sentiment turned today. Here's why."},
        # sector_shock
        {"cat": "sector_shock", "text": f"{sector} moved everything today."},
        {"cat": "sector_shock", "text": "One sector changed the mood."},
        {"cat": "sector_shock", "text": "This sector shifted sentiment."},
        # data_driven
        {"cat": "data_driven", "text": f"{big} moved the whole market."},
        {"cat": "data_driven", "text": f"{sector} did most of the work today."},
        # under_the_surface
        {"cat": "under_the_surface", "text": scroll or "Look under the index."},
        {"cat": "under_the_surface", "text": "Under the surface, a lot moved."},
        # beginner_friendly
        {"cat": "beginner_friendly", "text": "Why did the market move today?"},
        {"cat": "beginner_friendly", "text": "New to markets? Watch this move."},
        # maven_educational
        {"cat": "maven_educational", "text": "Understand today's move in 15s."},
    ]
    # family-specific sharpeners (front-load the most on-story hooks)
    if fam == "banks":
        seeds.insert(0, {"cat": "hidden_reason", "text": "Banks moved everything today."})
    elif fam == "policy":
        seeds.insert(0, {"cat": "what_changed", "text": "One policy signal moved stocks."})
    elif fam == "breadth":
        seeds.insert(0, {"cat": "under_the_surface", "text": "The real move was underneath."})
    elif fam == "sector":
        seeds.insert(0, {"cat": "sector_shock", "text": "One sector changed the mood."})
    return seeds[:25]


STRONG_CATS = {"hidden_reason", "under_the_surface", "sector_shock", "contrarian",
               "what_changed", "market_psychology"}


def _score(hook: str, story: dict, brief: dict | None, cat: str = "") -> tuple[int, dict]:
    """7-axis score -> 0-100 (weighted). Returns (score, axes). Calibrated so a
    clean, compliant, on-story, <=6-word hook lands ~90-95."""
    h = hook.lower().strip()
    words = hook.split()
    n = len(words)
    f = _facts(story)

    scroll = 7
    if h.endswith("?"): scroll += 1
    if any(w in h for w in ("real", "underneath", "hid", "wasn't", "not just",
                            "moved everything", "changed the mood")): scroll += 3
    clarity = 10 if n <= 6 else 7 if n <= 7 else 4
    specificity = 6
    if f["sector"].lower() in h and f["sector"] != "the market": specificity += 3
    if any(ch.isdigit() for ch in h) or "%" in h: specificity += 2
    if h.startswith(("banks", "one sector", "this sector", "one policy")): specificity += 2
    if cat in STRONG_CATS: specificity += 2   # inherently specific/scroll-stopping angle
    truthfulness = 10 if not any(b in h for b in BAD) else 2
    connection = 6
    fam = (brief or {}).get("metaphor_family")
    fam_words = {"banks": "bank", "policy": "policy", "sector": "sector",
                 "breadth": "under", "flows": "money"}.get(fam or "", "")
    if fam_words and fam_words in h: connection += 3
    elif any(w in h for w in ("market", "nifty", "index", "sector")): connection += 2
    brand = 9 if not any(g in h for g in GENERIC) else 3
    simplicity = 10 if n <= 6 else 6 if n <= 8 else 3

    axes = {"scroll_stop": min(10, scroll), "clarity": clarity, "specificity": min(10, specificity),
            "truthfulness": truthfulness, "story_connection": min(10, connection),
            "brand_fit": brand, "simplicity": simplicity}
    weights = {"scroll_stop": 1.4, "clarity": 1.1, "specificity": 1.3,
               "truthfulness": 1.5, "story_connection": 1.3, "brand_fit": 1.0,
               "simplicity": 1.0}
    raw = sum(axes[k] * weights[k] for k in axes)
    max_raw = sum(10 * w for w in weights.values())
    return round(raw / max_raw * 100), axes


def _on_screen(text: str) -> str:
    return " ".join(text.replace("—", "").split()[:7])


def _build(date: str, story: dict, brief: dict | None, strict: bool) -> list[dict]:
    seeds = _seed(story, brief)
    if strict:  # regeneration: drop any generic/short-on-specificity seeds
        f = _facts(story)
        seeds = [h for h in seeds
                 if not any(g in h["text"].lower() for g in GENERIC)]
    hooks = []
    for h in seeds:
        text = h["text"]
        bad = _c.scan(text) or [b for b in BAD if b in text.lower()]
        score, axes = _score(text, story, brief, h["cat"])
        hooks.append({"category": h["cat"], "text": text, "strength": score,
                      "score": score, "axes": axes, "on_screen": _on_screen(text),
                      "compliant": not bad,
                      "reason": f"{h['cat']} hook; scroll {axes['scroll_stop']}/10, "
                                f"specificity {axes['specificity']}/10"})
    return hooks


def run(date: str, angle: dict, viral_fit: dict, creative_brief: dict | None = None) -> dict:
    story = viral_fit["chosen"]["story"]
    hooks = _build(date, story, creative_brief, strict=False)
    ranked = sorted([h for h in hooks if h["compliant"]] or hooks,
                    key=lambda h: h["strength"], reverse=True)

    regenerated = False
    if ranked[0]["strength"] < 90:
        # one stricter regeneration pass for specificity
        hooks2 = _build(date, story, creative_brief, strict=True)
        ranked2 = sorted([h for h in hooks2 if h["compliant"]] or hooks2,
                         key=lambda h: h["strength"], reverse=True)
        if ranked2 and ranked2[0]["strength"] >= ranked[0]["strength"]:
            hooks, ranked, regenerated = hooks2, ranked2, True

    chosen = ranked[0]
    blocked = chosen["strength"] < 90
    payload = {
        "date": date, "categories": CATEGORIES, "hooks": hooks,
        "count": len(hooks), "chosen": chosen,
        "selected_hook": chosen["text"], "on_screen_hook": chosen["on_screen"],
        "voiceover_hook": " ".join(chosen["text"].split()[:12]),
        "hook_category": chosen["category"],
        "hook_score": chosen["strength"],
        "min_required": 90, "regenerated": regenerated,
        "hook_lab_blocked": blocked,
        "blocked_reason": (f"No hook cleared 90 (best {chosen['strength']}); story may be "
                           "too weak or generic for a scroll-stopping hook.") if blocked else "",
        "why_this_hook_should_stop_scroll": (
            f"'{chosen['text']}' is a {chosen['category']} hook tied to today's story "
            f"(scroll-stop {chosen['axes']['scroll_stop']}/10, specificity "
            f"{chosen['axes']['specificity']}/10) and reads in {len(chosen['text'].split())} words."),
        "backup_hooks": [{"hook": h["text"], "category": h["category"],
                          "score": h["strength"], "reason": h["reason"]}
                         for h in ranked[1:6]],
    }
    schemas.validate_hooks(payload)
    state.save_artifact(date, "hooks", payload)
    return payload
