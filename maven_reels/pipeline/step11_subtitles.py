"""Step 11 — Subtitle Engine.

Builds kinetic subtitle cues from the edited script segments: short (<=6-word)
lines with a highlighted key word, timed from segment durations (or, at real-run
time, the TTS-reported duration). Emits BOTH a burned-in `captions.srt` and a
structured `subtitles` cue list [{start,end,text,emphasis}] that the Motion
Graphics Engine renders as animated captions.
"""
from __future__ import annotations

import re

from . import config, state

_NUM = re.compile(r"-?\d+(?:\.\d+)?%?")
_STOP = {"the", "a", "an", "and", "but", "for", "with", "this", "that", "is",
         "was", "it", "to", "of", "in", "on", "as", "at", "its", "are", "were"}


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunks(narration: str, max_chars: int = 22, max_words: int = 5) -> list[str]:
    """Split narration into short caption lines bounded by BOTH width (chars) and
    word count, so wide lines wrap and never clip the 1080px frame."""
    words = narration.replace("…", "").split()
    out, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if cur and (len(trial) > max_chars or len(cur) >= max_words):
            out.append(" ".join(cur)); cur = [w]
        else:
            cur.append(w)
    if cur:
        out.append(" ".join(cur))
    return out or [narration[:max_chars]]


def _emphasis(text: str) -> str:
    """Pick a key word to highlight: a number/percent if present, else the
    longest non-stopword token."""
    m = _NUM.search(text)
    if m:
        return m.group(0)
    toks = [re.sub(r"[^A-Za-z0-9%.-]", "", w) for w in text.split()]
    toks = [t for t in toks if t and t.lower() not in _STOP]
    return max(toks, key=len) if toks else ""


def run(date: str, script_edited: dict) -> dict:
    srt, cues, idx, t = [], [], 1, 0.0
    for seg in script_edited["segments"]:
        lines = _chunks(seg["narration"])
        per = seg["seconds"] / max(1, len(lines))
        for ln in lines:
            start, end = round(t, 2), round(t + per, 2)
            emph = _emphasis(ln)
            srt.append(f"{idx}\n{_ts(t)} --> {_ts(t + per)}\n{ln}\n")
            cues.append({"start": start, "end": end, "text": ln, "emphasis": emph})
            idx += 1; t += per
    srt_path = config.run_dir(date) / "captions.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("\n".join(srt), encoding="utf-8")
    payload = {"date": date, "srt_path": str(srt_path), "cue_count": len(cues),
               "total_seconds": round(t, 1), "subtitles": cues}
    state.save_artifact(date, "subtitles", payload)
    return payload
