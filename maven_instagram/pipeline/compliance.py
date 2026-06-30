"""Compliance scanning — keep every word educational, never advisory.

This enforces the brand + SEBI personal-use boundary: no buy/sell/hold, no price
targets, no hype. Used by the content, caption, and quality-gate steps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import config


@dataclass
class ComplianceResult:
    ok: bool
    violations: list[str]
    score: int  # 0..100


def _strip_allowlisted(text: str) -> str:
    """Remove legitimate finance terms before scanning for banned words."""
    lowered = text.lower()
    for allowed in config.COMPLIANCE_ALLOWLIST:
        lowered = lowered.replace(allowed, " ")
    return lowered


def scan_text(text: str) -> list[str]:
    """Return a list of banned phrases found in ``text`` (word-boundary aware)."""
    cleaned = _strip_allowlisted(text)
    hits: list[str] = []
    for phrase in config.BANNED_PHRASES:
        # Word-boundary match so "hold" doesn't fire inside "household".
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, cleaned):
            hits.append(phrase)
    return hits


def scan_payload(obj: object, _path: str = "") -> list[str]:
    """Recursively scan every string in a nested dict/list structure."""
    violations: list[str] = []
    if isinstance(obj, str):
        for hit in scan_text(obj):
            violations.append(f"{_path or '<root>'}: banned term '{hit}'")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            violations.extend(scan_payload(v, f"{_path}.{k}" if _path else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            violations.extend(scan_payload(v, f"{_path}[{i}]"))
    return violations


def evaluate(payload: object, require_disclaimer_in: str | None = None) -> ComplianceResult:
    """Score compliance 0..100. Each banned term costs points; missing
    disclaimer (when required) is a hard fail."""
    violations = scan_payload(payload)
    score = 100 - min(100, len(violations) * 15)

    if require_disclaimer_in is not None:
        if "not investment advice" not in require_disclaimer_in.lower():
            violations.append("missing required disclaimer")
            score = min(score, 60)

    return ComplianceResult(ok=not violations, violations=violations, score=score)
