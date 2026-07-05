"""Configuration for the Maven Reels pipeline.

Separate from the carousel pipeline (maven_instagram). Reuses the carousel's
brand + compliance by READ-ONLY import — it never modifies maven_instagram.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Read-only reuse of the carousel brand + disclaimer (import, never modify).
from maven_instagram.pipeline.config import (  # noqa: F401
    BRAND_NAME, BRAND_HANDLE, BRAND_SITE, DISCLAIMER, IST as _IST,
)

IST = ZoneInfo("Asia/Kolkata")

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "maven_reels"
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def run_date(now: datetime | None = None) -> str:
    return (now or datetime.now(IST)).strftime("%Y-%m-%d")


def run_dir(date: str | None = None) -> Path:
    return OUTPUT_ROOT / (date or run_date())


ARTIFACTS = {
    "research": "01_research.json",
    "duplicate_check": "02_duplicate_check.json",
    "viral_fit": "02_viral_fit.json",
    "angle": "03_angle.json",
    "creative_brief": "04_creative_brief.json",
    "hooks": "04_hooks.json",
    "voiceover_v2": "10_voiceover.json",
    "script": "05_script.json",
    "script_edited": "06_script_edited.json",
    "template": "07_template.json",
    "motion_variation": "08_motion_variation.json",
    "storyboard": "07_storyboard.json",
    "asset_picker": "09_asset_picker.json",
    "higgsfield_request": "11_higgsfield_request.json",
    "fresh_video_scenes": "12_fresh_video_scenes.json",   # legacy (folded into scene_generation)
    "renderer_selection": "08_renderer_selection.json",
    "creative_direction": "09_higgsfield_creative_direction.json",
    "shot_plan": "10_higgsfield_shot_plan.json",
    "shot_prompts": "11_higgsfield_prompts.json",
    "scene_model_plan": "10_model_router.json",
    "scene_generation": "12_higgsfield_generation.json",
    "scene_quality": "13_scene_quality.json",
    "text_alignment": "20_text_alignment.json",
    "kinetic_text_plan": "21_kinetic_text_plan.json",
    "text_safe_area": "22_text_safe_area.json",
    "text_animation": "23_text_animation.json",
    "text_quality": "24_text_quality.json",
    "trendscout": "25_trendscout.json",
    "location_scout": "26_location_scout.json",
    "model_routing_plan": "27_model_routing_plan.json",
    "prompt_bible": "28_prompt_bible.json",
    "editor_in_chief": "29_editor_in_chief.json",
    "scene_vision": "30_scene_vision_inspection.json",
    "higgsfield_blueprint": "31_higgsfield_blueprint.json",
    "production_routing": "32_production_routing.json",
    "production_prompts": "33_production_prompts.json",
    "production_result": "34_production_result.json",
    "story_format": "35_story_format.json",
    "format_director": "36_format_director.json",
    "reel_variants": "37_reel_variants.json",
    "hooks_format": "38_hooks_format.json",
    "script_saveable": "39_script_saveable.json",
    "visual_pack": "40_visual_pack.json",
    "popup_plan": "41_popup_plan.json",
    "watch_through": "42_watch_through.json",
    "visual_taste": "43_visual_taste.json",
    "final_reel": "17_final_reel.json",
    "cost_guard": "cost_guard.json",
    "visual_uniqueness": "10_visual_uniqueness.json",
    "improvement_plan": "improvement_plan.json",
    "feedback": "feedback.json",
    "assets": "08_assets.json",
    "visual_direction": "08_visual_direction.json",
    "scenes": "09_scenes.json",
    "voiceover": "10_voiceover.json",
    "subtitles": "11_captions.json",
    "sound_design": "11_sound_design.json",
    "reel_video": "12_reel_video.json",
    "cover": "13_cover.json",
    "caption": "14_caption.json",
    "hashtags": "14_hashtags.json",
    "compliance": "15_compliance.json",
    "quality": "16_quality.json",
    "publish": "17_publish.json",
    "state": "_state.json",
    "final": "_final_output.json",
}

# ---------------------------------------------------------------------------
# Reel format
# ---------------------------------------------------------------------------
REEL_W, REEL_H = 1080, 1920            # 9:16
REEL_MIN_SECONDS = 15
REEL_MAX_SECONDS = 20
SCENE_MIN, SCENE_MAX = 7, 12
IMAGE_MODEL = "nano_banana_pro"        # Higgsfield stills (NanoBanana)
IMAGE_ASPECT = "9:16"
TTS_MODEL = "text2speech_v2_minimax"   # default; confirm via models_explore(type:'audio')

# ---------------------------------------------------------------------------
# Viral Fit Gate — the most important reel-specific gate
# ---------------------------------------------------------------------------
VIRAL_FIT_DIMS = [
    "importance", "curiosity", "emotional", "simplicity",
    "visual", "shareability", "retail_relevance",
]
# Reels weight scroll-stopping traits above raw importance.
VIRAL_FIT_WEIGHTS = {
    "importance": 1.0, "curiosity": 1.6, "emotional": 1.5, "simplicity": 1.2,
    "visual": 1.5, "shareability": 1.6, "retail_relevance": 1.3,
}
VIRAL_FIT_MIN = 6.0                    # min weighted-average to be reel-worthy

# ---------------------------------------------------------------------------
# Hook Lab — always cover these buckets
# ---------------------------------------------------------------------------
HOOK_BUCKETS = ["curiosity", "shock", "contrarian", "simple",
                "data", "myth", "question"]

# Retention Editor — filler openers that get cut on sight.
FILLER_OPENERS = [
    "today we", "today we're", "today we are", "in this video", "in this reel",
    "let's understand", "let us understand", "let's talk about", "let's dive",
    "we are going to", "we're going to", "hey guys", "what's up",
]

# ---------------------------------------------------------------------------
# Reel Auditor thresholds
# ---------------------------------------------------------------------------
QUALITY_GATES = {"hook": 85, "retention": 85, "visual": 85, "compliance": 95}

# ---------------------------------------------------------------------------
# Instagram Reels publish (Composio)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Cost strategy — Higgsfield is a REUSABLE asset library, not a daily generator.
# Daily runs render with Remotion + existing library assets = ~zero marginal cost.
# ---------------------------------------------------------------------------
def _envbool(name: str, default: bool) -> bool:
    import os
    v = os.getenv(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _envint(name: str, default: int) -> int:
    import os
    v = os.getenv(name)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


ALLOW_PAID_GENERATION = _envbool("ALLOW_PAID_GENERATION", False)
MAX_HIGGSFIELD_GENERATIONS_PER_DAILY_RUN = _envint("MAX_HIGGSFIELD_GENERATIONS_PER_DAILY_RUN", 0)
MAX_HIGGSFIELD_GENERATIONS_WITH_APPROVAL = _envint("MAX_HIGGSFIELD_GENERATIONS_WITH_APPROVAL", 1)
USE_EXISTING_ASSET_LIBRARY = _envbool("USE_EXISTING_ASSET_LIBRARY", True)

# Reusable Higgsfield motion-asset library (checked into the repo, reused daily).
ASSET_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "assets" / "library"
ASSET_LIBRARY_CATEGORIES = [
    "dark_dashboard", "white_data_cards", "banking", "rbi_policy",
    "sector_heatmap", "market_fall", "market_rally", "earnings",
    "company_news", "liquidity", "index_move", "end_cards", "covers",
]

# Remotion Reel templates (scene structure lives in step_template_selector).
REEL_TEMPLATES = [
    "market_move_explainer", "sector_breakdown", "policy_impact",
    "company_shock", "what_investors_missed",
]

# Motion-variation presets (make each daily reel unique with zero new generation).
MOTION_VARIATIONS = {
    "teal_terminal":  {"accent": "#22D3EE", "hook_animation": "scale-pop",  "transition_style": "flash",  "chart_style": "thin-line",   "subtitle_style": "highlight-teal",   "card_style": "slide-up"},
    "green_pulse":    {"accent": "#27C281", "hook_animation": "pulse",      "transition_style": "slide",  "chart_style": "glow-line",   "subtitle_style": "highlight-green",  "card_style": "pop"},
    "white_brief":    {"accent": "#16A34A", "hook_animation": "rise",       "transition_style": "wipe",   "chart_style": "clean-reveal","subtitle_style": "underline",        "card_style": "editorial"},
    "blue_newsroom":  {"accent": "#38BDF8", "hook_animation": "block-in",   "transition_style": "wipe",   "chart_style": "dashboard",   "subtitle_style": "highlight-blue",   "card_style": "panel"},
    "orange_alert":   {"accent": "#F59E0B", "hook_animation": "impact",     "transition_style": "impact", "chart_style": "bold-line",   "subtitle_style": "highlight-amber",  "card_style": "alert"},
}

# ---------------------------------------------------------------------------
# HIGGSFIELD-PRIMARY RENDERER — Higgsfield generates the animated scene clips
# (the actual video); a local ffmpeg assembler stitches them + voiceover +
# music/SFX + burned subtitles into the final reel. Remotion is DEMOTED to an
# explicit fallback (never used silently). Real costs, confirmed 2026-07-02:
#   seed still (nano_banana_pro, 9:16, 1k): 2 credits
#   video clip (seedance1_5, image-to-video, 9:16, 4s): 4.8 credits
#   => ~6.8 credits/shot, ~34-41 credits/reel (5-6 shots). NOT free.
# Paid generation NEVER runs automatically from Claude Code during builds —
# it requires an explicit UI trigger (Run Reel / Regenerate) or operator
# approval, executed by the conductor.
# ---------------------------------------------------------------------------
def _envstr(name: str, default: str) -> str:
    import os
    return (os.getenv(name) or default).strip().lower()


PRIMARY_REEL_RENDERER = _envstr("PRIMARY_REEL_RENDERER", "higgsfield_full_stack")
# --- Higgsfield full-stack production (text/cards/captions via Higgsfield) ---
DISABLE_REMOTION_FOR_REELS = _envbool("DISABLE_REMOTION_FOR_REELS", True)
USE_HIGGSFIELD_TEXT_TOOLS = _envbool("USE_HIGGSFIELD_TEXT_TOOLS", True)
USE_HIGGSFIELD_EDITOR = _envbool("USE_HIGGSFIELD_EDITOR", True)
USE_HIGGSFIELD_MONTAGE = _envbool("USE_HIGGSFIELD_MONTAGE", True)
ALLOW_LOCAL_TEXT_FALLBACK = _envbool("ALLOW_LOCAL_TEXT_FALLBACK", False)
REQUIRE_CREDIT_CONFIRMATION = _envbool("REQUIRE_CREDIT_CONFIRMATION", True)
ALLOW_PRODUCTION_FROM_CLAUDE = _envbool("ALLOW_PRODUCTION_FROM_CLAUDE", False)
ALLOW_REMOTION_FALLBACK = _envbool("ALLOW_REMOTION_FALLBACK", True)
ALLOW_PAID_HIGGSFIELD_FROM_UI = _envbool("ALLOW_PAID_HIGGSFIELD_FROM_UI", True)
ALLOW_PAID_HIGGSFIELD_FROM_CLAUDE_CODE = _envbool("ALLOW_PAID_HIGGSFIELD_FROM_CLAUDE_CODE", False)
MAX_HIGGSFIELD_SCENES_PER_REEL = _envint("MAX_HIGGSFIELD_SCENES_PER_REEL", 6)
TARGET_REEL_DURATION_SECONDS = _envint("TARGET_REEL_DURATION_SECONDS", 18)
HIGGSFIELD_SCENE_DURATION_SECONDS = _envint("HIGGSFIELD_SCENE_DURATION_SECONDS", 3)
REQUIRE_USER_TRIGGER_FOR_PAID_GENERATION = _envbool("REQUIRE_USER_TRIGGER_FOR_PAID_GENERATION", True)
REQUIRE_APPROVAL_BEFORE_PUBLISH = _envbool("REQUIRE_APPROVAL_BEFORE_PUBLISH", True)

# Generation economics (folded in from the retired Fresh Video Mode)
HIGGSFIELD_VIDEO_MODEL = "seedance1_5"
HIGGSFIELD_SEED_MODEL = IMAGE_MODEL            # nano_banana_pro seed still
HIGGSFIELD_GEN_CLIP_SECONDS = 4                # seedance1_5 allowed: 4/8/12; trimmed to ~3s in assembly
HIGGSFIELD_SEED_COST_CREDITS = 2.0             # confirmed via get_cost
HIGGSFIELD_CLIP_COST_CREDITS = 4.8             # confirmed via get_cost
HIGGSFIELD_MAX_CREDITS_PER_REEL = 60           # hard ceiling for a 5-6 shot reel
MAX_REEL_GENERATION_COST = _envint("MAX_REEL_GENERATION_COST", HIGGSFIELD_MAX_CREDITS_PER_REEL)
REQUIRE_COST_CONFIRMATION = _envbool("REQUIRE_COST_CONFIRMATION", True)
# generation method: text_to_video (cheapest, default) | image_seed (adds ~2cr/scene)
HIGGSFIELD_GENERATION_METHOD = _envstr("HIGGSFIELD_GENERATION_METHOD", "text_to_video")

# Legacy aliases (Fresh Video Mode is retired; kept so old artifacts still load)
FRESH_VIDEO_MODE_ENABLED = False
FRESH_VIDEO_MODEL = HIGGSFIELD_VIDEO_MODEL
FRESH_VIDEO_SEED_MODEL = HIGGSFIELD_SEED_MODEL
FRESH_VIDEO_CLIP_DURATION = HIGGSFIELD_GEN_CLIP_SECONDS
FRESH_VIDEO_SEED_COST_CREDITS = HIGGSFIELD_SEED_COST_CREDITS
FRESH_VIDEO_CLIP_COST_CREDITS = HIGGSFIELD_CLIP_COST_CREDITS
FRESH_VIDEO_MAX_CREDITS_PER_REEL = HIGGSFIELD_MAX_CREDITS_PER_REEL

IG_USER_ID = "36492003990443127"       # try.maven business account
COMPOSIO_TOOLS = {
    "create_media": "INSTAGRAM_POST_IG_USER_MEDIA",   # media_type=REELS
    "publish": "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
    "get_media": "INSTAGRAM_GET_IG_MEDIA",
    "insights": "INSTAGRAM_GET_IG_MEDIA_INSIGHTS",
}
