"""LLM scoring layer for Newsroom Reels (local Ollama, llama3.2:3b).

Replaces the v1 keyword heuristics for the judgment scores: episode topic
relevance, segment relevance, virality, and context safety. Compliance stays
regex-based — hard rules are not delegated to a small model.

Fail-soft: every function returns None when Ollama is unavailable or returns
garbage; callers fall back to the keyword scorer and log the downgrade.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = "llama3.2:3b"          # CLAUDE.md fast-classifier assignment
TIMEOUT_S = 90


def llm_json(prompt: str) -> dict[str, Any] | None:
    """One JSON-mode generation. None on any failure — callers must fall back."""
    if os.environ.get("NEWSROOM_REELS_NO_LLM"):
        return None
    body = json.dumps({
        "model": MODEL, "prompt": prompt, "format": "json", "stream": False,
        "options": {"temperature": 0, "num_predict": 200},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA_HOST}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            out = json.loads(resp.read())
        parsed = json.loads(out.get("response", ""))
        return parsed if isinstance(parsed, dict) else None
    except Exception:  # noqa: BLE001 — fail-soft by design
        return None


def _clamp(v: Any) -> int | None:
    try:
        return max(0, min(100, int(v)))
    except (TypeError, ValueError):
        return None


def llm_episode_relevance(title: str, description: str) -> int | None:
    """0-100: is this episode useful source material for Indian-finance Reels?"""
    out = llm_json(
        "You score YouTube episodes for an Indian finance research team.\n"
        "Score 0-100 how strongly this episode is about Indian finance, Indian "
        "stock markets, investing, mutual funds, personal finance, taxation, "
        "RBI/SEBI policy, or the Indian economy. US-only finance, crypto hype, "
        "generic motivation, or non-finance content scores under 30.\n"
        f"TITLE: {title[:200]}\nDESCRIPTION: {(description or '')[:600]}\n"
        'Reply as JSON: {"relevance": <0-100>}')
    return _clamp(out.get("relevance")) if out else None


def llm_segment_scores(text: str) -> dict[str, int] | None:
    """One call scoring a transcript segment on the three judgment gates."""
    out = llm_json(
        "You evaluate a short podcast transcript segment as a potential "
        "Instagram Reel for Indian retail investors.\n"
        "Score each 0-100:\n"
        "- relevance: usefulness for Indian finance/markets/investing/personal "
        "finance (Indian context required for high scores)\n"
        "- virality: hook strength, surprise, clarity, emotional pull, payoff "
        "— would a viewer stop scrolling and watch to the end? Calibration: "
        "40 = ordinary commentary; 60 = interesting but no strong hook; "
        "75 = surprising fact or mistake/myth with a clear payoff; "
        "85+ = concrete numbers, contrarian insight, and a memorable lesson.\n"
        "- context_safety: does it make complete sense on its own, with a "
        "clean start and end, no unresolved pronouns or missing setup, and "
        "not misleading when isolated from the full conversation?\n"
        f"SEGMENT: {text[:900]}\n"
        'Reply as JSON: {"relevance": <0-100>, "virality": <0-100>, '
        '"context_safety": <0-100>}')
    if not out:
        return None
    scores = {k: _clamp(out.get(k)) for k in ("relevance", "virality", "context_safety")}
    if any(v is None for v in scores.values()):
        return None
    return scores  # type: ignore[return-value]


def llm_available() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5) as r:
            models = json.loads(r.read()).get("models", [])
        return any(m.get("name", "").startswith(MODEL) for m in models)
    except Exception:  # noqa: BLE001
        return False
