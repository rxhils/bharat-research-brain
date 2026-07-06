"""Claude Video watch agents — visual perception layer (no Higgsfield).

watch_source(): inspects a ranked episode using yt-dlp metadata + caption
availability (no full download) and scores short-form potential.
watch_local(): ffprobe + blackdetect on a local file; reused by the candidate
watch (Phase 7) and final render watch (Phase 9).

Reports persist to reels_video_watch_reports and E:\\MavenReels\\watch-reports.
The notes_json structure is Claude-readable so a vision pass can enrich it.
"""
from __future__ import annotations

import json
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq
from .newsroom_reels_storage import STORAGE_ROOT, guard_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_report(subject_type: str, subject_id: str, score: int,
                 notes: dict, passed: bool, run_id: str | None) -> dict:
    report_id = f"watch-{uuid.uuid4().hex[:8]}"
    path = guard_path(STORAGE_ROOT / "watch-reports" / f"{report_id}.json")
    Path(path).write_text(json.dumps(
        {"report_id": report_id, "subject_type": subject_type,
         "subject_id": subject_id, "watch_score": score, "passed": passed,
         "notes": notes}, ensure_ascii=False, indent=1), encoding="utf-8")
    rdb.upsert("reels_video_watch_reports", {
        "report_id": report_id, "subject_type": subject_type,
        "subject_id": subject_id, "watch_score": score,
        "notes_json": json.dumps(notes, ensure_ascii=False),
        "passed": int(passed), "report_path": str(path), "created_at": _now(),
    }, ["report_id"])
    rq.log(run_id, "video_watch", f"reels.video.watch_{subject_type}",
           f"{subject_id}: score {score} passed={passed}")
    return {"report_id": report_id, "watch_score": score, "passed": passed,
            "notes": notes}


def fetch_video_meta(url: str) -> dict:
    out = subprocess.run(
        ["python", "-m", "yt_dlp", url, "--dump-json", "--skip-download",
         "--no-warnings"], capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout.splitlines()[0]) if out.stdout.strip() else {}


def watch_source(episode_id: str) -> dict:
    """Score an episode's short-form potential from real metadata."""
    ep = rdb.query_one("SELECT * FROM reels_episodes WHERE episode_id=?", (episode_id,))
    if not ep:
        raise ValueError(f"unknown episode {episode_id}")
    meta = fetch_video_meta(ep["url"])
    height = meta.get("height") or 0
    fps = meta.get("fps") or 0
    has_subs = bool(meta.get("subtitles") or meta.get("automatic_captions"))
    duration = meta.get("duration") or ep["duration_sec"] or 0
    chapters = len(meta.get("chapters") or [])

    notes = {
        "resolution": f"{meta.get('width', '?')}x{height}", "fps": fps,
        "captions_available": has_subs, "duration_sec": duration,
        "chapters": chapters, "channel": meta.get("channel"),
        "speaker_framing": "unknown — needs vision pass",
        "charts_or_slides": "unknown — needs vision pass",
    }
    score = 0
    score += 35 if height >= 1080 else 25 if height >= 720 else 10
    score += 15 if fps >= 25 else 5
    score += 20 if has_subs else 0
    score += 20 if 600 <= duration <= 7200 else 5   # podcast-length sweet spot
    score += 10 if chapters else 0
    passed = score >= 60 and height >= 720
    return _save_report("source", episode_id, score, notes, passed, ep["run_id"])


_BLACK_RE = re.compile(r"black_start:(?P<s>[\d.]+).*?black_duration:(?P<d>[\d.]+)")


def _parse_fps(rate: str | None) -> float:
    """ffprobe avg_frame_rate like '30000/1001' -> 30.0."""
    try:
        num, _, den = str(rate or "0/1").partition("/")
        return round(float(num) / max(1.0, float(den or 1)), 1)
    except ValueError:
        return 0.0


def watch_local(path: str | Path, subject_type: str, subject_id: str,
                run_id: str | None = None) -> dict:
    """ffprobe + blackdetect QA for a local clip/render on E:."""
    p = guard_path(path)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
         "-show_format", str(p)], capture_output=True, text=True, timeout=60)
    info = json.loads(probe.stdout or "{}")
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(info.get("format", {}).get("duration") or 0)

    black = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(p), "-vf", "blackdetect=d=0.5",
         "-an", "-f", "null", "-"], capture_output=True, text=True, timeout=300)
    black_total = sum(float(m.group("d"))
                     for m in _BLACK_RE.finditer(black.stderr.replace("\n", " ")))

    notes = {
        "resolution": f"{v.get('width', 0)}x{v.get('height', 0)}",
        "fps": _parse_fps(v.get("avg_frame_rate")),
        "has_audio": a is not None, "duration_sec": round(duration, 2),
        "black_seconds": round(black_total, 2),
    }
    score = 0
    score += 30 if (v.get("height") or 0) >= 720 else 10
    score += 25 if a is not None else 0
    score += 25 if black_total < 0.5 else 5 if black_total < 2 else 0
    score += 20 if duration > 1 else 0
    passed = score >= 70 and a is not None and black_total < 2
    return _save_report(subject_type, subject_id, score, notes, passed, run_id)


async def _handle_watch_source(job: dict) -> None:
    watch_source(job["subject_id"])


rq.register("reels.video.watch_source", _handle_watch_source)
