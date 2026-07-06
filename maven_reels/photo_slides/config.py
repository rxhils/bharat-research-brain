"""Configuration for the Native Photo Reel Slides framework.

All feature flags are env-overridable; defaults follow the operator spec.
Reuses the carousel brand constants by READ-ONLY import — never modifies
maven_instagram, and never imports the legacy reel_studio flow.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Read-only reuse of brand identity (import, never modify).
from maven_instagram.pipeline.config import (  # noqa: F401
    BRAND_HANDLE,
    BRAND_NAME,
    BRAND_SITE,
)

IST = ZoneInfo("Asia/Kolkata")

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "maven_photo_reels"
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _envbool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _envstr(name: str, default: str) -> str:
    return (os.getenv(name) or default).strip()


# ---------------------------------------------------------------------------
# Feature flags (operator spec, 2026-07-06)
# ---------------------------------------------------------------------------
LEGACY_REELS_UI_ENABLED = _envbool("LEGACY_REELS_UI_ENABLED", False)
LEGACY_REELS_CRON_ENABLED = _envbool("LEGACY_REELS_CRON_ENABLED", False)
REEL_IMAGE_SLIDES_ENABLED = _envbool("REEL_IMAGE_SLIDES_ENABLED", True)
REEL_IMAGE_SLIDES_CRON_ENABLED = _envbool("REEL_IMAGE_SLIDES_CRON_ENABLED", False)
PRIMARY_REELS_MODE = _envstr("PRIMARY_REELS_MODE", "native_photo_reel_manual")
ALLOW_AUTO_REEL_VIDEO_MODE = _envbool("ALLOW_AUTO_REEL_VIDEO_MODE", True)
DEFAULT_REEL_PUBLISH_MODE = _envstr("DEFAULT_REEL_PUBLISH_MODE", "native_photo_reel_manual")
DISABLE_REMOTION_FOR_REELS = _envbool("DISABLE_REMOTION_FOR_REELS", True)
ALLOW_LOCAL_TEXT_FALLBACK = _envbool("ALLOW_LOCAL_TEXT_FALLBACK", True)
REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION = _envbool(
    "REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION", True)

PUBLISH_MODES = ("native_photo_reel_manual", "slideshow_video_reel_auto")

# ---------------------------------------------------------------------------
# Slide format
# ---------------------------------------------------------------------------
SLIDE_W, SLIDE_H = 1080, 1920          # 9:16 vertical
SLIDE_COUNT = 5
TITLE_MAX_WORDS = 7
BODY_MAX_WORDS = 18
SLIDE_ROLES = ["hook", "what_happened", "why_it_happened", "why_it_matters",
               "maven_takeaway"]
SLIDE_ROLE_LABELS = {
    "hook": "Hook", "what_happened": "What happened",
    "why_it_happened": "Why it happened", "why_it_matters": "Why it matters",
    "maven_takeaway": "Maven takeaway",
}

DISCLAIMER = "Educational content only. Not investment advice."

# Compositor style variants (deterministic, zero-credit "redesign style").
STYLE_VARIANTS = {
    "teal_editorial":  {"accent": "#22D3EE", "bg_top": "#0A1220", "bg_bottom": "#101B2D"},
    "green_brief":     {"accent": "#27C281", "bg_top": "#081118", "bg_bottom": "#0E1B22"},
    "blue_newsroom":   {"accent": "#38BDF8", "bg_top": "#0A1020", "bg_bottom": "#0F1830"},
    "amber_alert":     {"accent": "#F2994A", "bg_top": "#120E0A", "bg_bottom": "#1D150E"},
}
DEFAULT_STYLE = "teal_editorial"

# ---------------------------------------------------------------------------
# Artifacts (one JSON per agent, per the spec)
# ---------------------------------------------------------------------------
ARTIFACTS = {
    "market_radar": "01_market_radar.json",
    "fact_check": "02_fact_check.json",
    "story_selector": "03_story_selector.json",
    "slide_script": "04_slide_script.json",
    "slide_design": "05_slide_design.json",
    "design_judge": "09_slide_design_judge.json",
    "export": "06_native_photo_reel_export.json",
    "video_render": "06b_reel_video_render.json",
    "music_scout": "07_music_scout.json",
    "qa_gate": "08_qa_gate.json",
    "package": "_package.json",
}

# ---------------------------------------------------------------------------
# Fact Check Desk — trusted source domains (CLAUDE.md news whitelist)
# ---------------------------------------------------------------------------
TRUSTED_DOMAINS = [
    "pib.gov.in", "rbi.org.in", "sebi.gov.in", "reuters.com", "bloomberg.com",
    "livemint.com", "business-standard.com", "economictimes.indiatimes.com",
    "economictimes.com", "moneycontrol.com", "cnbctv18.com", "thehindu.com",
    "thehindubusinessline.com", "financialexpress.com", "ndtvprofit.com",
    "yahoo.com", "investing.com",
]

# Advisory / hype language that must never appear in slides or captions.
BANNED_TOKENS = [
    "buy", "sell", "tip", "tips", "guaranteed", "sure-shot", "sureshot",
    "multibagger", "recommendation", "jackpot", "target price", "price target",
    "buy now", "must buy", "book profit",
]
# Tokens that look banned but are safe market vocabulary.
BANNED_EXCEPTIONS = ["sell-off", "selloff", "sell-offs", "buyback", "buybacks",
                     "overbought", "oversold"]

RUMOUR_MARKERS = ["reportedly", "rumour", "rumor", "sources say", "unconfirmed",
                  "speculation", "may consider", "likely to announce", "insider"]

# ---------------------------------------------------------------------------
# QA Gate thresholds (spec)
# ---------------------------------------------------------------------------
QA_THRESHOLDS = {"facts": 95, "design": 90, "readability": 92, "overall": 92}

# ---------------------------------------------------------------------------
# Optional slideshow MP4 (auto-publish mode ONLY — never the default)
# ---------------------------------------------------------------------------
VIDEO_SECONDS_PER_SLIDE = 3.6          # 5 slides -> 18s (within 15-25s)
VIDEO_XFADE_SECONDS = 0.4

# ---------------------------------------------------------------------------
# Manual native photo Reel upload steps (shown in UI + export artifact)
# ---------------------------------------------------------------------------
INSTAGRAM_MANUAL_STEPS = [
    "Open Instagram.",
    "Tap +.",
    "Select Reel.",
    "Open gallery.",
    "Tap Select Multiple.",
    "Select the 5 Maven images in order (1 to 5).",
    "Add Instagram music.",
    "Adjust slide durations if needed.",
    "Add caption.",
    "Share as Reel.",
]

PACKAGE_STATUSES = [
    "draft", "needs_review", "approved", "rejected", "revise_requested",
    "exported", "posted_manually", "queued_for_auto_video",
    "published_video_reel", "blocked",
]


def now_ist() -> datetime:
    return datetime.now(IST)


def new_job_id(now: datetime | None = None) -> str:
    """Unique, sortable package id — never reuses/overwrites an old run."""
    n = now or now_ist()
    base = n.strftime("slides-%Y-%m-%d-%H%M")
    seq, jid = 1, None
    while True:
        jid = f"{base}-{seq:03d}"
        if not (OUTPUT_ROOT / jid).exists():
            return jid
        seq += 1
