"""Transcript Agent — timestamped transcripts for ranked episodes.

Priority: official YouTube captions -> auto captions -> WhisperX fallback.
WhisperX is optional; if it is not installed the agent fails loud (recorded in
reels_agent_logs) instead of fabricating text. Transcript JSON lives on
E:\\MavenReels\\transcripts; cue rows are the raw material for Segment
Discovery (Phase 6).
"""
from __future__ import annotations

import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq
from .newsroom_reels_storage import STORAGE_ROOT, guard_path


class TranscriptUnavailable(Exception):
    """No captions and no working fallback — the episode is skipped, not faked."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _fmt_ts(seconds: float) -> str:
    """Millisecond-precise HH:MM:SS.mmm — ffmpeg cut points must match the
    caption timeline exactly, or subtitles drift off the voice."""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def parse_json3(raw: dict) -> list[dict]:
    """YouTube json3 caption events -> [{start_sec, end_sec, text, words}].

    Auto-captions carry per-word tOffsetMs — kept as word timings so subtitle
    events can follow the actual voice. Official captions (one seg per event)
    fall back to evenly spaced words within the cue.
    """
    cues = []
    for ev in raw.get("events", []):
        segs = ev.get("segs") or []
        text = "".join(s.get("utf8", "") for s in segs).strip()
        if not text or text == "\n":
            continue
        start = (ev.get("tStartMs") or 0) / 1000
        dur = (ev.get("dDurationMs") or 0) / 1000
        words: list[dict] = []
        timed = [s for s in segs if s.get("utf8", "").strip()]
        has_offsets = sum(1 for s in timed if "tOffsetMs" in s) >= max(1, len(timed) // 2)
        if has_offsets:
            for s in timed:
                for w in s.get("utf8", "").split():
                    words.append({"t": round(start + (s.get("tOffsetMs") or 0) / 1000, 3),
                                  "w": w})
        else:
            toks = text.split()
            step = dur / max(1, len(toks))
            words = [{"t": round(start + i * step, 3), "w": w}
                     for i, w in enumerate(toks)]
        cues.append({"start_sec": round(start, 3),
                     "end_sec": round(start + dur, 3), "text": text,
                     "words": words})
    return cues


def fetch_youtube_captions(url: str, workdir: Path) -> tuple[list[dict], str]:
    """Download official-first (then auto) captions as json3. No video download.

    YouTube 429-throttles the caption endpoint during batch fetches — retry
    with backoff before declaring captions unavailable.
    """
    import time
    workdir.mkdir(parents=True, exist_ok=True)
    base = workdir / "captions"
    cmd = ["python", "-m", "yt_dlp", url, "--skip-download",
           "--write-subs", "--write-auto-subs", "--sub-langs", "en.*,en,hi",
           "--sub-format", "json3", "--no-warnings", "-o", str(base)]
    stderr_tail = ""
    for attempt, backoff in enumerate((0, 30, 75)):
        if backoff:
            time.sleep(backoff)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        files = sorted(workdir.glob("captions*.json3"))
        if files:
            break
        stderr_tail = (res.stderr or "")[-200:]
        if "429" not in stderr_tail and attempt > 0:
            break                     # not throttling — retrying won't help
    files = sorted(workdir.glob("captions*.json3"))
    if not files:
        raise TranscriptUnavailable(
            f"no captions available for {url} (last error: {stderr_tail})")
    # yt-dlp names official subs before auto ('en' vs 'en-orig' ordering varies);
    # any json3 here is real caption data — take the first.
    raw = json.loads(files[0].read_text(encoding="utf-8"))
    method = "auto_captions" if "orig" in files[0].name else "youtube_captions"
    return parse_json3(raw), method


def whisperx_transcribe(url: str) -> tuple[list[dict], str]:
    """WhisperX fallback. Optional dependency — loud failure when missing."""
    try:
        import whisperx  # noqa: F401
    except ImportError as e:
        raise TranscriptUnavailable(
            "captions missing and WhisperX is not installed "
            "(pip install whisperx) — episode skipped") from e
    raise TranscriptUnavailable("WhisperX path not yet implemented")  # Phase 5 scope


def create_transcript(episode_id: str) -> dict:
    """Build and persist the transcript for one ranked episode."""
    ep = rdb.query_one("SELECT * FROM reels_episodes WHERE episode_id=?", (episode_id,))
    if not ep:
        raise ValueError(f"unknown episode {episode_id}")
    out_dir = guard_path(STORAGE_ROOT / "transcripts" / episode_id)
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    try:
        cues, method = fetch_youtube_captions(ep["url"], Path(out_dir) / "_dl")
    except TranscriptUnavailable:
        cues, method = whisperx_transcribe(ep["url"])  # raises loud if unavailable

    # enrich cues with speaker placeholder + surrounding context
    segments = []
    for i, c in enumerate(cues):
        segments.append({
            "start": _fmt_ts(c["start_sec"]), "end": _fmt_ts(c["end_sec"]),
            "start_sec": c["start_sec"], "end_sec": c["end_sec"],
            "speaker": "Speaker",  # diarization only with WhisperX
            "text": c["text"],
            "words": c.get("words", []),
            "context_before": cues[i - 1]["text"] if i else "",
            "context_after": cues[i + 1]["text"] if i + 1 < len(cues) else "",
        })

    path = guard_path(Path(out_dir) / "transcript.json")
    Path(path).write_text(json.dumps(
        {"episode_id": episode_id, "method": method, "segments": segments},
        ensure_ascii=False, indent=1), encoding="utf-8")

    transcript_id = f"tr-{uuid.uuid4().hex[:8]}"
    rdb.upsert("reels_transcripts", {
        "transcript_id": transcript_id, "episode_id": episode_id,
        "method": method, "language": "en", "path": str(path),
        "segment_count": len(segments), "created_at": _now(),
    }, ["transcript_id"])
    rq.log(ep["run_id"], "transcript", "reels.transcript.create",
           f"{episode_id}: {len(segments)} cues via {method}")
    return {"transcript_id": transcript_id, "method": method,
            "segment_count": len(segments), "path": str(path)}


async def _handle_transcript_create(job: dict) -> None:
    episode_id = job["subject_id"]
    create_transcript(episode_id)
    rq.enqueue("reels.video.watch_source", run_id=job["run_id"], subject_id=episode_id)


rq.register("reels.transcript.create", _handle_transcript_create)
