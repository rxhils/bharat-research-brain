"""Phase 7 agents: Clip Planner, FFmpeg Clip Builder, Candidate Watch.

Clip Planner picks the top 5 clips per episode by weighted final_clip_score
(>= 85 gate). FFmpeg Clip Builder cuts raw clips deterministically — the exact
command is stored so every clip is reproducible — onto E:\\MavenReels.
Candidate Watch reuses the local ffprobe/blackdetect watcher before any
render time is spent.
"""
from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import newsroom_reels_db as rdb
from ..newsroom_reels_config import STORAGE_ROOT
from . import newsroom_reels_queue as rq
from .newsroom_reels_storage import guard_path, run_subdir
from .newsroom_reels_watch import watch_local

CLIPS_PER_EPISODE = 5
FINAL_SCORE_GATE = 85.0


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ------------------------------------------------- Agent 15: Clip Planner

def _uniqueness(text: str, chosen_texts: list[str]) -> int:
    """100 = novel vs already-chosen clips; Jaccard word overlap penalty."""
    words = set((text or "").lower().split())
    if not words:
        return 0
    worst = 0.0
    for other in chosen_texts:
        ow = set(other.lower().split())
        if ow:
            worst = max(worst, len(words & ow) / len(words | ow))
    return round(100 * (1 - worst))


def final_clip_score(s: dict[str, Any], video_perception: int, source_score: int,
                     uniqueness: int) -> float:
    compliance_safety = 100 - (s["compliance_risk_score"] or 0)
    return round(
        (s["indian_relevance_score"] or 0) * .25 +
        (s["virality_score"] or 0) * .20 +
        compliance_safety * .15 +
        (s["context_safety_score"] or 0) * .10 +
        video_perception * .15 +
        source_score * .05 +
        uniqueness * .10, 2)


def plan_clips(run_id: str, episode_id: str) -> list[dict[str, Any]]:
    """Select the top clips (max 5) for one episode; only gate-passed segments."""
    ep = rdb.query_one(
        "SELECT e.*, s.source_score FROM reels_episodes e "
        "LEFT JOIN reels_sources s ON s.source_id = e.source_id "
        "WHERE e.episode_id=?", (episode_id,))
    if not ep:
        raise ValueError(f"unknown episode {episode_id}")
    watch = rdb.query_one(
        "SELECT watch_score FROM reels_video_watch_reports "
        "WHERE subject_type='source' AND subject_id=? ORDER BY created_at DESC",
        (episode_id,))
    video_perception = watch["watch_score"] if watch else 50

    rows = rdb.query_all(
        "SELECT g.*, s.* FROM reels_segments g "
        "JOIN reels_segment_scores s ON s.segment_id = g.segment_id "
        "WHERE g.episode_id=? AND s.passed=1 "
        "AND g.segment_id NOT IN (SELECT segment_id FROM reels_clip_candidates)",
        (episode_id,))

    # cross-run dedup: discovery mints new segment ids each run, so exclude
    # any moment overlapping a clip already planned for this episode
    def _sec(ts: str) -> float:
        h, m, s = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    taken = [( _sec(c["start_ts"]), _sec(c["end_ts"]) ) for c in rdb.query_all(
        "SELECT start_ts, end_ts FROM reels_clip_candidates WHERE episode_id=?",
        (episode_id,))]

    planned: list[dict[str, Any]] = []
    chosen_texts: list[str] = []
    # greedy: best-scoring first, uniqueness re-computed against already chosen
    remaining = sorted(rows, key=lambda r: (r["virality_score"] or 0), reverse=True)
    for r in remaining:
        if len(planned) >= CLIPS_PER_EPISODE:
            break
        a, b = _sec(r["start_ts"]), _sec(r["end_ts"])
        if any(a < tb + 5 and b > ta - 5 for ta, tb in taken):
            continue                     # overlaps an already-clipped moment
        uniq = _uniqueness(r["text"], chosen_texts)
        score = final_clip_score(r, video_perception, ep["source_score"] or 0, uniq)
        if score < FINAL_SCORE_GATE:
            continue
        clip_id = f"clip-{uuid.uuid4().hex[:10]}"
        rdb.upsert("reels_clip_candidates", {
            "clip_id": clip_id, "segment_id": r["segment_id"],
            "episode_id": episode_id, "run_id": run_id,
            "rank_in_episode": len(planned) + 1,
            "start_ts": r["start_ts"], "end_ts": r["end_ts"],
            "status": "planned", "created_at": _now(),
        }, ["clip_id"])
        with rdb.connect() as c:
            c.execute("UPDATE reels_segment_scores SET uniqueness_score=?, "
                      "final_clip_score=? WHERE segment_id=?",
                      (uniq, score, r["segment_id"]))
        chosen_texts.append(r["text"])
        planned.append({"clip_id": clip_id, "final_clip_score": score,
                        "start_ts": r["start_ts"], "end_ts": r["end_ts"]})
    rq.log(run_id, "clip_planner", "reels.clip.plan",
           f"{episode_id}: {len(planned)}/{CLIPS_PER_EPISODE} clips >= {FINAL_SCORE_GATE}")
    return planned


# ------------------------------------------------- Agent 16: FFmpeg Clip Builder

def download_source_video(episode_id: str) -> Path:
    """Fetch the episode video once (<=1080p) to E:; reused by all its clips."""
    ep = rdb.query_one("SELECT * FROM reels_episodes WHERE episode_id=?", (episode_id,))
    if not ep:
        raise ValueError(f"unknown episode {episode_id}")
    out = guard_path(STORAGE_ROOT / "source-videos" / f"{episode_id}.mp4")
    if Path(out).exists():
        return Path(out)
    cmd = ["python", "-m", "yt_dlp", ep["url"], "-f",
           "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
           "--merge-output-format", "mp4", "--no-warnings", "-o", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if not Path(out).exists():
        raise RuntimeError(f"source download failed for {episode_id}: {res.stderr[-300:]}")
    with rdb.connect() as c:
        c.execute("UPDATE reels_episodes SET video_path=? WHERE episode_id=?",
                  (str(out), episode_id))
    return Path(out)


def build_clip(clip_id: str, run_date: str) -> dict[str, str]:
    """Deterministically cut one raw clip; never overwrites; command recorded."""
    clip = rdb.query_one("SELECT * FROM reels_clip_candidates WHERE clip_id=?", (clip_id,))
    if not clip:
        raise ValueError(f"unknown clip {clip_id}")
    ep = rdb.query_one("SELECT * FROM reels_episodes WHERE episode_id=?",
                       (clip["episode_id"],))
    src = (ep or {}).get("video_path") or str(download_source_video(clip["episode_id"]))

    out_dir = run_subdir(run_date, "candidate-clips")
    out = guard_path(Path(out_dir) / f"{clip_id}.mp4")
    if Path(out).exists():
        raise FileExistsError(f"refusing to overwrite existing clip: {out}")

    # re-encode (not -c copy) so cuts are frame-accurate at sentence boundaries
    cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", clip["start_ts"],
           "-to", clip["end_ts"], "-i", str(src),
           "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0 or not Path(out).exists():
        raise RuntimeError(f"ffmpeg cut failed for {clip_id}: {res.stderr[-300:]}")

    with rdb.connect() as c:
        c.execute("UPDATE reels_clip_candidates SET clip_path=?, ffmpeg_command=?, "
                  "status='built' WHERE clip_id=?",
                  (str(out), " ".join(cmd), clip_id))
    rq.log(clip["run_id"], "ffmpeg_builder", "reels.clip.build", f"built {clip_id}")
    return {"clip_id": clip_id, "clip_path": str(out), "ffmpeg_command": " ".join(cmd)}


# ------------------------------------------------- Agent 17: Candidate Watch

def watch_candidate(clip_id: str) -> dict[str, Any]:
    clip = rdb.query_one("SELECT * FROM reels_clip_candidates WHERE clip_id=?", (clip_id,))
    if not clip or not clip["clip_path"]:
        raise ValueError(f"clip {clip_id} not built yet")
    rep = watch_local(clip["clip_path"], "candidate", clip_id, clip["run_id"])
    new_status = "watched" if rep["passed"] else "rejected"
    with rdb.connect() as c:
        c.execute("UPDATE reels_clip_candidates SET status=? WHERE clip_id=?",
                  (new_status, clip_id))
    return rep


# ------------------------------------------------- queue handlers

async def _handle_clip_plan(job: dict[str, Any]) -> None:
    planned = plan_clips(job["run_id"], job["subject_id"])
    for p in planned:
        rq.enqueue("reels.clip.build", run_id=job["run_id"], subject_id=p["clip_id"])


async def _handle_clip_build(job: dict[str, Any]) -> None:
    run = rdb.query_one("SELECT run_date FROM reels_daily_runs WHERE run_id=?",
                        (job["run_id"],))
    build_clip(job["subject_id"], run["run_date"] if run else _now()[:10])
    rq.enqueue("reels.video.watch_candidate", run_id=job["run_id"],
               subject_id=job["subject_id"])


async def _handle_watch_candidate(job: dict[str, Any]) -> None:
    rep = watch_candidate(job["subject_id"])
    if rep["passed"]:
        rq.enqueue("reels.hook.write", run_id=job["run_id"], subject_id=job["subject_id"])


rq.register("reels.clip.plan", _handle_clip_plan)
rq.register("reels.clip.build", _handle_clip_build)
rq.register("reels.video.watch_candidate", _handle_watch_candidate)
