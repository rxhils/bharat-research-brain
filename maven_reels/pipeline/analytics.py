"""Signal Tracker — reel-specific analytics + learning rollups.

The winning signal for reels is not likes — it's watched-past-3s + rewatch +
share/save. Metrics are pulled post-publish via Composio IG insights (in the
conductor); this defines the schema and the learning rollups.
"""
from __future__ import annotations

from . import state

REEL_METRICS = [
    "reach", "impressions", "plays", "avg_watch_time_s", "three_second_retention",
    "replay_rate", "saves", "shares", "comments", "likes", "follows_gained",
    "profile_visits",
]
LEARNING_DIMS = ["hook_bucket", "video_length_s", "scene_count", "has_voiceover",
                 "visual_style", "topic_category"]


def record(date: str, metrics: dict, context: dict) -> dict:
    """Store a published reel's metrics + its context for learning."""
    payload = {"date": date,
               "metrics": {k: metrics.get(k) for k in REEL_METRICS},
               "context": {k: context.get(k) for k in LEARNING_DIMS},
               "north_star": {
                   "watched_past_3s": metrics.get("three_second_retention"),
                   "rewatch": metrics.get("replay_rate"),
                   "save_share": (metrics.get("saves") or 0) + (metrics.get("shares") or 0),
               }}
    state.save_artifact(date, "final", {**(state.load_artifact(date, "final")
                                           if state.artifact_exists(date, "final") else {}),
                                        "analytics": payload})
    return payload


def learnings(rows: list[dict]) -> list[str]:
    """Very small rollup: which hook buckets / lengths correlate with saves+shares."""
    out = []
    by_bucket: dict[str, list[int]] = {}
    for r in rows:
        b = r.get("context", {}).get("hook_bucket")
        ss = r.get("north_star", {}).get("save_share") or 0
        if b:
            by_bucket.setdefault(b, []).append(ss)
    for b, vals in sorted(by_bucket.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        out.append(f"{b} hooks: avg {sum(vals)/len(vals):.0f} saves+shares over {len(vals)} reels")
    return out
