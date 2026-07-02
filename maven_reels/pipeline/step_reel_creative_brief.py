"""Step — Reel Creative Brief.

Turns the selected market story into a creative direction BEFORE hooks/scripts/
prompts are written, so every Reel is emotionally + visually connected to the
story instead of a generic finance demo. Deterministic (no LLM required, no paid
calls): it classifies the story into a metaphor family and emits a brief the
downstream agents (Hook Lab, Script, Higgsfield Creative Director) read.

Honesty: teaches ONE real market idea, no hype, no buy/sell, no price targets.

Artifact: outputs/maven_reels/{job_id}/04_creative_brief.json
Runs after the viral angle and before hooks/scripts.
"""
from __future__ import annotations

from . import state

# Metaphor families keyed by what the story is really about. Each is a real,
# teachable market mechanic — not decoration.
_METAPHORS = {
    "banks": {
        "name": "Index surface vs banking engine underneath",
        "description": "The index shown as a calm surface that cracks open to reveal "
                       "heavy banking/financial gears driving it from below.",
        "why_it_fits": "High-weight financials move the index more than the index reveals.",
        "risk": "Keep the 'engine' abstract — no fake tickers or logos.",
        "emotion": "the surface looked calm, but banks moved the engine underneath",
        "scroll_stop": "Nifty is not the whole story.",
        "teaching_goal": "Indices move because their highest-weight sectors move underneath.",
        "opening": "A still index line that suddenly splits to show gears turning below.",
        "payoff": "You learn to look under the index at the sectors carrying it.",
    },
    "policy": {
        "name": "Rate signal pulsing through the finance system",
        "description": "A single policy pulse travelling along glowing lines through "
                       "banks, loans and markets, changing each as it passes.",
        "why_it_fits": "One central-bank signal ripples across the whole system.",
        "risk": "Show flow, not text — no fake rate numbers on screen.",
        "emotion": "one policy signal flows through banks, loans, and stocks",
        "scroll_stop": "One signal. Many market effects.",
        "teaching_goal": "A policy decision transmits through liquidity into asset prices.",
        "opening": "A single pulse of light leaving a central node.",
        "payoff": "You learn how one decision reaches many corners of the market.",
    },
    "sector": {
        "name": "One sector tile lighting up the whole board",
        "description": "A dark market board of sector tiles where one tile ignites "
                       "and its glow spreads mood across the rest.",
        "why_it_fits": "A single sector can set the day's tone for the market.",
        "risk": "Abstract heat/glow only — no readable sector labels.",
        "emotion": "one sector quietly changed the market's mood",
        "scroll_stop": "One sector changed the mood.",
        "teaching_goal": "Market breadth and sentiment often turn on one leading sector.",
        "opening": "A grid of dim tiles; one flares first.",
        "payoff": "You learn to spot which sector is leading sentiment.",
    },
    "breadth": {
        "name": "Wide vs narrow — the market's true breadth",
        "description": "Many small columns rising together (broad strength) versus a "
                       "few tall ones carrying a hollow index (narrow strength).",
        "why_it_fits": "Broad-based moves are healthier than index-only moves.",
        "risk": "Columns are abstract — no fake values.",
        "emotion": "the whole market moved together, not just the headline index",
        "scroll_stop": "The real move was underneath.",
        "teaching_goal": "Breadth — how many stocks move — reveals the move's real strength.",
        "opening": "A single tall column, then hundreds rise beside it.",
        "payoff": "You learn to check breadth, not just the index number.",
    },
    "flows": {
        "name": "Liquidity flowing between hands",
        "description": "Streams of light (capital) flowing between abstract pools "
                       "labelled only by shape, changing which pool glows brighter.",
        "why_it_fits": "Fund flows quietly move markets beneath the price.",
        "risk": "No FII/DII numbers on screen — flow is the visual, data is overlaid later.",
        "emotion": "money quietly moved, and the market followed",
        "scroll_stop": "Follow the money, not the noise.",
        "teaching_goal": "Capital flows can drive price before the news explains it.",
        "opening": "Two pools; a stream shifts from one to the other.",
        "payoff": "You learn that flows often lead the price.",
    },
    "default": {
        "name": "The story beneath the number",
        "description": "A single market number that dissolves into the forces that "
                       "actually created it — clean, premium, abstract.",
        "why_it_fits": "Every market move has a cause worth understanding.",
        "risk": "Stay abstract and specific to the day's real driver.",
        "emotion": "there's a real reason behind today's move",
        "scroll_stop": "Markets reacted for one reason.",
        "teaching_goal": "Understanding why the market moved beats memorising that it did.",
        "opening": "A number that breaks apart into moving forces.",
        "payoff": "You leave understanding the driver, not just the headline.",
    },
}

_KEYWORDS = {
    "banks": ["bank", "financial", "hdfc", "icici", "nbfc", "psu bank", "bank nifty"],
    "policy": ["rbi", "repo", "policy", "sebi", "rate", "fed", "inflation", "cpi", "mpc"],
    "sector": ["sector", "auto", "it ", "pharma", "metal", "energy", "fmcg", "realty", "heatmap"],
    "breadth": ["midcap", "smallcap", "broad", "breadth", "advance", "rally", "gainers"],
    "flows": ["fii", "dii", "flow", "inflow", "outflow", "liquidity", "buying", "selling"],
}


def _classify(story: dict) -> str:
    text = " ".join(str(story.get(k, "")) for k in
                    ("headline", "summary", "what_happened", "why_it_matters", "category")).lower()
    sectors = " ".join(story.get("affected_sectors") or []).lower()
    hay = text + " " + sectors
    for family, words in _KEYWORDS.items():
        if any(w in hay for w in words):
            return family
    return "default"


def run(date: str, *, viral_fit: dict, angle: dict, research: dict | None = None,
        recent_briefs: list | None = None) -> dict:
    story = viral_fit["chosen"]["story"]
    family = _classify(story)
    m = _METAPHORS[family]

    # offer 2 metaphor candidates (chosen family + the generic fallback) so the
    # UI can show the choice; the chosen one drives downstream direction.
    candidates = [family] + (["default"] if family != "default" else ["breadth"])
    visual_metaphors = [{
        "name": _METAPHORS[c]["name"],
        "description": _METAPHORS[c]["description"],
        "why_it_fits": _METAPHORS[c]["why_it_fits"],
        "risk": _METAPHORS[c]["risk"],
    } for c in candidates]

    data_mode = (research or {}).get("data_window") or (research or {}).get("data_mode") or "latest_trading_day"

    brief = {
        "viewer_emotion": m["emotion"],
        "scroll_stop_reason": m["scroll_stop"],
        "main_visual_metaphor": m["name"],
        "story_energy": "calm-but-decisive" if family in ("banks", "breadth", "default")
                        else "signal-spreading",
        "teaching_goal": m["teaching_goal"],
        "maven_positioning": "Maven helps retail investors understand WHY the market "
                             "moved — clearly, without hype or tips.",
        "opening_visual_idea": m["opening"],
        "payoff": m["payoff"],
        "avoid": ["hype", "fake drama", "buy/sell/hold", "price targets",
                  "readable fake numbers", "fake tickers", "fearmongering"],
    }
    payload = {
        "job_id": date,
        "data_mode": data_mode,
        "metaphor_family": family,
        "creative_brief": brief,
        "visual_metaphors": visual_metaphors,
        "selected_visual_metaphor": visual_metaphors[0],
        "angle": (angle.get("chosen") or {}).get("angle") if isinstance(angle, dict) else None,
        "status": "completed",
    }
    state.save_artifact(date, "creative_brief", payload)
    return payload
