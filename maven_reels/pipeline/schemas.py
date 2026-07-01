"""Lightweight validators for reel artifacts (stdlib only)."""
from __future__ import annotations

from . import config


class SchemaError(ValueError):
    """Raised when a reel artifact does not match its contract."""


def _req(obj: dict, key: str, types, ctx: str):
    if key not in obj:
        raise SchemaError(f"{ctx}: missing '{key}'")
    if not isinstance(obj[key], types):
        raise SchemaError(f"{ctx}: '{key}' must be {types}")
    return obj[key]


def validate_research(d: dict) -> dict:
    _req(d, "top_3_stories", list, "reel.research")
    if not d["top_3_stories"]:
        raise SchemaError("reel.research: no stories")
    return d


def validate_viral_fit(d: dict) -> dict:
    _req(d, "chosen", dict, "reel.viral_fit")
    _req(d, "ranked", list, "reel.viral_fit")
    return d


def validate_hooks(d: dict) -> dict:
    hooks = _req(d, "hooks", list, "reel.hooks")
    if len(hooks) < len(config.HOOK_BUCKETS):
        raise SchemaError("reel.hooks: expected >=1 hook per bucket")
    _req(d, "chosen", dict, "reel.hooks")
    return d


def validate_script(d: dict) -> dict:
    segs = _req(d, "segments", list, "reel.script")
    if not segs:
        raise SchemaError("reel.script: empty")
    total = sum(s.get("seconds", 0) for s in segs)
    if not (config.REEL_MIN_SECONDS - 5 <= total <= config.REEL_MAX_SECONDS + 5):
        raise SchemaError(f"reel.script: total {total}s outside 20-35s band")
    return d


def validate_storyboard(d: dict) -> dict:
    scenes = _req(d, "scenes", list, "reel.storyboard")
    if not (config.SCENE_MIN - 1 <= len(scenes) <= config.SCENE_MAX + 2):
        raise SchemaError(f"reel.storyboard: {len(scenes)} scenes outside range")
    return d
