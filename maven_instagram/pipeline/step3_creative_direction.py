"""Step 3 — Creative direction.

Defines three candidate visual systems, scores them against the brief
(premium / clean / mobile-readable / finance-editorial), and selects one. The
selected direction's design tokens flow into the image prompts in Step 4.
"""
from __future__ import annotations

from . import state

DIRECTIONS = [
    {
        "concept_name": "Market Digest Dark",
        "style": "Premium finance-editorial, dark market-digest cover system",
        "layout": "Top: section label + date. Middle: one large headline. "
                  "Lower third: compact data chips. Footer: source + brand.",
        "background": "Near-black navy (#0B1220) with a faint single trend line, "
                      "generous negative space, no candlestick spam",
        "typography": "Tight geometric sans; oversized bold headline, light "
                      "subhead, mono for numbers",
        "visual_elements": "Delta chips (▲/▼ %), thin rule lines, one accent "
                           "color per slide, small circular icon",
        "chart_style": "Single minimal line or 3-4 bar mini-chart, no gridlines",
        "why_it_fits": "Reads instantly on mobile, looks like a high-end market "
                       "digest, lets numbers breathe",
        "what_to_avoid": ["clutter", "random candlesticks", "neon", "3D",
                          "stocky bull/bear art", "tiny text"],
        "score": 0,
    },
    {
        "concept_name": "Analytical White",
        "style": "Clean white analytical report slide",
        "layout": "Left-aligned headline column + right data card; airy margins",
        "background": "White / very light grey, thin teal accent rule",
        "typography": "Editorial serif headline + sans body; strong hierarchy",
        "visual_elements": "Boxed stat cards, one highlighted metric, subtle "
                           "iconography",
        "chart_style": "Flat horizontal bars or a single sparkline",
        "why_it_fits": "Feels like a research note; great for company/sector "
                       "data slides; very legible",
        "what_to_avoid": ["gradients", "drop shadows everywhere", "emoji",
                          "cartoon", "copied smallcase layout"],
        "score": 0,
    },
    {
        "concept_name": "Hybrid Cover+Cards",
        "style": "Dark cover (slide 1) + light data cards (slides 2-3)",
        "layout": "Slide 1 dark hero; slides 2-3 light cards with consistent "
                  "footer system",
        "background": "Mixed: dark navy hero, light analytical interiors",
        "typography": "Consistent sans family across both modes",
        "visual_elements": "Shared chip + footer system, accent color carries "
                           "across slides",
        "chart_style": "Line on cover, bars on interior cards",
        "why_it_fits": "Maximum visual variety while staying one cohesive system "
                       "— avoids three near-identical slides",
        "what_to_avoid": ["inconsistent fonts between slides", "too many colors",
                          "clutter", "fake terminals"],
        "score": 0,
    },
]


def _score(direction: dict) -> int:
    """Heuristic fit score: rewards readability + variety, penalizes risk."""
    score = 70
    text = " ".join(str(v) for v in direction.values()).lower()
    if "mobile" in direction["why_it_fits"].lower() or "legible" in text:
        score += 8
    if "variety" in text or "hybrid" in direction["concept_name"].lower():
        score += 12  # avoiding repetitive slides is a stated requirement
    if "consistent" in text:
        score += 6
    score -= 2 * sum(1 for _ in direction["what_to_avoid"])
    return max(0, min(100, score))


def run(date: str) -> dict:
    directions = [dict(d, score=_score(d)) for d in DIRECTIONS]
    chosen = max(directions, key=lambda d: d["score"])

    payload = {
        "date": date,
        "directions": directions,
        "selected": chosen["concept_name"],
        "selection_rationale": (
            f"'{chosen['concept_name']}' scored highest because it maximizes "
            "slide-to-slide variety while keeping one cohesive premium system — "
            "directly addressing the 'don't make three repetitive slides' "
            "requirement — and stays highly mobile-readable."
        ),
    }
    state.save_artifact(date, "creative", payload)
    return payload
