"""Central configuration for the Maven Instagram carousel pipeline.

Single source of truth for brand strings, paths, thresholds, model IDs, and the
compliance word lists. No magic numbers anywhere else in the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------
BRAND_NAME = "Maven"
BRAND_HANDLE = "@try.maven"
BRAND_SITE = "trymaven.in"
BRAND_TAGLINE = "Clean Indian market research."

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "maven_instagram"
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def run_date(now: datetime | None = None) -> str:
    """Return today's date in IST as YYYY-MM-DD (the run partition key)."""
    return (now or datetime.now(IST)).strftime("%Y-%m-%d")


def run_dir(date: str | None = None) -> Path:
    """Directory holding every artifact for one day's run."""
    return OUTPUT_ROOT / (date or run_date())


# Per-step artifact filenames (saved as JSON inside run_dir).
ARTIFACTS = {
    "research": "01_research.json",
    "content_plan": "02_content_plan.json",
    "creative": "03_creative_direction.json",
    "images": "04_images.json",
    "caption": "05_caption.json",
    "hashtags": "06_hashtags.json",
    "quality": "07_quality_check.json",
    "publish": "08_publish.json",
    "story": "09_story_video.json",
    "story_publish": "10_story_publish.json",
    "state": "_state.json",
    "final": "_final_output.json",
}

SLIDE_FILENAMES = ["slide_1.png", "slide_2.png", "slide_3.png"]
SLIDE_JPEG_FILENAMES = ["slide_1.jpg", "slide_2.jpg", "slide_3.jpg"]

# ---------------------------------------------------------------------------
# Research thresholds (Step 1)
# ---------------------------------------------------------------------------
MIN_IMPORTANCE_SCORE = 7  # 1..10
MIN_CONFIDENCE_SCORE = 8  # 1..10
TARGET_STORY_COUNT = 3

# ---------------------------------------------------------------------------
# Image generation (Step 4) — Higgsfield MCP
# ---------------------------------------------------------------------------
# NanoBanana == the `nano_banana_pro` model inside Higgsfield. Best for
# text/diagrams/4K, which is exactly what a typography-heavy finance carousel
# needs. `soul_2` is the fallback for a more editorial/photographic look.
IMAGE_MODEL_PRIMARY = "nano_banana_pro"
IMAGE_MODEL_FALLBACK = "soul_2"
IMAGE_ASPECT_RATIO = "4:5"          # Instagram portrait carousel
IMAGE_TARGET_W = 1080
IMAGE_TARGET_H = 1350
IMAGE_MAX_BYTES = 8 * 1024 * 1024   # Instagram hard limit: 8 MB
IMAGE_JPEG_QUALITY = 90
IMAGE_GEN_MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Instagram publishing (Step 8) — Composio MCP, Instagram Graph API
# ---------------------------------------------------------------------------
IG_ACCOUNT_USERNAME = "try.maven"
IG_USER_ID = "me"                   # Composio resolves the authed business acct
IG_CAROUSEL_MIN = 2
IG_CAROUSEL_MAX = 10
IG_CAPTION_MAX = 2200
IG_MAX_HASHTAGS = 30
PUBLISH_MAX_RETRIES = 3
PUBLISH_RETRY_COOLDOWN_S = 20       # Graph API error 9/9007 backoff

COMPOSIO_TOOLS = {
    "user_info": "INSTAGRAM_GET_USER_INFO",
    "publish_limit": "INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT",
    "create_child": "INSTAGRAM_POST_IG_USER_MEDIA",
    "create_carousel": "INSTAGRAM_CREATE_CAROUSEL_CONTAINER",
    "publish": "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH",
    "get_media": "INSTAGRAM_GET_IG_MEDIA",
}

# ---------------------------------------------------------------------------
# Quality gate (Step 7)
# ---------------------------------------------------------------------------
QUALITY_GATES = {"content": 90, "design": 90, "compliance": 95}

# ---------------------------------------------------------------------------
# Compliance — content must be educational, never advisory
# ---------------------------------------------------------------------------
BANNED_PHRASES = [
    "buy", "sell", "hold", "multibagger", "guaranteed", "sure-shot",
    "sure shot", "tip", "recommendation", "must buy", "price target",
    "target price", "jackpot", "double your money",
]
# Words that look banned but are legitimate in finance context. Compliance
# scanning uses word boundaries and skips these substrings.
COMPLIANCE_ALLOWLIST = [
    "buyback", "buy-back", "holding", "holdings", "stakeholder",
    "shareholder", "household", "selling pressure", "sell-off", "selloff",
    # "hold up"/"held up" = withstand, not advisory "hold". Same for "hold on".
    "hold up", "held up", "holds up", "holding up", "hold on",
]

DISCLAIMER = (
    "Educational content only. Not investment advice. "
    "Maven is not a SEBI-registered adviser or research analyst."
)


@dataclass
class BrandContext:
    """Bundle handed to steps that render brand strings."""
    name: str = BRAND_NAME
    handle: str = BRAND_HANDLE
    site: str = BRAND_SITE
    tagline: str = BRAND_TAGLINE
    disclaimer: str = DISCLAIMER
    palette: list[str] = field(default_factory=lambda: [
        "#0B1220",  # near-black navy (primary dark bg)
        "#0F1B2D",  # dark navy
        "#FFFFFF",  # white
        "#9AA7B8",  # cool grey
        "#1FB6A6",  # teal accent
        "#2F6FED",  # blue accent
        "#27C281",  # green (up)
        "#F2994A",  # orange (use sparingly)
    ])
