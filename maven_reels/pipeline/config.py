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
    "viral_fit": "02_viral_fit.json",
    "angle": "03_angle.json",
    "hooks": "04_hooks.json",
    "script": "05_script.json",
    "script_edited": "06_script_edited.json",
    "storyboard": "07_storyboard.json",
    "assets": "08_assets.json",
    "visual_direction": "08_visual_direction.json",
    "scenes": "09_scenes.json",
    "voiceover": "10_voiceover.json",
    "subtitles": "11_captions.json",
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
IG_USER_ID = "36492003990443127"       # try.maven business account
COMPOSIO_TOOLS = {
    "create_media": "INSTAGRAM_POST_IG_USER_MEDIA",   # media_type=REELS
    "publish": "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
    "get_media": "INSTAGRAM_GET_IG_MEDIA",
    "insights": "INSTAGRAM_GET_IG_MEDIA_INSIGHTS",
}
