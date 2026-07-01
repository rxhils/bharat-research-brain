"""Step 2 — Viral Fit Gate.

The most important reel-specific gate. The most *important* story is not always
the best *reel*. This scores every research story on 7 dimensions, weights them
toward scroll-stopping traits, ranks them, and picks the single best reel story
(recording the losers with reasons).
"""
from __future__ import annotations

import re

from . import schemas, state
from .config import VIRAL_FIT_DIMS, VIRAL_FIT_MIN, VIRAL_FIT_WEIGHTS

_EMOTION = re.compile(r"\b(crash|plunge|plunged|wiped|surge|surged|jump|jumped|"
                      r"soar|soared|slump|slumped|panic|fear|record|shock|"
                      r"tumble|tumbled|rally|rallied|3-year low|52-week)\b", re.I)
_BIGNUM = re.compile(r"(lakh crore|crore|\d+\s*%|₹|rs\s?\d)", re.I)
_RETAIL = re.compile(r"\b(bank|banking|nifty|sensex|reliance|adani|tata|hdfc|"
                     r"infosys|tcs|maruti|it|auto|pharma|sbi|kotak)\b", re.I)


def _score_story(s: dict) -> dict[str, float]:
    text = " ".join(str(s.get(k, "")) for k in
                    ("headline", "what_happened", "why_it_matters"))
    what = str(s.get("what_happened", ""))
    return {
        "importance": float(s.get("importance_score", 8)),
        "curiosity": min(10.0, 5 + 2 * len(re.findall(r"\bwhy\b", text, re.I))
                         + (2 if "?" in s.get("headline", "") else 0)),
        "emotional": min(10.0, 4 + 2.0 * len(_EMOTION.findall(text))),
        # shorter = simpler to explain in 30s
        "simplicity": max(2.0, 10 - len(what) / 90),
        "visual": min(10.0, 5 + 1.5 * len(s.get("affected_sectors", []) or [])
                      + (2 if s.get("key_numbers") else 0)),
        "shareability": min(10.0, 4 + 2.0 * len(_BIGNUM.findall(text))),
        "retail_relevance": min(10.0, 4 + 1.5 * len(set(_RETAIL.findall(text.lower())))),
    }


def _weighted(scores: dict[str, float]) -> float:
    num = sum(scores[d] * VIRAL_FIT_WEIGHTS[d] for d in VIRAL_FIT_DIMS)
    den = sum(VIRAL_FIT_WEIGHTS.values())
    return round(num / den, 2)


def run(date: str, research: dict) -> dict:
    ranked = []
    for s in research["top_3_stories"]:
        dims = {k: round(v, 1) for k, v in _score_story(s).items()}
        ranked.append({
            "rank_in_research": s.get("rank"),
            "headline": s.get("headline"),
            "dims": dims,
            "viral_fit": _weighted(dims),
            "story": s,
        })
    ranked.sort(key=lambda r: r["viral_fit"], reverse=True)
    chosen = ranked[0]
    for r in ranked[1:]:
        r["rejected_reason"] = (
            f"Lower viral fit ({r['viral_fit']} vs {chosen['viral_fit']}); "
            f"weaker on " + ", ".join(
                d for d in ("curiosity", "emotional", "visual", "shareability")
                if r["dims"][d] < chosen["dims"][d]) or "overall balance")

    payload = {
        "date": date,
        "dimensions": VIRAL_FIT_DIMS,
        "weights": VIRAL_FIT_WEIGHTS,
        "min_fit": VIRAL_FIT_MIN,
        "chosen": {"headline": chosen["headline"], "viral_fit": chosen["viral_fit"],
                   "dims": chosen["dims"], "story": chosen["story"]},
        "ranked": [{k: r[k] for k in ("headline", "viral_fit", "dims")
                    } | ({"rejected_reason": r["rejected_reason"]} if "rejected_reason" in r else {})
                   for r in ranked],
        "reel_worthy": chosen["viral_fit"] >= VIRAL_FIT_MIN,
    }
    schemas.validate_viral_fit(payload)
    state.save_artifact(date, "viral_fit", payload)
    return payload
