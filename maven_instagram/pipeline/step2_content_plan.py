"""Step 2 — Content planning.

Turns the gated research stories into a 3-slide carousel plan. Deterministic:
slide N maps to story rank N. Writing rules (simple English, premium tone, no
advice) are enforced by trimming/normalizing and a compliance scan.
"""
from __future__ import annotations

from . import compliance, schemas, state
from .config import BRAND_NAME, BRAND_SITE


def _short(text: str, max_chars: int) -> str:
    """Clamp a sentence to a slide-friendly length on a word boundary."""
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:") + "…"


def _bullets_for(story: dict) -> list[str]:
    """Build 2-3 tight, factual bullets from a story's key numbers / sectors."""
    bullets: list[str] = []
    for kn in story.get("key_numbers", [])[:3]:
        bullets.append(_short(kn, 70))
    if len(bullets) < 2:
        sectors = ", ".join(story.get("affected_sectors", [])[:3])
        if sectors:
            bullets.append(_short(f"In focus: {sectors}", 70))
    return bullets[:3]


def _source_footer(story: dict) -> str:
    names = [s.get("name", "").split(" (")[0] for s in story.get("sources", [])]
    names = [n for n in names if n][:2]
    return "Source: " + ", ".join(names) if names else "Source: Indian financial media"


def _visual_direction(rank: int, story: dict) -> str:
    """Hint for the image step — one main visual idea per slide."""
    cat = story.get("category", "").lower()
    if "indices" in cat or "macro" in cat:
        return ("Cover slide: large index name + delta chips (Sensex/Nifty), a "
                "single subtle down-trend line; dark navy background.")
    if "company" in cat or "bank" in cat:
        return ("Data-card slide: one company name, a clean stat block, a small "
                "neutral bar showing the day's move; light background.")
    return ("Sector slide: a minimal horizontal sector-performance bar list with "
            "one highlighted bar; light analytical background.")


def run(date: str, research: dict) -> dict:
    stories = research["top_3_stories"]
    plan: list[dict] = []

    for idx, story in enumerate(stories, start=1):
        slide = {
            "slide": idx,
            "story_rank": story.get("rank", idx),
            "headline": _short(story["headline"], 64),
            "subtitle": _short(story["what_happened"], 120),
            "bullets": _bullets_for(story),
            "takeaway": _short(story["why_it_matters"], 130),
            "visual_direction": _visual_direction(idx, story),
            "source_footer": _source_footer(story),
            "footer_brand": f"{BRAND_NAME} · {BRAND_SITE}",
        }
        plan.append(slide)

    payload = {"date": date, "carousel_plan": plan}

    schemas.validate_content_plan(payload)
    comp = compliance.evaluate(payload)
    payload["_compliance"] = {"ok": comp.ok, "violations": comp.violations,
                              "score": comp.score}

    state.save_artifact(date, "content_plan", payload)
    return payload
