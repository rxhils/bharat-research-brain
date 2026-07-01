"""Step — Higgsfield Asset Request (OPTIONAL, gated).

Prepares PAID Higgsfield generation call-specs ONLY for library slots the Asset
Picker could not fill. It NEVER executes generation — it returns specs plus a
cost-guard decision. The conductor executes them only after explicit approval and
saves the result into the reusable library for future reuse.
"""
from __future__ import annotations

from . import config, state, step_cost_guard

_STYLE = ("premium financial newsroom, clean modern market dashboard, dark navy/black "
          "background, subtle teal/green/blue accents, elegant data panels, soft chart "
          "grid, refined motion, lots of empty space for text overlays, high-end editorial "
          "finance aesthetic, suitable behind animated typography")
_NEG = ("readable text, fake numbers, logos, buy/sell arrows, candlestick spam, clutter, "
        "cartoon style, cheap AI look, watermark, gibberish text, bull/bear mascots, 3D coins")
_MOTION = "slow cinematic push-in, subtle dashboard parallax, smooth moving data glow, calm premium motion"


def _spec(slot: str, category: str) -> dict:
    return {
        "slot": slot, "target_category": category, "model": config.IMAGE_MODEL,
        "aspect_ratio": config.IMAGE_ASPECT, "resolution": "1080x1920",
        "duration_seconds": "5-8 (loopable if possible)",
        "prompt": (f"Create a premium 9:16 finance motion background plate for Maven, an "
                   f"Indian stock market research brand. Category: {category}. {_STYLE}. "
                   f"Motion: {_MOTION}. No readable text, no fake numbers, no logos."),
        "negative_prompt": _NEG,
        "save_to_library": {"category": category, "reuse": True},
    }


def run(date: str, *, asset_picker: dict, approved: bool = False) -> dict:
    missing = asset_picker.get("missing_assets", [])
    specs = [_spec(m.get("slot", "asset_bg_dark"), m.get("category", "dark_dashboard"))
             for m in missing]
    guard = step_cost_guard.evaluate(date, requested=len(specs), approved=approved)

    payload = {
        "date": date, "needed": len(specs), "requests": specs,
        "cost_guard": guard, "approved": approved,
        "allowed_to_execute": guard["allowed"] and len(specs) > 0,
        "requires_approval": len(specs) > 0 and not guard["allowed"],
        "status": ("no_generation_needed" if not specs
                   else "ready_to_execute" if guard["allowed"]
                   else "requires_approval"),
        "note": ("Reusing the library — no paid generation." if not specs else
                 "Paid Higgsfield generation is gated. The conductor executes these "
                 "specs ONLY after explicit approval, then saves them to the library."),
    }
    state.save_artifact(date, "higgsfield_request", payload)
    return payload
