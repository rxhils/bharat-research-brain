"""Visual motif system — reusable finance graphics for photo-reel slides.

Every motif is drawn LOCALLY by the compositor (deterministic PIL shapes,
never AI text/numbers) and doubles as the theme brief for the optional
Higgsfield background. Motifs are what make a valuation story LOOK like a
valuation story instead of a generic navy card.
"""
from __future__ import annotations

MOTIFS: dict[str, dict] = {
    "valuation_gauge": {
        "id": "valuation_gauge",
        "name": "Valuation Gauge",
        "best_for": ["pe", "p/e", "valuation", "expensive", "cheap", "premium",
                     "discount", "overvalued", "undervalued", "ratio"],
        "visual_elements": ["semicircle gauge", "needle in hot zone",
                            "floating metric card", "tick marks"],
        "layout_hint": "gauge dominates the lower half of the hook slide",
        "higgsfield_background_prompt": (
            "abstract premium valuation gauge glowing softly, subtle market-grid "
            "depth, floating clean finance cards without readable text"),
        "compositor_shapes": ["gauge_arc", "needle", "metric_card", "ticks"],
        "avoid": ["real PE numbers unless verified", "buy/sell zones"],
    },
    "sector_heatmap": {
        "id": "sector_heatmap",
        "name": "Sector Heatmap Blocks",
        "best_for": ["sector", "mid-cap", "midcap", "smallcap", "stocks",
                     "gainers", "losers", "heatmap", "breadth"],
        "visual_elements": ["grid of rounded blocks", "varying intensity",
                            "one highlighted block"],
        "layout_hint": "block grid as the story visual, one block accented",
        "higgsfield_background_prompt": (
            "abstract sector heatmap of softly glowing rounded blocks in varying "
            "intensity, no text inside blocks, editorial depth"),
        "compositor_shapes": ["block_grid", "accent_block"],
        "avoid": ["company names", "tickers", "red/green profit coloring"],
    },
    "index_sector_split": {
        "id": "index_sector_split",
        "name": "Index vs Sector Split",
        "best_for": ["nifty", "sensex", "index", "hid", "diverge", "breadth",
                     "underperform", "outperform"],
        "visual_elements": ["one wide index bar", "smaller sector bars",
                            "split divider line"],
        "layout_hint": "index layer above, sector layers fanned below",
        "higgsfield_background_prompt": (
            "layered abstract index line above smaller diverging sector layers, "
            "clean split composition, subtle depth"),
        "compositor_shapes": ["index_bar", "sector_bars", "divider"],
        "avoid": ["fake index values", "candlesticks with numbers"],
    },
    "policy_pulse": {
        "id": "policy_pulse",
        "name": "Policy Signal Pulse",
        "best_for": ["rbi", "sebi", "government", "policy", "rate", "repo",
                     "regulation", "budget", "gst", "circular"],
        "visual_elements": ["institution pillar block", "radiating pulse rings",
                            "signal dot"],
        "layout_hint": "pillar left, pulse rings radiating toward content",
        "higgsfield_background_prompt": (
            "minimal institutional pillar silhouette with soft radiating signal "
            "rings, calm authoritative editorial mood"),
        "compositor_shapes": ["pillar", "pulse_rings", "signal_dot"],
        "avoid": ["official emblems", "flags", "real logos"],
    },
    "ai_tech_grid": {
        "id": "ai_tech_grid",
        "name": "AI / Tech Grid",
        "best_for": ["ai", "artificial intelligence", "it ", "tech", "data",
                     "software", "digital", "chip", "semiconductor"],
        "visual_elements": ["node grid", "connecting lines", "one lit node",
                            "circuit hints"],
        "layout_hint": "node grid as backdrop texture plus one focal cluster",
        "higgsfield_background_prompt": (
            "abstract glowing node grid with fine connecting lines, one focal "
            "lit cluster, premium tech-editorial depth"),
        "compositor_shapes": ["node_grid", "links", "focus_node"],
        "avoid": ["binary text", "code snippets", "robot cliches"],
    },
    "market_mood": {
        "id": "market_mood",
        "name": "Market Mood Meter",
        "best_for": ["rally", "fall", "crash", "surge", "sentiment", "fear",
                     "record", "high", "low", "volatile", "swing"],
        "visual_elements": ["horizontal mood meter", "marker", "wave line"],
        "layout_hint": "mood meter under the headline, wave texture behind",
        "higgsfield_background_prompt": (
            "sweeping abstract market wave line with a calm-to-intense gradient "
            "meter, cinematic editorial depth"),
        "compositor_shapes": ["meter_track", "meter_marker", "wave_line"],
        "avoid": ["fear/greed labels with numbers", "emoji"],
    },
    "retail_lens": {
        "id": "retail_lens",
        "name": "Retail Investor Lens",
        "best_for": ["investor", "retail", "you", "portfolio", "sip",
                     "beginner", "learn", "track", "watch"],
        "visual_elements": ["phone silhouette", "market layers behind",
                            "focus ring"],
        "layout_hint": "phone silhouette right, insight text left",
        "higgsfield_background_prompt": (
            "sleek phone silhouette with abstract market layers glowing behind "
            "it, focus ring highlight, premium fintech mood"),
        "compositor_shapes": ["phone", "market_layers", "focus_ring"],
        "avoid": ["app screenshots", "readable UI text", "brand phones"],
    },
    "cause_effect_flow": {
        "id": "cause_effect_flow",
        "name": "Cause → Effect Flow",
        "best_for": ["why", "because", "driven", "led", "after", "impact",
                     "mechanism", "reason"],
        "visual_elements": ["three flow cards", "connecting arrows",
                            "outcome card accent"],
        "layout_hint": "three cards left→right with arrows, outcome accented",
        "higgsfield_background_prompt": (
            "three abstract glass panels connected by subtle light arrows, "
            "clean explanatory flow composition"),
        "compositor_shapes": ["flow_cards", "arrows", "outcome_accent"],
        "avoid": ["fake percentages on cards", "more than 4 steps"],
    },
}

# Per-role defaults: slide 3 is always mechanism, slide 4 is always the
# investor lens; slides 1-2 pick the STORY motif; slide 5 stays brand-clean.
ROLE_MOTIF_POLICY = {
    "hook": "story",
    "what_happened": "story",
    "why_it_happened": "cause_effect_flow",
    "why_it_matters": "retail_lens",
    "maven_takeaway": "brand_card",   # no heavy motif — premium end-card
}

# Cause-chain chip labels per theme (deterministic, no fake numbers).
CAUSE_CHAINS = {
    "Banking": ["Credit flows", "Margins", "Rate cues"],
    "IT & AI": ["Deal wins", "AI demand", "Global cues"],
    "Auto": ["Volumes", "Input costs", "Demand cues"],
    "Energy": ["Crude moves", "Refining", "Policy cues"],
    "Pharma": ["Approvals", "Exports", "Pricing cues"],
    "FMCG": ["Rural demand", "Margins", "Input costs"],
    "Metals": ["Global prices", "Demand", "Supply cues"],
    "Realty & Infra": ["Rates", "Launches", "Capex cues"],
    "Markets & Index": ["Flows", "Earnings", "Policy cues"],
    "Policy & Macro": ["Data", "Decision", "Market read"],
    "IPO & Deals": ["Pricing", "Demand", "Listing cues"],
}


def story_motif(story: dict) -> str:
    """Pick the motif that best matches the story text (deterministic)."""
    text = f" {story.get('headline', '')} {story.get('summary', '')} ".lower()
    best, best_hits = "market_mood", 0
    for mid, m in MOTIFS.items():
        hits = sum(1 for kw in m["best_for"] if kw in text)
        if hits > best_hits:
            best, best_hits = mid, hits
    return best


def motif_for(role: str, story: dict, override: str | None = None) -> str:
    """Motif id for a slide role (honours an operator override)."""
    if override and override in MOTIFS:
        return override
    policy = ROLE_MOTIF_POLICY.get(role, "story")
    if policy == "story":
        return story_motif(story)
    if policy == "brand_card":
        return "brand_card"
    return policy


def cause_chain(story: dict) -> list[str]:
    return CAUSE_CHAINS.get(story.get("sector_or_theme", ""),
                            CAUSE_CHAINS["Markets & Index"])


def next_motif(current: str) -> str:
    """Cycle to the next motif (for the UI 'Change Motif' button)."""
    ids = list(MOTIFS)
    if current not in ids:
        return ids[0]
    return ids[(ids.index(current) + 1) % len(ids)]
