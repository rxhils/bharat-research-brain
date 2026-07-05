"""Agent — Hook Lab (format-aware, Maven Reels Newsroom). Local, free.

Chunk 3 rewrite: 25 hooks across Indian-finance hook BUCKETS, tuned to the
selected format. Stricter than the legacy lab — reject-list is a hard fail,
minimum accepted score is 92 (not 90), scored on Indian-finance-hook axes:
  specificity 25 / first-frame clarity 20 / curiosity 20 / truthfulness 15 /
  save-share 10 / visual potential 10.
Reads format_director + story_format. Writes 38_hooks_format.json.
Educational only — no buy/sell, no hype, no clickbait the reel can't answer.
"""
from __future__ import annotations

from . import state
from .step_viral_reference_bank import reject_hooks

MIN_SCORE = 92

# Indian-finance hook buckets → seed templates ({s}=sector, {h}=headline hint)
_BUCKETS = {
    "contrarian": ["{s} wasn't the real story.", "Don't just watch the index.",
                   "The headline wasn't the full story."],
    "hidden_cause": ["One sector moved everything.", "The real move was underneath.",
                     "This is what moved underneath."],
    "beginner_clarity": ["Don't just watch the index.", "Why did {s} really move?",
                         "New to markets? Read this move."],
    "market_map": ["This is what moved underneath.", "Here's the map of today's move.",
                   "One layer explains the whole day."],
    "policy_signal": ["One signal moved stocks.", "One policy shift moved the market.",
                      "A single signal rippled out."],
    "retail_mistake": ["Most investors read this wrong.", "Most people misread {s}.",
                       "Here's the mistake to avoid."],
    "saveable_lesson": ["Remember this during market moves.", "Keep this for the next rally.",
                        "The index is the result, not the reason."],
    "risk_warning": ["Don't follow this blindly.", "Here's how investors get trapped.",
                     "This is the trap to watch."],
}

# format → preferred buckets (front-loaded)
_FORMAT_BUCKETS = {
    "hidden_mechanism": ["contrarian", "hidden_cause", "market_map", "saveable_lesson"],
    "one_sector": ["hidden_cause", "contrarian", "market_map", "beginner_clarity"],
    "policy_signal": ["policy_signal", "hidden_cause", "market_map", "saveable_lesson"],
    "retail_mistake": ["retail_mistake", "beginner_clarity", "saveable_lesson", "contrarian"],
    "market_myth": ["contrarian", "market_map", "saveable_lesson", "hidden_cause"],
    "risk_explainer": ["risk_warning", "retail_mistake", "saveable_lesson", "beginner_clarity"],
}

_HYPE = ["explode", "crash coming", "crash tomorrow", "guaranteed", "will make you rich",
         "must buy", "before it's too late", "watch before tomorrow", "double your money"]


def _fill(t: str, sector: str, headline: str) -> str:
    return t.replace("{s}", sector or "the market").replace("{h}", headline or "the market")


def _score(hook: str, sector: str, bucket: str) -> tuple[int, dict]:
    h = hook.lower().strip()
    words = hook.split(); n = len(words)
    rejects = [r.lower() for r in reject_hooks()]

    specificity = 12
    if sector and sector.lower() in h and sector.lower() != "the market": specificity += 8
    if any(c.isdigit() for c in h): specificity += 5
    specificity = min(25, specificity)
    first_frame = 20 if n <= 6 else 14 if n <= 8 else 7
    curiosity = 20 if any(w in h for w in ("wasn't", "underneath", "real", "hid", "map",
                          "mistake", "wrong", "trap", "signal", "remember")) else 12
    truthfulness = 0 if any(b in h for b in _HYPE) else 15
    save_share = 10 if bucket in ("saveable_lesson", "retail_mistake", "risk_warning",
                                  "hidden_cause") else 6
    visual = 10 if n <= 7 else 6
    axes = {"specificity": specificity, "first_frame_clarity": first_frame,
            "curiosity": curiosity, "truthfulness": truthfulness,
            "save_share": save_share, "visual_potential": visual}
    total = sum(axes.values())
    if h.rstrip(".?!") in rejects:                    # reject-list = hard fail
        total = min(total, 30); axes["rejected"] = True
    return total, axes


def _on_screen(text: str) -> str:
    return " ".join(text.replace("—", "").split()[:7])


def run(date: str) -> dict:
    fd = _opt(date, "format_director") or {}
    sf = _opt(date, "story_format") or {}
    fid = fd.get("format") or sf.get("selected_format", "hidden_mechanism")
    story = sf.get("selected_story", {})
    sector = (story.get("sector") or "the market").split("/")[0].strip()
    headline = story.get("headline", "")

    order = _FORMAT_BUCKETS.get(fid, list(_BUCKETS)) + [b for b in _BUCKETS
                                                        if b not in _FORMAT_BUCKETS.get(fid, [])]
    hooks, seen = [], set()
    for bucket in order:
        for tmpl in _BUCKETS[bucket]:
            text = _fill(tmpl, sector, headline)
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            score, axes = _score(text, sector, bucket)
            hooks.append({"bucket": bucket, "text": text, "score": score, "axes": axes,
                          "on_screen": _on_screen(text), "rejected": axes.get("rejected", False)})
            if len(hooks) >= 25:
                break
        if len(hooks) >= 25:
            break

    ranked = sorted(hooks, key=lambda h: h["score"], reverse=True)
    chosen = ranked[0]
    blocked = chosen["score"] < MIN_SCORE
    payload = {
        "date": date, "format": fid, "buckets": list(_BUCKETS),
        "hooks": hooks, "count": len(hooks),
        "chosen": chosen, "selected_hook": chosen["text"],
        "on_screen_hook": chosen["on_screen"],
        "voiceover_hook": " ".join(chosen["text"].split()[:12]),
        "hook_bucket": chosen["bucket"], "hook_score": chosen["score"],
        "min_required": MIN_SCORE, "hook_lab_blocked": blocked,
        "blocked_reason": (f"No hook cleared {MIN_SCORE} (best {chosen['score']}); story may be "
                           "too generic for a scroll-stopping, saveable hook.") if blocked else "",
        "reject_list": reject_hooks(),
        "backup_hooks": [{"hook": h["text"], "bucket": h["bucket"], "score": h["score"]}
                         for h in ranked[1:6]],
    }
    state.save_artifact(date, "hooks_format", payload)
    return payload


def _opt(date: str, key: str):
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None
