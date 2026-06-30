"""The Newsroom node registry — premium UI names mapped to the REAL architecture.

This mirrors the actual Claude Code pipeline classes (A-G), not a marketing
version. Every node declares:
  - component_class: A | B | C | Cprime | D | E | F | G
  - component_type : human label (LLM Agent / Python Module / MCP Service /
                     Guardrail / Quality Gate / Publisher / State System /
                     Scheduler / LLM Runtime)
  - intelligent    : true ONLY for genuine LLM reasoning (Market Sentinel,
                     Claude Conductor). Everything else is deterministic / a
                     service / a courier — and the inspector says so.
  - external       : drives the purple node colour (MCP / external API).
  - in_graph       : appears in the main linear pipeline graph.
"""
from __future__ import annotations

CLASS_LABELS = {
    "A": "Class A · LLM Research Agent",
    "B": "Class B · Deterministic Python Module",
    "C": "Class C · External Generative MCP",
    "Cprime": "Class C′ · Local DSP / Video",
    "D": "Class D · External API Courier",
    "E": "Class E · Orchestrator / State",
    "F": "Class F · Claude Code Conductor",
    "G": "Class G · Scheduled Run",
}

NODES: list[dict] = [
    {"node_id": "closing_bell", "name": "Closing Bell", "order": 0,
     "component_class": "G", "component_type": "Scheduler", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "5 PM IST cron / manual trigger",
     "role": "Starts the post-market workflow after the Indian market close."},
    {"node_id": "claude_conductor", "name": "Claude Conductor", "order": 1,
     "component_class": "F", "component_type": "LLM Runtime", "intelligent": True,
     "external": False, "in_graph": True,
     "actual_component": "Claude Code runtime",
     "role": "Bridges Python, Higgsfield MCP, Composio MCP, visual QA and publish."},
    {"node_id": "market_sentinel", "name": "Market Sentinel", "order": 2,
     "component_class": "A", "component_type": "LLM Agent", "intelligent": True,
     "external": False, "in_graph": True,
     "actual_component": "IndianMarketResearchAgent (web-enabled LLM)",
     "role": "Finds and verifies the top Indian market-moving stories."},
    {"node_id": "conviction_gate", "name": "Conviction Gate", "order": 3,
     "component_class": "B", "component_type": "Guardrail", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step1_research.py",
     "role": "Validates research; keeps importance>=7 & confidence>=8; top 3."},
    {"node_id": "slide_architect", "name": "Slide Architect", "order": 4,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step2_content_plan.py",
     "role": "Converts the top 3 stories into a 3-slide carousel plan."},
    {"node_id": "art_director", "name": "Art Director", "order": 5,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step3_creative_direction.py",
     "role": "Chooses the design system (Dark / White / Hybrid)."},
    {"node_id": "prompt_forge", "name": "Prompt Forge", "order": 6,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step4_images.build_prompt()",
     "role": "Builds unique prompts + variation + negative prompts per slide."},
    {"node_id": "nano_studio", "name": "Nano Studio", "order": 7,
     "component_class": "C", "component_type": "MCP Service", "intelligent": False,
     "external": True, "in_graph": True,
     "actual_component": "Higgsfield MCP · generate_image (nano_banana_pro)",
     "role": "Generates the three carousel images."},
    {"node_id": "pixel_lab", "name": "Pixel Lab", "order": 8,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step4_images.postprocess() (Pillow)",
     "role": "Crops/convert/compress to 1080x1350 JPEG under IG limits."},
    {"node_id": "caption_desk", "name": "Caption Desk", "order": 9,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step5_caption.py",
     "role": "Hook, intro, summary, Maven CTA, disclaimer."},
    {"node_id": "hashtag_desk", "name": "Hashtag Desk", "order": 10,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step6_hashtags.py",
     "role": "Relevant hashtags, capped and de-duplicated."},
    {"node_id": "compliance_shield", "name": "Compliance Shield", "order": 11,
     "component_class": "B", "component_type": "Guardrail", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "compliance.py",
     "role": "Blocks advice, hype, fake claims and unsafe wording."},
    {"node_id": "meta_auditor", "name": "Meta Auditor", "order": 12,
     "component_class": "B", "component_type": "Quality Gate", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step7_quality_check.py",
     "role": "Scores content/design/compliance; blocks publish on fail."},
    {"node_id": "publish_gate", "name": "Publish Gate", "order": 13,
     "component_class": "B", "component_type": "Python Module", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "step8_publish.preflight",
     "role": "Confirms publish allowed; validates assets; requires approval."},
    {"node_id": "ig_courier", "name": "IG Courier", "order": 14,
     "component_class": "D", "component_type": "Publisher", "intelligent": False,
     "external": True, "in_graph": True,
     "actual_component": "Composio MCP -> Instagram Graph API",
     "role": "Uploads media, creates carousel, publishes, returns permalink."},
    {"node_id": "run_vault", "name": "Run Vault", "order": 15,
     "component_class": "E", "component_type": "State System", "intelligent": False,
     "external": False, "in_graph": True,
     "actual_component": "state.py / artifact storage",
     "role": "Stores JSON outputs, logs, images, state and run history."},
    # Optional side branch — not in the main linear graph.
    {"node_id": "story_studio", "name": "Story Studio", "order": 16,
     "component_class": "Cprime", "component_type": "Python Module",
     "intelligent": False, "external": False, "in_graph": False,
     "actual_component": "step9_story_video.py (ffmpeg)",
     "role": "Optional 9:16 Story video with original ambient music."},
]

NODES_BY_ID = {n["node_id"]: n for n in NODES}
PIPELINE_ORDER = [n["node_id"] for n in sorted(NODES, key=lambda n: n["order"])]
GRAPH_ORDER = [n["node_id"] for n in sorted(NODES, key=lambda n: n["order"])
               if n["in_graph"]]

# Back-compat aliases (older modules import these names).
AGENTS = NODES
AGENTS_BY_ID = NODES_BY_ID
AGENT_TYPE_LABELS = {
    "A": "LLM Agent", "B": "Deterministic Module", "C": "External MCP Service",
    "Cprime": "Local DSP / Video", "D": "External API Courier",
    "E": "State System", "F": "Claude Conductor", "G": "Scheduler",
}


def node(node_id: str) -> dict:
    return NODES_BY_ID.get(node_id, {
        "node_id": node_id, "name": node_id, "component_class": "B",
        "component_type": "Python Module", "intelligent": False,
        "external": False, "in_graph": False, "actual_component": "", "role": "",
    })


# Alias kept for modules that call agent()/get_agent().
def agent(node_id: str) -> dict:
    return node(node_id)
