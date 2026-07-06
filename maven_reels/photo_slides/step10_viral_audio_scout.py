"""Agent — Viral Audio Scout.

Finds the song to attach to the Reel: what is trending RIGHT NOW on
Instagram/TikTok in the finance/business niche, matched to the story's mood.

Sources, in order of trust:
1. Curated registry (viral_audio_registry.json) — refreshed from Instagram's
   own Trending tab + tokchart/heyorca/scottsocial weekly lists; every entry
   carries `last_verified` and trends are treated as stale after 10 days.
2. Best-effort LIVE scrape of tokchart.com (daily TikTok top songs, no key).
   Failure is reported honestly — never fabricated chart positions.

Compliance is explicit: copyrighted trending tracks are NEVER baked into
API-published MP4s. The pick is applied by tapping the track inside
Instagram's audio picker during the native photo-Reel upload (that is also
what makes the reel ride the trend's distribution).
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, datetime
from pathlib import Path

from . import config, state

REGISTRY_PATH = Path(__file__).resolve().parent / "viral_audio_registry.json"
STALE_DAYS = 10                       # research: trends live ~7-10 days

_MOOD_MAP = [   # story keywords -> wanted moods (first match wins)
    (("crash", "fall", "slump", "drop", "sell-off", "selloff", "plunge"),
     ["intense", "hype"]),
    (("rally", "surge", "record", "all-time", "jump", "soar", "high"),
     ["hype", "upbeat"]),
    (("grows", "growth", "profit", "revenue", "expands", "wins", "gain"),
     ["confident", "upbeat"]),
    (("rbi", "sebi", "policy", "rate", "budget", "regulation"),
     ["confident", "explainer"]),
]
_DEFAULT_MOODS = ["explainer", "confident", "upbeat"]


def _story_moods(story: dict) -> list[str]:
    text = f"{story.get('headline', '')} {story.get('summary', '')}".lower()
    for kws, moods in _MOOD_MAP:
        if any(k in text for k in kws):
            return moods
    return _DEFAULT_MOODS


def _age_days(iso: str) -> int:
    try:
        return (date.today() - datetime.fromisoformat(iso).date()).days
    except ValueError:
        return 999


def _load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"tracks": [], "last_refreshed": None, "refresh_sources": []}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"tracks": [], "last_refreshed": None, "refresh_sources": []}


def _live_tokchart(limit: int = 10) -> tuple[list[dict], str]:
    """Best-effort daily TikTok chart scrape; honest failure note."""
    try:
        req = urllib.request.Request(
            "https://tokchart.com/",
            headers={"User-Agent": "Mozilla/5.0 (MavenNewsroom research; "
                                   "personal educational use)"})
        html = urllib.request.urlopen(req, timeout=10).read().decode(
            "utf-8", "ignore")
        # song links look like /songs/<slug>; titles in the anchor text
        names = re.findall(
            r'href="https?://tokchart\.com/songs/[^"]+"[^>]*>([^<]{3,80})<',
            html)
        seen, out = set(), []
        for n in names:
            t = re.sub(r"\s+", " ", n).strip()
            if t and t.lower() not in seen and not t.lower().startswith("view"):
                seen.add(t.lower())
                out.append({"title": t, "platform": "tiktok",
                            "source": "tokchart_live"})
            if len(out) >= limit:
                break
        if out:
            return out, "live"
        return [], "tokchart reachable but no songs parsed (markup changed?)"
    except Exception as exc:  # network/timeout — report, don't fake
        return [], f"tokchart unreachable: {exc}"


def _score(track: dict, wanted: list[str]) -> int:
    score = 50
    mood_hits = len(set(track.get("moods", [])) & set(wanted))
    score += mood_hits * 18
    if "finance-explainer" in track.get("niche_fit", []) \
            or "business" in track.get("niche_fit", []):
        score += 12
    if track.get("business_safe"):
        score += 8                     # usable on a business/brand account
    age = _age_days(track.get("last_verified", ""))
    if age > STALE_DAYS:
        score -= min(30, (age - STALE_DAYS) * 3)
    return max(score, 0)


def run(job_id: str) -> dict:
    sel = state.load_artifact(job_id, "story_selector") or {}
    story = sel.get("selected_story") or {}
    wanted = _story_moods(story)

    registry = _load_registry()
    tracks = registry.get("tracks", [])
    live, live_status = _live_tokchart()

    ranked = sorted(tracks, key=lambda t: _score(t, wanted), reverse=True)
    picks = []
    for t in ranked[:3]:
        age = _age_days(t.get("last_verified", ""))
        picks.append({
            "title": t["title"], "artist": t.get("artist", ""),
            "platform": t.get("platform", ""),
            "why": t.get("trend_use", ""),
            "match_score": _score(t, wanted),
            "business_safe": t.get("business_safe", False),
            "freshness": ("fresh" if age <= STALE_DAYS
                          else f"STALE — verified {age} days ago, re-check the "
                               "Trending tab before using"),
            "how_to_use": (f"Instagram → create Reel → add audio → search "
                           f"\"{t['title']}\" (or the Trending tab) and tap it."),
        })

    stale = _age_days(registry.get("last_refreshed") or "")
    payload = {
        "story_moods": wanted,
        "picks": picks,
        "primary_pick": picks[0] if picks else None,
        "live_tiktok_top": live[:10],
        "live_status": live_status if not live else "live",
        "registry_last_refreshed": registry.get("last_refreshed"),
        "registry_stale": stale > STALE_DAYS,
        "refresh_sources": registry.get("refresh_sources", []),
        "compliance_note": ("Trending tracks are tapped inside Instagram during "
                            "the manual native photo-Reel upload. They are NEVER "
                            "baked into API-published MP4s (copyright + account "
                            "risk); auto mode keeps original audio only."),
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "viral_audio", payload)
    return payload
