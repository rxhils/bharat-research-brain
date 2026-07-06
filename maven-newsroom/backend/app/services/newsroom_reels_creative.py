"""Phase 8 agents: Hook Writer, Caption, Visual Storyboard.

Hook Writer produces 3-5 finance-safe hook options per clip (8-12 words, no
fake claims, no buy/sell framing). Caption Agent builds two-line mobile
subtitles from the transcript plus the Instagram caption, attribution,
disclaimer, and hashtags. Visual Storyboard lays out the Reel using ONLY
Remotion-based assets: hook card, source bar, speaker clip with subtitles,
keyword cards, disclaimer, Maven outro. No Higgsfield anywhere.

Everything lands in reels_edit_plans — the single input the Remotion Render
Agent (Phase 9) consumes.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq
from .newsroom_reels_segments import DEFAULT_DISCLAIMER, score_compliance
from .newsroom_reels_storage import run_subdir

ACCENT_COLOR = "#1FB6A6"          # Maven teal (settings palette)
BRAND_HANDLE = "@try.maven"

_TOPIC_PATTERNS = [
    (r"\bsip\b", "SIP"), (r"mutual fund", "mutual funds"), (r"\brbi\b", "RBI"),
    (r"\bsebi\b", "SEBI"), (r"\bnifty|sensex\b", "the index"),
    (r"\btax", "tax"), (r"small ?cap", "smallcaps"), (r"\bipo\b", "IPOs"),
    (r"valuation", "valuations"), (r"dividend", "dividends"),
    (r"portfolio", "your portfolio"), (r"stock market|stocks", "the market"),
    (r"invest", "investing"),
]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _main_topic(text: str) -> str:
    t = text.lower()
    for pattern, label in _TOPIC_PATTERNS:
        if re.search(pattern, t):
            return label
    return "Indian markets"


# ------------------------------------------------- Agent 18: Hook Writer

def write_hooks(text: str) -> list[str]:
    """3-5 hook options, 8-12 words, curiosity-first, finance-safe."""
    topic = _main_topic(text)
    options = [
        f"The {topic} mistake most Indian investors never notice",
        f"What nobody tells you about {topic} in India",
        f"Most investors get {topic} wrong — here's the real picture",
        f"The uncomfortable truth about {topic} for Indian investors",
        f"Why {topic} doesn't work the way you think",
    ]
    safe = []
    for h in options:
        risk, _ = score_compliance(h)
        words = len(h.split())
        if risk == 0 and 6 <= words <= 12:
            safe.append(h)
    return safe[:5]


def pick_hook(options: list[str], text: str) -> str:
    """Prefer the hook sharing the most vocabulary with the actual clip."""
    words = set(text.lower().split())
    return max(options, key=lambda h: len(set(h.lower().split()) & words))


# ------------------------------------------------- Agent 19: Caption Agent

_HASHTAGS = ("#IndianStockMarket #PersonalFinance #InvestingIndia "
             "#MutualFunds #FinancialLiteracy #NiftyFifty #StockMarketIndia")


def _two_line_chunks(cues: list[dict[str, Any]], max_chars: int = 38) -> list[dict[str, Any]]:
    """Re-chunk transcript cues into <=2-line mobile-readable subtitle events."""
    events = []
    for c in cues:
        words, line = c["text"].split(), ""
        lines: list[str] = []
        for w in words:
            if len(line) + len(w) + 1 > max_chars and line:
                lines.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            lines.append(line)
        # pair lines into 2-line events, splitting the cue duration evenly
        pairs = [lines[i:i + 2] for i in range(0, len(lines), 2)]
        dur = (c["end_sec"] - c["start_sec"]) / max(1, len(pairs))
        for k, pair in enumerate(pairs):
            events.append({
                "start_sec": round(c["start_sec"] + k * dur, 2),
                "end_sec": round(c["start_sec"] + (k + 1) * dur, 2),
                "lines": pair,
            })
    return events


def _ts_to_sec(ts: str) -> float:
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _words_to_events(words: list[dict[str, Any]], t0: float,
                     max_words: int = 5, max_chars: int = 22) -> list[dict[str, Any]]:
    """Group word-timed tokens into short caption events that follow the voice.

    Event start/end come from the actual word timestamps, so subtitles land
    exactly when the words are spoken.
    """
    groups: list[list[dict[str, Any]]] = []
    group: list[dict[str, Any]] = []
    for w in words:
        group.append(w)
        line_len = sum(len(g["w"]) + 1 for g in group)
        if len(group) >= max_words or line_len > max_chars * 2:
            groups.append(group)
            group = []
    if group:
        groups.append(group)
    out = []
    for i, g in enumerate(groups):
        start = g[0]["t"] - t0
        # an event ends when the next one starts (or +2.5s for the last)
        end = (groups[i + 1][0]["t"] - t0) if i + 1 < len(groups) else g[-1]["t"] - t0 + 2.5
        text = " ".join(x["w"] for x in g)
        # wrap into <=2 lines
        lines, line = [], ""
        for tok in text.split():
            if len(line) + len(tok) + 1 > max_chars and line:
                lines.append(line)
                line = tok
            else:
                line = f"{line} {tok}".strip()
        if line:
            lines.append(line)
        out.append({"start_sec": round(max(0.0, start), 3),
                    "end_sec": round(max(0.1, end), 3), "lines": lines[:2]})
    return out


def build_captions(clip_id: str, run_date: str) -> dict[str, Any]:
    """Subtitle events (clip-relative), IG caption, attribution, disclaimer."""
    clip = rdb.query_one("SELECT * FROM reels_clip_candidates WHERE clip_id=?", (clip_id,))
    if not clip:
        raise ValueError(f"unknown clip {clip_id}")
    seg = rdb.query_one("SELECT * FROM reels_segments WHERE segment_id=?",
                        (clip["segment_id"],))
    ep = rdb.query_one("SELECT e.*, s.name AS source_name FROM reels_episodes e "
                       "LEFT JOIN reels_sources s ON s.source_id=e.source_id "
                       "WHERE e.episode_id=?", (clip["episode_id"],))
    tr = rdb.query_one("SELECT * FROM reels_transcripts WHERE episode_id=? "
                       "ORDER BY created_at DESC", (clip["episode_id"],))
    if not (seg and ep and tr):
        raise ValueError(f"missing segment/episode/transcript for clip {clip_id}")

    t0, t1 = _ts_to_sec(clip["start_ts"]), _ts_to_sec(clip["end_ts"])
    cues = json.loads(Path(tr["path"]).read_text(encoding="utf-8"))["segments"]
    words = [w for c in cues for w in c.get("words", [])
             if t0 <= w["t"] < t1]
    if words:
        subtitle_events = _words_to_events(words, t0)
    else:   # legacy transcripts without word timing
        window = [{**c, "start_sec": c["start_sec"] - t0, "end_sec": c["end_sec"] - t0}
                  for c in cues if c["start_sec"] >= t0 and c["end_sec"] <= t1]
        subtitle_events = _two_line_chunks(window)

    attribution = f"Source: {ep['source_name'] or 'YouTube'} — {ep['title']}"[:110]
    ig_caption = (
        f"{seg['text'][:180].rsplit(' ', 1)[0]}…\n\n"
        f"{attribution}\nFull episode: {ep['url']}\n\n"
        f"{DEFAULT_DISCLAIMER}\n\n{_HASHTAGS}")

    out_dir = run_subdir(run_date, "captions")
    path = Path(out_dir) / f"{clip_id}.json"
    path.write_text(json.dumps({
        "clip_id": clip_id, "subtitle_events": subtitle_events,
        "ig_caption": ig_caption, "attribution": attribution,
        "disclaimer": DEFAULT_DISCLAIMER, "hashtags": _HASHTAGS,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"captions_path": str(path), "subtitle_events": len(subtitle_events),
            "ig_caption": ig_caption, "attribution": attribution}


# ------------------------------------------------- Agent 20: Visual Storyboard

def build_storyboard(clip_id: str, hook: str, captions_path: str,
                     attribution: str) -> dict[str, Any]:
    """Remotion-only layout: hook card, source bar, subtitles, outro."""
    clip = rdb.query_one("SELECT * FROM reels_clip_candidates WHERE clip_id=?", (clip_id,))
    if not clip:
        raise ValueError(f"unknown clip {clip_id}")
    seg = rdb.query_one("SELECT * FROM reels_segments WHERE segment_id=?",
                        (clip["segment_id"],))
    clip_dur = round(_ts_to_sec(clip["end_ts"]) - _ts_to_sec(clip["start_ts"]), 2)
    keywords = [label for pattern, label in _TOPIC_PATTERNS
                if re.search(pattern, (seg["text"] if seg else "").lower())][:3]
    storyboard = {
        "template": "maven-dark-premium-v1",
        "resolution": {"w": 1080, "h": 1920}, "fps": 30,
        "accent_color": ACCENT_COLOR,
        "style": {"background": "#05070A", "captions": "white",
                  "max_caption_lines": 2, "clutter": "none"},
        "timeline": [
            {"t": [0.0, 1.5], "layer": "hook_card", "text": hook},
            {"t": [1.5, 3.0], "layer": "source_bar",
             "text": attribution, "disclaimer": DEFAULT_DISCLAIMER},
            {"t": [3.0, 3.0 + clip_dur], "layer": "speaker_clip",
             "src": clip["clip_path"], "subtitles": captions_path,
             "keyword_cards": keywords, "motion": "subtle_zoom"},
            {"t": [3.0 + clip_dur, 3.0 + clip_dur + 1.5], "layer": "maven_outro",
             "text": BRAND_HANDLE},
        ],
        "duration_sec": round(3.0 + clip_dur + 1.5, 2),
    }
    return storyboard


# ------------------------------------------------- edit-plan assembly

def create_edit_plan(clip_id: str, run_date: str) -> dict[str, Any]:
    seg = rdb.query_one(
        "SELECT g.* FROM reels_segments g JOIN reels_clip_candidates c "
        "ON c.segment_id = g.segment_id WHERE c.clip_id=?", (clip_id,))
    if not seg:
        raise ValueError(f"no segment for clip {clip_id}")
    hooks = write_hooks(seg["text"])
    if not hooks:
        raise ValueError(f"no safe hooks generated for {clip_id}")
    hook = pick_hook(hooks, seg["text"])
    caps = build_captions(clip_id, run_date)
    storyboard = build_storyboard(clip_id, hook, caps["captions_path"],
                                  caps["attribution"])
    plan_id = f"plan-{uuid.uuid4().hex[:8]}"
    rdb.upsert("reels_edit_plans", {
        "plan_id": plan_id, "clip_id": clip_id, "hook_text": hook,
        "hook_options_json": json.dumps(hooks, ensure_ascii=False),
        "captions_path": caps["captions_path"],
        "storyboard_json": json.dumps(storyboard, ensure_ascii=False),
        "template": storyboard["template"], "accent_color": ACCENT_COLOR,
        "ig_caption": caps["ig_caption"], "hashtags": _HASHTAGS,
        "disclaimer": DEFAULT_DISCLAIMER, "attribution": caps["attribution"],
        "created_at": _now(),
    }, ["plan_id"])
    return {"plan_id": plan_id, "hook": hook, "hook_options": hooks,
            "storyboard": storyboard}


# ------------------------------------------------- queue handlers

def _run_date(run_id: str | None) -> str:
    run = rdb.query_one("SELECT run_date FROM reels_daily_runs WHERE run_id=?",
                        (run_id,)) if run_id else None
    return run["run_date"] if run else _now()[:10]


async def _handle_hook_write(job: dict[str, Any]) -> None:
    # hooks/captions/storyboard are one edit plan; chain ends at render queue
    create_edit_plan(job["subject_id"], _run_date(job.get("run_id")))
    rq.enqueue("reels.render.create", run_id=job.get("run_id"),
               subject_id=job["subject_id"])


rq.register("reels.hook.write", _handle_hook_write)
