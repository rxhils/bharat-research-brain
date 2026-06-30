"""Lightweight schema validation for each step's JSON.

Dependency-light (stdlib only) on purpose — the pipeline must run in a bare
Python 3.11 environment. Each validator raises ``SchemaError`` with a precise
message so a malformed upstream artifact fails loudly, not silently.
"""
from __future__ import annotations

from typing import Any

from . import config


class SchemaError(ValueError):
    """Raised when a step artifact does not match its contract."""


def _require(obj: dict, key: str, types: type | tuple[type, ...], ctx: str) -> Any:
    if key not in obj:
        raise SchemaError(f"{ctx}: missing required key '{key}'")
    val = obj[key]
    if not isinstance(val, types):
        raise SchemaError(f"{ctx}: '{key}' must be {types}, got {type(val)}")
    return val


def validate_research(data: dict) -> dict:
    """Validate Step 1 output and enforce importance/confidence thresholds."""
    _require(data, "date", str, "research")
    _require(data, "market_summary", str, "research")
    stories = _require(data, "top_3_stories", list, "research")
    if not stories:
        raise SchemaError("research: top_3_stories is empty")

    for i, s in enumerate(stories):
        ctx = f"research.story[{i}]"
        for field_name in ("headline", "what_happened", "why_it_matters",
                            "investor_takeaway"):
            _require(s, field_name, str, ctx)
        _require(s, "sources", list, ctx)
        imp = _require(s, "importance_score", int, ctx)
        conf = _require(s, "confidence_score", int, ctx)
        if not (1 <= imp <= 10) or not (1 <= conf <= 10):
            raise SchemaError(f"{ctx}: scores must be in 1..10")
        if not s["sources"]:
            raise SchemaError(f"{ctx}: every story must cite at least one source")

    return data


def passing_stories(data: dict) -> list[dict]:
    """Stories that clear both thresholds, ranked by importance desc."""
    qualified = [
        s for s in data["top_3_stories"]
        if s["importance_score"] >= config.MIN_IMPORTANCE_SCORE
        and s["confidence_score"] >= config.MIN_CONFIDENCE_SCORE
    ]
    return sorted(qualified, key=lambda s: s["importance_score"], reverse=True)


def validate_content_plan(data: dict) -> dict:
    plan = _require(data, "carousel_plan", list, "content_plan")
    if not (1 <= len(plan) <= 3):
        raise SchemaError("content_plan: expected 1..3 slides")
    for i, slide in enumerate(plan):
        ctx = f"content_plan.slide[{i}]"
        _require(slide, "slide", int, ctx)
        _require(slide, "headline", str, ctx)
        _require(slide, "subtitle", str, ctx)
        _require(slide, "bullets", list, ctx)
        _require(slide, "takeaway", str, ctx)
        _require(slide, "source_footer", str, ctx)
    return data


def validate_caption(data: dict) -> dict:
    cap = _require(data, "caption", str, "caption")
    if len(cap) > config.IG_CAPTION_MAX:
        raise SchemaError(
            f"caption: {len(cap)} chars exceeds IG max {config.IG_CAPTION_MAX}"
        )
    _require(data, "disclaimer", str, "caption")
    return data


def validate_hashtags(data: dict) -> dict:
    tags = _require(data, "hashtags", list, "hashtags")
    if not (10 <= len(tags) <= 18):
        raise SchemaError(f"hashtags: expected 10..18, got {len(tags)}")
    if len(tags) > config.IG_MAX_HASHTAGS:
        raise SchemaError("hashtags: exceeds Instagram 30-tag limit")
    for t in tags:
        if not isinstance(t, str) or not t.startswith("#"):
            raise SchemaError(f"hashtags: '{t}' must be a string starting with #")
    return data
