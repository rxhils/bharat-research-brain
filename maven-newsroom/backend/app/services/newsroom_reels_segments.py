"""Phase 6 agents: Segment Discovery + the four scoring gates.

Segment Discovery turns a transcript into 8-12 candidate Reel moments
(20-75s, preferring 28-55s, clean start/end, complete thought arc).
Then each candidate passes four independent gates:

  Indian Finance Relevance  >= 80
  Virality                  >= 75
  Compliance risk           <= 35
  Context Safety            >= 80

Deterministic heuristics over the transcript text (v1) — each scorer is a
pure function an LLM scorer can replace without touching the pipeline.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq
from .newsroom_reels_sources import topic_relevance

MIN_LEN, MAX_LEN = 20, 30           # seconds — operator wants tight, captivating clips
PREF_MIN, PREF_MAX = 22, 30
TARGET_CANDIDATES = (20, 30)        # large pool; gates cut it down to the best 5

DEFAULT_DISCLAIMER = "Educational content only. Not financial advice. Source credited."


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ------------------------------------------------- Agent 10: Segment Discovery

_SENT_END = re.compile(r"[.!?]\s*$")
_CLEAN_START = re.compile(r"^[A-Z\"'‘“]")


def discover_segments(episode_id: str) -> list[dict]:
    """Merge transcript cues into candidate moments with clean boundaries."""
    tr = rdb.query_one(
        "SELECT * FROM reels_transcripts WHERE episode_id=? ORDER BY created_at DESC",
        (episode_id,))
    if not tr:
        raise ValueError(f"no transcript for {episode_id}")
    cues = json.loads(Path(tr["path"]).read_text(encoding="utf-8"))["segments"]
    if not cues:
        return []

    # rank every cue as a potential anchor: hooky, finance-relevant openings
    # win over blind position sampling (the intro is never the good part)
    def _anchor_strength(idx: int) -> int:
        window = " ".join(c["text"] for c in cues[idx:idx + 6]).lower()
        s = sum(6 for w in _HOOK_WORDS if w in window)
        s += min(20, topic_relevance(window) // 5)
        if _CLEAN_START.match(cues[idx]["text"]):
            s += 10
        return s

    anchors = sorted(range(len(cues)), key=_anchor_strength, reverse=True)

    candidates: list[dict] = []
    used_spans: list[tuple[float, float]] = []
    for i in anchors:
        if len(candidates) >= TARGET_CANDIDATES[1]:
            break
        if not _CLEAN_START.match(cues[i]["text"]):
            continue
        start = cues[i]
        # skip anchors overlapping an already-taken span
        if any(a - 5 < start["start_sec"] < b + 5 for a, b in used_spans):
            continue
        j, last_clean_end = i, None
        while j < len(cues):
            dur = cues[j]["end_sec"] - start["start_sec"]
            if dur > MAX_LEN:
                break
            if dur >= MIN_LEN and _SENT_END.search(cues[j]["text"]):
                last_clean_end = j
                if dur >= PREF_MIN:      # good enough — prefer 28-55s
                    break
            j += 1
        if last_clean_end is None:
            continue
        end = cues[last_clean_end]
        text = " ".join(c["text"] for c in cues[i:last_clean_end + 1])
        seg_id = f"seg-{uuid.uuid4().hex[:10]}"
        seg = {
            "segment_id": seg_id, "episode_id": episode_id,
            "start_ts": start["start"], "end_ts": end["end"],
            "duration_sec": round(end["end_sec"] - start["start_sec"], 2),
            "speaker": start.get("speaker") or "Speaker", "text": text,
            "context_before": cues[i - 1]["text"] if i else "",
            "context_after": cues[last_clean_end + 1]["text"]
                             if last_clean_end + 1 < len(cues) else "",
            "topic_tags": None, "created_at": _now(),
        }
        rdb.upsert("reels_segments", seg, ["segment_id"])
        candidates.append(seg)
        used_spans.append((start["start_sec"], end["end_sec"]))

    rq.log(None, "segment_discovery", "reels.segments.create",
           f"{episode_id}: {len(candidates)} candidate moments")
    return candidates


# ------------------------------------------------- Agent 11: Relevance

def score_relevance(text: str) -> int:
    """Indian-finance usefulness for a SHORT segment, 0-100.

    Channel-level topic_relevance counts distinct keywords in 25-point jumps —
    too coarse for ~40s of speech. Here repeated mentions also count: distinct
    keywords carry most weight, extra occurrences add up to 25.
    """
    from .newsroom_reels_sources import APPROVED_TOPICS, REJECT_TOPICS
    t = (text or "").lower()
    distinct = [k for k in APPROVED_TOPICS if k in t]
    extra = sum(t.count(k) - 1 for k in distinct)
    rejects = sum(1 for k in REJECT_TOPICS if k in t)
    score = min(100, len(distinct) * 25 + min(25, extra * 10)) - rejects * 40
    return max(0, score)


# ------------------------------------------------- Agent 12: Virality

_HOOK_WORDS = ("mistake", "myth", "truth", "wrong", "never", "secret", "nobody",
               "hidden", "why ", "how ", "stop", "biggest", "avoid", "trap",
               "actually", "real reason", "most people")
_PAYOFF_WORDS = ("because", "so the", "that's why", "which means", "the answer",
                 "instead", "here's")


def score_virality(text: str) -> int:
    t = text.lower()
    score = 40
    score += min(30, sum(8 for w in _HOOK_WORDS if w in t))
    score += min(15, sum(5 for w in _PAYOFF_WORDS if w in t))
    if re.search(r"\d", t):
        score += 10                       # numbers = concrete claims
    if "?" in text:
        score += 5
    first = t[:80]
    if any(w in first for w in _HOOK_WORDS):
        score += 10                       # strong first line
    return min(100, score)


# ------------------------------------------------- Agent 13: Compliance

_COMPLIANCE_PATTERNS = [
    (r"\b(buy|sell|short|dump|add)\b.{0,25}\b(this|these|the)?\s*(stock|share|nifty|fund)", "direct buy/sell advice", 45),
    (r"\btarget( price)? of|price target\b", "price target without context", 35),
    (r"\bguaranteed?\b.{0,20}\b(return|profit|income)", "guaranteed returns", 60),
    (r"\b(sure[- ]?shot|jackpot|multibagger tip|100% safe)\b", "tip language", 50),
    (r"\b(sponsored|promo code|use my link|affiliate)\b", "promotional claim", 30),
    (r"\b(fraud|scam|cheat)\b.{0,30}\b(company|promoter|ceo)\b", "potentially defamatory", 40),
]


def score_compliance(text: str) -> tuple[int, list[str]]:
    """Returns (risk 0-100, flags). Risk <= 35 passes."""
    t = text.lower()
    risk, flags = 0, []
    for pattern, label, weight in _COMPLIANCE_PATTERNS:
        if re.search(pattern, t):
            risk += weight
            flags.append(label)
    return min(100, risk), flags


# ------------------------------------------------- Agent 14: Context Safety

_ORPHAN_START = re.compile(r"^(and|but|so|also|then|because|which|that's why)\b", re.I)
_PRONOUN_START = re.compile(r"^(this|that|it|he|she|they|those|these)\b", re.I)
_BACKREF = re.compile(r"\b(as i said|like i mentioned|earlier|going back to|as we discussed)\b", re.I)


def score_context_safety(text: str) -> int:
    score = 100
    if _ORPHAN_START.match(text):
        score -= 25                       # starts mid-thought
    if _PRONOUN_START.match(text):
        score -= 30                       # unclear referent when isolated
    if _BACKREF.search(text):
        score -= 25                       # depends on prior context
    if not _SENT_END.search(text.strip()):
        score -= 20                       # ends abruptly
    return max(0, score)


# ------------------------------------------------- combined gate

def score_segment(segment_id: str) -> dict:
    seg = rdb.query_one("SELECT * FROM reels_segments WHERE segment_id=?", (segment_id,))
    if not seg:
        raise ValueError(f"unknown segment {segment_id}")
    text = seg["text"] or ""
    from .newsroom_reels_llm import llm_segment_scores
    llm = llm_segment_scores(text)
    if llm:
        rel, viral, ctx = llm["relevance"], llm["virality"], llm["context_safety"]
    else:                       # LLM down -> keyword fallback
        rel, viral, ctx = (score_relevance(text), score_virality(text),
                           score_context_safety(text))
    risk, flags = score_compliance(text)   # compliance stays deterministic
    reasons = []
    if rel < 80:
        reasons.append(f"relevance {rel}<80")
    if viral < 75:
        reasons.append(f"virality {viral}<75")
    if risk > 35:
        reasons.append(f"compliance risk {risk}>35: {', '.join(flags)}")
    if ctx < 80:
        reasons.append(f"context safety {ctx}<80")
    passed = not reasons
    row = {
        "segment_id": segment_id, "indian_relevance_score": rel,
        "virality_score": viral, "compliance_risk_score": risk,
        "compliance_flags_json": json.dumps(flags),
        "context_safety_score": ctx, "passed": int(passed),
        "reject_reason": "; ".join(reasons) or None, "scored_at": _now(),
    }
    rdb.upsert("reels_segment_scores", row, ["segment_id"])
    return {**row, "passed": passed}


def score_episode_segments(episode_id: str) -> dict:
    segs = rdb.query_all("SELECT segment_id FROM reels_segments WHERE episode_id=?",
                         (episode_id,))
    results = [score_segment(s["segment_id"]) for s in segs]
    passed = sum(1 for r in results if r["passed"])
    rq.log(None, "segment_scoring", None,
           f"{episode_id}: {passed}/{len(results)} segments passed all gates")
    return {"scored": len(results), "passed": passed}


# ------------------------------------------------- queue handlers

async def _handle_segments_create(job: dict) -> None:
    episode_id = job["subject_id"]
    discover_segments(episode_id)
    rq.enqueue("reels.segment.score_finance", run_id=job["run_id"], subject_id=episode_id)


async def _handle_segment_scoring(job: dict) -> None:
    """One combined pass covers all four score queues (each gate is a pure fn)."""
    score_episode_segments(job["subject_id"])
    rq.enqueue("reels.clip.plan", run_id=job["run_id"], subject_id=job["subject_id"])


rq.register("reels.segments.create", _handle_segments_create)
rq.register("reels.segment.score_finance", _handle_segment_scoring)
