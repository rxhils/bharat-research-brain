"""Step 4 (upgraded) — Hook Lab.

Generates 15 hooks across 8 categories, scores each for scroll-stop strength,
and picks the winner. The hook must land in the first 0.3s: on-screen <= 8 words,
voiceover first line <= 12 words. No fake drama, no buy/sell, no clickbait the
video doesn't answer. Deterministic templates seed them; the conductor may refine.
"""
from __future__ import annotations

from . import compliance_util as _c
from . import schemas, state

CATEGORIES = ["question", "curiosity", "data", "contrarian", "direct",
              "hidden_reason", "you_missed_this", "market_psychology"]

# banned in hooks even beyond the compliance list (no hype/clickbait)
BAD = ["explode", "crash tomorrow", "guaranteed", "will make you rich", "must buy"]


def _seed(story: dict, angle: str) -> list[dict]:
    sector = (story.get("affected_sectors") or ["the market"])[0].split("/")[0].strip()
    nums = story.get("key_numbers") or []
    pct = next((n for n in nums if "%" in n), None)
    big = pct or "one number"
    s = sector.lower()
    return [
        {"cat": "question", "text": f"Why did {s} really move today?"},
        {"cat": "question", "text": "Nifty moved. But why?"},
        {"cat": "curiosity", "text": "Everyone watched Nifty. This is what they missed."},
        {"cat": "curiosity", "text": "The market looked calm. It wasn't."},
        {"cat": "data", "text": f"{big} moved the whole market today."},
        {"cat": "data", "text": f"{s.title()} did most of the damage today."},
        {"cat": "contrarian", "text": f"{sector} moving is not the real story."},
        {"cat": "contrarian", "text": "A red index isn't always bad news."},
        {"cat": "direct", "text": f"Here's why {s} moved today."},
        {"cat": "direct", "text": "Today's market, in 15 seconds."},
        {"cat": "hidden_reason", "text": "One reason moved everything today."},
        {"cat": "hidden_reason", "text": "The real driver wasn't the index."},
        {"cat": "you_missed_this", "text": "Here's what investors missed today."},
        {"cat": "you_missed_this", "text": "Don't just watch Nifty."},
        {"cat": "market_psychology", "text": "The market's mood changed today. Here's why."},
    ]


def _strength(hook: str) -> int:
    h = hook.lower()
    score = 60
    if h.endswith("?"): score += 12
    if any(w in h for w in ("missed", "real story", "real driver", "wasn't", "not the")): score += 14
    if any(ch.isdigit() for ch in h) or "%" in h: score += 8
    words = len(hook.split())
    if words <= 6: score += 10
    elif words <= 8: score += 5
    if h.startswith(("here's", "why", "everyone", "don't")): score += 4
    return min(100, score)


def _on_screen(text: str) -> str:
    return " ".join(text.replace("—", "").split()[:8])


def run(date: str, angle: dict, viral_fit: dict) -> dict:
    story = viral_fit["chosen"]["story"]
    seeds = _seed(story, angle["chosen"]["angle"])
    hooks = []
    for h in seeds:
        text = h["text"]
        bad = _c.scan(text) or [b for b in BAD if b in text.lower()]
        hooks.append({"category": h["cat"], "text": text, "strength": _strength(text),
                      "on_screen": _on_screen(text), "compliant": not bad})
    ranked = sorted([h for h in hooks if h["compliant"]] or hooks,
                    key=lambda h: h["strength"], reverse=True)
    chosen = ranked[0]
    payload = {
        "date": date, "categories": CATEGORIES, "hooks": hooks,
        "count": len(hooks), "chosen": chosen,
        "selected_hook": chosen["text"], "on_screen_hook": chosen["on_screen"],
        "voiceover_hook": " ".join(chosen["text"].split()[:12]),
        "hook_score": chosen["strength"],
        "backup_hooks": [h["text"] for h in ranked[1:5]],
    }
    schemas.validate_hooks(payload)
    state.save_artifact(date, "hooks", payload)
    return payload
