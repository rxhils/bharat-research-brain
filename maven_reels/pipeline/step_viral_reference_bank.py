"""Agent — Viral Reference Bank (Maven Reels Newsroom). Local, free.

Loads the authored Indian-finance-Reel pattern library (system/
viral_reference_bank.json) and surfaces the patterns for the format selected on
this story. Extracts principles; never copies a creator. No fabricated per-Reel
analytics — the bank is design guidance, honestly labelled.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config, format_taxonomy

BANK_PATH = Path(config.OUTPUT_ROOT) / "system" / "viral_reference_bank.json"


def load_bank() -> dict:
    if not BANK_PATH.exists():
        raise FileNotFoundError(f"viral reference bank missing: {BANK_PATH}")
    return json.loads(BANK_PATH.read_text(encoding="utf-8"))


def patterns_for(format_id: str) -> dict:
    """The reference pattern record for one format (falls back to hidden_mechanism)."""
    bank = load_bank()
    fp = bank.get("format_patterns", {})
    return fp.get(format_id) or fp.get("hidden_mechanism", {})


def reject_hooks() -> list[str]:
    return load_bank().get("reject_hooks", [])


def platform_signals() -> dict:
    return load_bank().get("platform_signals", {})


def summary() -> dict:
    """Compact, UI-friendly view of the bank."""
    bank = load_bank()
    return {
        "version": bank.get("version"),
        "source_note": bank.get("source_note"),
        "platform_signals": bank.get("platform_signals", {}),
        "formats_covered": list(bank.get("format_patterns", {}).keys()),
        "creator_categories": [c["category"] for c in bank.get("creator_categories", [])],
        "reject_hooks": bank.get("reject_hooks", []),
        "all_formats": {fid: format_taxonomy.get(fid)["name"] for fid in format_taxonomy.FORMAT_IDS},
    }
