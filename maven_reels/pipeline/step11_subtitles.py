"""Step 11 — Subtitle Engine.

Builds burned-in subtitle timing (captions.srt) from the edited script segments.
Timings come from segment durations (or, at real-run time, the TTS-reported
duration). Short on-screen lines for fast reading.
"""
from __future__ import annotations

from . import config, state


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _lines(narration: str) -> list[str]:
    words, out, cur = narration.replace("…", "").split(), [], []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) > 32:
            out.append(" ".join(cur)); cur = []
    if cur:
        out.append(" ".join(cur))
    return out or [narration[:40]]


def run(date: str, script_edited: dict) -> dict:
    srt, idx, t = [], 1, 0.0
    for seg in script_edited["segments"]:
        lines = _lines(seg["narration"])
        per = seg["seconds"] / max(1, len(lines))
        for ln in lines:
            srt.append(f"{idx}\n{_ts(t)} --> {_ts(t + per)}\n{ln}\n")
            idx += 1; t += per
    srt_text = "\n".join(srt)
    srt_path = config.run_dir(date) / "captions.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text(srt_text, encoding="utf-8")
    payload = {"date": date, "srt_path": str(srt_path), "cue_count": idx - 1,
               "total_seconds": round(t, 1)}
    state.save_artifact(date, "subtitles", payload)
    return payload
