"""Reel Template Library loader (Maven Reels Newsroom). Local, free.

Proven beat sheets per viral format (system/reel_template_library.json). The
Format Director and the 3-Variant Blueprint Lab pull a template so a Reel is
chosen from a template, not invented from scratch.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config

LIB_PATH = Path(config.OUTPUT_ROOT) / "system" / "reel_template_library.json"


def load_library() -> dict:
    if not LIB_PATH.exists():
        raise FileNotFoundError(f"template library missing: {LIB_PATH}")
    return json.loads(LIB_PATH.read_text(encoding="utf-8"))


def template_for(format_id: str) -> dict:
    templates = load_library().get("templates", {})
    return templates.get(format_id) or templates.get("hidden_mechanism", {})
