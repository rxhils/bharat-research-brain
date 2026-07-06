"""Agent 2 — Fact Check Desk.

Deterministic verification gate that runs BEFORE any slide is written.
Blocks: unsupported claims (no URL), weak/unknown sources, rumour framing,
advisory language, price-target stories and penny-stock hype. Simulated
stories pass ONLY with an explicit warning so the QA gate can refuse
publishing them.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from . import config, state


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return ""


def _is_trusted(url: str) -> bool:
    d = _domain(url)
    return any(d == t or d.endswith("." + t) for t in config.TRUSTED_DOMAINS)


def banned_language(text: str) -> list[str]:
    """Advisory/hype tokens present in text (word-boundary, minus safe vocab)."""
    t = text.lower()
    for ok in config.BANNED_EXCEPTIONS:
        t = t.replace(ok, " ")
    hits = []
    for tok in config.BANNED_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", t):
            hits.append(tok)
    return hits


def _check(story: dict) -> tuple[bool, list[str], list[str], int]:
    """-> (verified, reject_reasons, warnings, confidence 0-100)."""
    text = f"{story.get('headline', '')} {story.get('summary', '')}"
    reasons: list[str] = []
    warnings: list[str] = []
    confidence = 50

    if story.get("simulated"):
        return True, [], ["SIMULATION story — framework test only; QA will "
                          "block publishing"], 0

    srcs = [s for s in story.get("sources", []) if s.get("url")]
    if not srcs:
        reasons.append("no source URL — unsupported claim")
    else:
        trusted = [s for s in srcs if _is_trusted(s["url"])]
        confidence += min(len(srcs), 3) * 10
        if trusted:
            confidence += 20
        else:
            warnings.append("no Tier-A/B source domain; weighted with skepticism")
            confidence -= 20

    low = text.lower()
    rumours = [m for m in config.RUMOUR_MARKERS if m in low]
    if rumours:
        if len(srcs) >= 2:
            warnings.append(f"rumour framing ({', '.join(rumours)}) — kept only "
                            "because multiple sources carry it")
            confidence -= 15
        else:
            reasons.append(f"rumour framing with a single source: {', '.join(rumours)}")

    advisory = banned_language(text)
    if advisory:
        reasons.append(f"advisory/hype language in source story: {', '.join(advisory)}")

    if re.search(r"\btarget\b.{0,20}(₹|rs|price)|price target", low):
        reasons.append("price-target story — excluded by policy")
    if re.search(r"penny stock|small ?cap gem|next multibagger", low):
        reasons.append("penny-stock hype — excluded by policy")

    return (not reasons), reasons, warnings, max(0, min(confidence, 100))


def run(job_id: str) -> dict:
    radar = state.load_artifact(job_id, "market_radar") or {}
    verified, rejected, all_warnings = [], [], []
    confidences = []

    for story in radar.get("candidate_stories", []):
        ok, reasons, warnings, conf = _check(story)
        all_warnings.extend(f"{story['story_id']}: {w}" for w in warnings)
        if ok:
            verified.append({**story, "fact_confidence": conf,
                             "fact_warnings": warnings})
            confidences.append(conf)
        else:
            rejected.append({"story_id": story["story_id"],
                             "headline": story["headline"], "reasons": reasons})

    payload = {
        "verified_stories": verified,
        "rejected_stories": rejected,
        "fact_warnings": all_warnings,
        "source_confidence": round(sum(confidences) / len(confidences)) if confidences else 0,
        "data_mode": radar.get("data_mode", "unknown"),
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "fact_check", payload)
    return payload
