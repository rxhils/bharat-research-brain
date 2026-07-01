"""Step 15 — Compliance Shield.

Scans every piece of reel text (hook, angle, script, caption) for advisory / hype
language using the carousel's compliance scanner (read-only reuse).
"""
from __future__ import annotations

from . import compliance_util as _c
from . import state


def run(date: str, *, hooks: dict, angle: dict, script_edited: dict,
        caption: dict) -> dict:
    texts = {
        "hook": hooks["chosen"]["text"],
        "angle": angle["chosen"]["angle"],
        "script": [s["narration"] for s in script_edited["segments"]],
        "caption": caption["caption"],
    }
    violations = _c.scan_payload(texts)
    score = 100 - min(100, len(violations) * 15)
    payload = {"date": date, "violations": violations, "score": score,
               "ok": not violations,
               "disclaimer_present": "not investment advice" in caption["caption"].lower()}
    state.save_artifact(date, "compliance", payload)
    return payload
