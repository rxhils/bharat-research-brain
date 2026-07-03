"""Agent — Trendscout (Maven Reels Newsroom). Local, free, deterministic.

Studies the STRUCTURAL patterns that make finance/news Reels perform, and how to
apply them to Maven — before any generation. It extracts principles, it does not
copy any creator's footage or layout. Writes trendscout.json.

The patterns are a curated, editable knowledge base (retention research +
short-form finance conventions), lightly tailored to the selected story's
footage world so the guidance is concrete, not generic.
"""
from __future__ import annotations

from . import state
from .step_location_scout import classify

# Structural winning patterns (principles, not copies).
_PATTERNS = [
    {"pattern": "First frame IS the hook — a real-world visual + 3–5 word centered line in <0.5s",
     "why_it_works": "Instagram is fast-scroll; the first second is the main retention cliff.",
     "how_to_apply_to_maven": "Open on a premium real-world finance shot with a bold centered hook, never a slow intro."},
    {"pattern": "One idea, taught fast (15–22s), three facts max",
     "why_it_works": "Single-takeaway Reels get saved; lectures get skipped.",
     "how_to_apply_to_maven": "Structure: hook → what → why → why-it-matters → Maven takeaway. No filler."},
    {"pattern": "Real-world footage over abstract charts",
     "why_it_works": "Real environments read as credible media; generic dashboards read as AI slop.",
     "how_to_apply_to_maven": "Use the Location Scout footage world; charts only as brief abstract accents."},
    {"pattern": "Pattern interrupt every 1.5–2.5s (new shot / motion / text beat)",
     "why_it_works": "Fresh visual information resets attention and holds retention.",
     "how_to_apply_to_maven": "5–7 shots, 2–4s each; a text/motion beat on every shot."},
    {"pattern": "Centered kinetic text, one underlined key word per screen",
     "why_it_works": "Designed typography reads premium; auto-caption dumps read cheap.",
     "how_to_apply_to_maven": "Big centered hook + phrase cards + short subtitles, teal highlight, no thick outline."},
    {"pattern": "Voice and on-screen text reinforce, never fight",
     "why_it_works": "Clear audio-visual alignment aids comprehension and save-rate.",
     "how_to_apply_to_maven": "Hook card = spoken hook; subtitles match the voice; cards summarize."},
    {"pattern": "Concrete, sourced specifics beat vague hype",
     "why_it_works": "Real numbers/sectors build trust; hype triggers scepticism.",
     "how_to_apply_to_maven": "Name the sector/level (sourced), never 'this stock will explode'."},
    {"pattern": "Branded, calm end card with a soft CTA",
     "why_it_works": "A premium close earns the follow without feeling salesy.",
     "how_to_apply_to_maven": "Maven end card: 'Understand the market with Maven', subtle, centered."},
]

_AI_SLOP_TRAPS = [
    "abstract purple/teal dashboards as every scene",
    "fake readable text, tickers, numbers or company logos baked into the video",
    "cartoon bull/bear or meme overlays",
    "white subtitles with a thick black outline (auto-caption look)",
    "slow intro / 'here's what investors missed today' generic opener",
    "too much text on screen at once",
    "footage unrelated to the actual news story",
    "no clear single teaching point",
]

# footage world -> concrete visual style + hook style nudge
_WORLD_NUDGE = {
    "banking_financial_system": ("realistic banking/finance environments; the index vs the banking engine underneath",
                                 "surface-vs-underneath contrast hook"),
    "policy_institutional": ("institutional, official-but-not-fake-logo world; one signal flowing through the system",
                             "one-signal-many-effects hook"),
    "sector_broll": ("that sector's real world (server room / grid / line / lab)",
                     "one-sector-moved-the-market hook"),
    "market_stress": ("cinematic low-key tension, investor watching a screen",
                      "the-calm-was-not-real hook"),
    "market_rally": ("bright confident trading floor, green accents",
                     "what-drove-the-move hook"),
    "investor_phone_pov": ("relatable investor POV, phone with blurred UI",
                           "don't-just-watch-the-index hook"),
    "finance_newsroom": ("premium finance newsroom, analyst desk, screen wall",
                         "the-index-hid-the-real-story hook"),
}


def run(date: str, *, story: dict | None = None) -> dict:
    story = story or {}
    world = classify(story)
    visual, hook_nudge = _WORLD_NUDGE.get(world, _WORLD_NUDGE["finance_newsroom"])
    payload = {
        "date": date,
        "footage_world_detected": world,
        "winning_patterns": _PATTERNS,
        "ai_slop_traps": _AI_SLOP_TRAPS,
        "recommended_reel_structure": "hook (0–2s) → what happened (2–6s) → why (6–12s) → "
                                      "why it matters (12–18s) → Maven takeaway (18–22s)",
        "recommended_hook_style": f"short, centered, bold, story-specific — {hook_nudge}; "
                                  "never a generic 'market update today' line",
        "recommended_visual_style": f"realistic premium finance media — {visual}; "
                                    "abstract charts only as brief accents, never the whole reel",
        "recommended_text_style": "centered kinetic typography, one underlined key word per screen, "
                                  "teal highlight, no thick outline",
        "recommended_pacing": "5–7 shots, 2–4s each, a pattern interrupt on every shot",
        "save_share_reason": "teaches one useful, sourced market idea fast and looks like premium "
                             "finance media — worth saving and sending to a friend who invests",
    }
    state.save_artifact(date, "trendscout", payload)
    return payload
