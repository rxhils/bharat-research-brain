"""Step — Renderer Selector.

Decides HOW this reel gets rendered. Default: higgsfield_primary — Higgsfield
generates the animated scene clips (the actual video) and the local Final Reel
Assembler (ffmpeg) stitches/finishes. Remotion is kept ONLY as an explicit
fallback; it is never chosen silently. simulation_only is for UI demos and
mock-clip testing (zero cost).
"""
from __future__ import annotations

from . import config, state

RENDERERS = ("higgsfield_primary", "remotion_fallback", "simulation_only")


def run(date: str, *, requested: str | None = None,
        higgsfield_available: bool = True) -> dict:
    # any higgsfield* value (incl. higgsfield_full_stack) => Higgsfield path;
    # Remotion is never the default while DISABLE_REMOTION_FOR_REELS is set.
    default = ("higgsfield_primary"
               if (str(config.PRIMARY_REEL_RENDERER).startswith("higgsfield")
                   or config.DISABLE_REMOTION_FOR_REELS)
               else "remotion_fallback")
    renderer = requested if requested in RENDERERS else default

    reason = "User requested Higgsfield animated video generation as primary renderer."
    if requested == "remotion_fallback":
        reason = "Remotion fallback explicitly selected by the operator."
    elif requested == "simulation_only":
        reason = "Simulation mode explicitly selected (no paid generation)."
    elif renderer == "higgsfield_primary" and not higgsfield_available:
        renderer = "simulation_only"
        reason = ("Higgsfield MCP unavailable from this runtime — falling to "
                  "simulation_only. Paid generation runs via the Claude Code "
                  "conductor after the UI trigger.")

    payload = {
        "date": date,
        "renderer": renderer,
        "reason": reason,
        "fallback_available": config.ALLOW_REMOTION_FALLBACK,
        "paid_generation_required": renderer == "higgsfield_primary",
        "requires_user_trigger": config.REQUIRE_USER_TRIGGER_FOR_PAID_GENERATION,
        "options": list(RENDERERS),
    }
    state.save_artifact(date, "renderer_selection", payload)
    return payload
