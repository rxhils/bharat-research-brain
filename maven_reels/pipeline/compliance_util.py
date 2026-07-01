"""Compliance wrapper — reuses the carousel's scanner (read-only import).

Keeps the Reels pipeline's advisory-language guardrail identical to the carousel
pipeline without duplicating the word lists or modifying maven_instagram.
"""
from __future__ import annotations

from maven_instagram.pipeline import compliance as _carousel_compliance


def scan(text: str) -> list[str]:
    """Return banned advisory phrases found in ``text`` (empty = clean)."""
    return _carousel_compliance.scan_text(text)


def scan_payload(obj: object) -> list[str]:
    return _carousel_compliance.scan_payload(obj)


def evaluate(payload: object, require_disclaimer_in: str | None = None):
    return _carousel_compliance.evaluate(payload, require_disclaimer_in=require_disclaimer_in)
