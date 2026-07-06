"""Agent 8 — Music Scout.

Suggests a mood + search terms for INSTAGRAM'S OWN licensed music library,
chosen during the manual Reel upload. Never downloads audio, never attaches
copyrighted tracks automatically.
"""
from __future__ import annotations

from . import config, state

_MOODS = [
    (("fall", "crash", "slump", "drop", "sell-off", "selloff", "decline"),
     {"mood": "tense minimal", "tempo": "slow-mid (80-100 BPM)",
      "search_terms": ["dark minimal beat", "tension instrumental",
                       "cinematic suspense", "news documentary beat"]}),
    (("rally", "surge", "record", "high", "jump", "gain", "soar"),
     {"mood": "confident upbeat", "tempo": "mid-up (100-120 BPM)",
      "search_terms": ["upbeat corporate", "confident instrumental",
                       "motivational beat", "success anthem instrumental"]}),
    (("rbi", "sebi", "policy", "budget", "rate", "inflation"),
     {"mood": "calm authoritative", "tempo": "mid (90-105 BPM)",
      "search_terms": ["calm corporate", "documentary underscore",
                       "focused instrumental", "newsroom background"]}),
]
_DEFAULT = {"mood": "premium editorial", "tempo": "mid (95-110 BPM)",
            "search_terms": ["premium corporate beat", "editorial instrumental",
                             "modern finance background", "clean tech beat"]}


def run(job_id: str) -> dict:
    sel = state.load_artifact(job_id, "story_selector") or {}
    text = (sel.get("selected_story", {}).get("headline", "")
            + " " + sel.get("selected_story", {}).get("summary", "")).lower()
    pick = next((m for kws, m in _MOODS if any(k in text for k in kws)), _DEFAULT)

    payload = {
        "music_source": "instagram_music_library",
        **pick,
        "note": "Choose licensed music inside Instagram during manual Reel upload.",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "music_scout", payload)
    return payload
