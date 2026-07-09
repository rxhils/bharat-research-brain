"""Photo-slides node registry — the 10 native photo-Reel agents.

The honest map of the `maven_reels/photo_slides` pipeline (the zero-credit
5-image native photo Reel), mirroring the shape of `registry.NODES` so the same
graph UI, event bus and inspector work unchanged. Node ids match the photo-slides
stage keys (`orchestrator.PIPELINE_STAGES`). This pipeline is fully local/
deterministic — no LLM, no external MCP node — so nothing is marked
`intelligent` or `external`.
"""
from __future__ import annotations

from .registry import CLASS_LABELS  # reuse the shared class-label legend

__all__ = [
    "CLASS_LABELS", "PHOTO_NODES", "NODES_BY_ID_PHOTO", "GRAPH_ORDER_PHOTO",
    "photo_node",
]

PHOTO_NODES: list[dict] = [
    {"node_id": "market_radar", "name": "Market Radar", "order": 0,
     "component_class": "B", "component_type": "Research Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step01_market_radar.py (free RSS/news providers)",
     "role": "Fetches & deterministically scores India market/finance stories for a 5-slide reel."},
    {"node_id": "fact_check", "name": "Fact Check Desk", "order": 1,
     "component_class": "B", "component_type": "Guardrail", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step02_fact_check.py",
     "role": "Rejects unsourced, price-target/hype, single-source-rumour and advisory stories."},
    {"node_id": "story_selector", "name": "Story Selector", "order": 2,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step03_story_selector.py",
     "role": "Ranks verified stories across 7 dimensions and picks the best one."},
    {"node_id": "slide_script", "name": "5-Slide Scriptwriter", "order": 3,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step04_slide_script.py",
     "role": "Writes exactly 5 slides (hook/what/why/matters/takeaway) + caption + hashtags."},
    {"node_id": "slide_design", "name": "Slide Designer", "order": 4,
     "component_class": "Cprime", "component_type": "Local Compositor", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step05_slide_design.py + compositor.py (Pillow)",
     "role": "Plans per-slide motifs and renders 5x 1080x1920 slides locally — text drawn exactly."},
    {"node_id": "design_judge", "name": "Design Judge", "order": 5,
     "component_class": "B", "component_type": "Quality Gate", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step09_slide_design_judge.py",
     "role": "Scores visual richness / layout / readability; flags too-plain slides."},
    {"node_id": "music_scout", "name": "Music Scout", "order": 6,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step07_music_scout.py",
     "role": "Suggests a licensed Instagram audio mood + search terms (never downloads audio)."},
    {"node_id": "viral_audio", "name": "Viral Audio Scout", "order": 7,
     "component_class": "B", "component_type": "Research Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step10_viral_audio_scout.py",
     "role": "Finds a business-safe trending Instagram audio pick for the manual native repost."},
    {"node_id": "export", "name": "Native Exporter", "order": 8,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step06_exporter.py",
     "role": "Exports the 5 PNGs + caption + upload steps as a ZIP for the native photo-Reel."},
    {"node_id": "qa_gate", "name": "QA Gate", "order": 9,
     "component_class": "B", "component_type": "Quality Gate", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step08_qa_gate.py",
     "role": "Deterministic pre-publish gate: facts / design / readability / compliance."},
    {"node_id": "package", "name": "Package", "order": 10,
     "component_class": "E", "component_type": "State System", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "state.py (_package.json + status history)",
     "role": "Aggregates every agent artifact + timestamped status history into the run package."},
]

NODES_BY_ID_PHOTO = {n["node_id"]: n for n in PHOTO_NODES}
GRAPH_ORDER_PHOTO = [n["node_id"] for n in sorted(PHOTO_NODES, key=lambda n: n["order"])
                     if n["in_graph"]]


def photo_node(node_id: str) -> dict:
    return NODES_BY_ID_PHOTO.get(node_id, {
        "node_id": node_id, "name": node_id, "component_class": "B",
        "component_type": "Python Module", "intelligent": False,
        "external": False, "in_graph": False, "actual_component": "", "role": "",
    })
