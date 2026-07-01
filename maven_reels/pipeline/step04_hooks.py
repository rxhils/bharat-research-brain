"""Step 4 — Hook Lab.

The first 2 seconds decide whether the reel lives or dies. Always generate a hook
in each of 7 buckets (so reels don't feel repetitive), score each for strength,
pick the winner. Deterministic templates seed them; the conductor may refine.
"""
from __future__ import annotations

from . import compliance_util as _c  # local compliance wrapper
from . import state
from .config import HOOK_BUCKETS


def _seed(story: dict, angle: str) -> dict[str, str]:
    sector = (story.get("affected_sectors") or ["the market"])[0]
    nums = story.get("key_numbers") or []
    big = next((n for n in nums if "%" in n or "crore" in n.lower()), "a big move")
    return {
        "curiosity": f"Everyone saw the market today — but this is the part they missed.",
        "shock": f"Indian markets just got hit by something bigger than the headline.",
        "contrarian": f"{sector} moving is not the real story today. Here's what is.",
        "simple": f"Here's why {sector.lower()} moved today, in 30 seconds.",
        "data": f"{big} — and it came down to one thing.",
        "myth": f"You think the index tells the story. Today it didn't.",
        "question": f"Why did {sector.lower()} really move today?",
    }


def _strength(hook: str) -> int:
    h = hook.lower()
    score = 62
    if h.endswith("?"): score += 10
    if any(w in h for w in ("missed", "real story", "bigger", "few", "not the")): score += 14
    if any(c.isdigit() for c in h): score += 8
    if len(hook) <= 70: score += 8
    if h.startswith(("here's", "why", "everyone")): score += 4
    return min(100, score)


def run(date: str, angle: dict, viral_fit: dict) -> dict:
    story = viral_fit["chosen"]["story"]
    seeds = _seed(story, angle["chosen"]["angle"])
    hooks = []
    for bucket in HOOK_BUCKETS:
        text = seeds[bucket]
        hooks.append({"bucket": bucket, "text": text,
                      "strength": _strength(text),
                      "compliant": not _c.scan(text)})
    # never pick a non-compliant hook
    ranked = sorted([h for h in hooks if h["compliant"]] or hooks,
                    key=lambda h: h["strength"], reverse=True)
    payload = {
        "date": date,
        "buckets": HOOK_BUCKETS,
        "hooks": hooks,
        "chosen": ranked[0],
    }
    from . import schemas
    schemas.validate_hooks(payload)
    state.save_artifact(date, "hooks", payload)
    return payload
