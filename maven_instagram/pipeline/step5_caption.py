"""Step 5 — Instagram caption / description.

Structure: hook → short intro → 3 bullet summary → Maven CTA → disclaimer.
Soft brand promotion, zero advice, under the 2,200-char limit.
"""
from __future__ import annotations

from . import compliance, schemas, state
from .config import BRAND_NAME, BRAND_SITE, DISCLAIMER


def run(date: str, research: dict, content_plan: dict) -> dict:
    stories = research["top_3_stories"]
    slides = content_plan["carousel_plan"]

    hook = "Three things moved Indian markets today — and here's why they matter."
    intro = (
        "A clean, no-noise digest of the session: what happened, in plain "
        "English, with sources. Swipe through 👉"
    )

    bullet_lines = []
    for i, slide in enumerate(slides, start=1):
        bullet_lines.append(f"{i}. {slide['headline']}")
    bullets_block = "\n".join(bullet_lines)

    cta = f"Follow {BRAND_NAME} for clean Indian market research → {BRAND_SITE}"

    caption = (
        f"{hook}\n\n"
        f"{intro}\n\n"
        f"{bullets_block}\n\n"
        f"{cta}\n\n"
        f"{DISCLAIMER}"
    )

    payload = {
        "date": date,
        "caption": caption,
        "description": intro,
        "hook": hook,
        "cta": cta,
        "disclaimer": DISCLAIMER,
        "char_count": len(caption),
    }

    schemas.validate_caption(payload)
    comp = compliance.evaluate(payload, require_disclaimer_in=caption)
    payload["_compliance"] = {"ok": comp.ok, "violations": comp.violations,
                              "score": comp.score}

    state.save_artifact(date, "caption", payload)
    return payload
