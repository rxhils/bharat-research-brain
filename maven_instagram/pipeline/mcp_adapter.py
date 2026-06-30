"""MCP execution boundary — documents how the live tool calls happen.

IMPORTANT (architecture honesty): the Higgsfield and Composio MCP servers are
available to the *agent runtime* (Claude Code), not to this Python process. A
bare ``python -m maven_instagram`` run does the deterministic work — research
validation, content/caption/hashtag generation, image post-processing, quality
scoring, payload building — but the two network actions below are performed by
the agent (or by a future DirectApiExecutor wired with your own API keys):

  * image generation  -> Higgsfield MCP  ``generate_image``
  * carousel publish  -> Composio MCP    INSTAGRAM_* tools

This module defines the Executor protocol + a NoopExecutor so the orchestrator
can run end-to-end in "prepare" mode and hand the built payloads to whatever
executor is available.
"""
from __future__ import annotations

from typing import Protocol


# --- Exact MCP call specs, for reference / wiring -------------------------

HIGGSFIELD_GENERATE_IMAGE = {
    "tool": "mcp__<higgsfield>__generate_image",
    "params": {
        "model": "nano_banana_pro",      # == NanoBanana
        "prompt": "<built per-slide prompt>",
        "aspect_ratio": "4:5",
        "count": 1,
    },
    "notes": "Returns a job whose result has a (signed) image URL. Download the "
             "bytes, then run step4_images.postprocess() to get a clean JPEG.",
}

COMPOSIO_PUBLISH_SEQUENCE = [
    "INSTAGRAM_POST_IG_USER_MEDIA  (one per slide, is_carousel_item=true)",
    "INSTAGRAM_CREATE_CAROUSEL_CONTAINER  (children=[child ids], caption=...)",
    "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH  (creation_id=parent id)",
    "INSTAGRAM_GET_IG_MEDIA  (fields=id,permalink) to fetch the post URL",
]

# Instagram fetches images by URL, so slide JPEGs must be at a clean public
# HTTPS URL (no query string). Hosting options handled at publish time:
HOSTING_OPTIONS = {
    "vercel_public": "Copy JPEGs into maven-site/public/ig/<date>/ and deploy; "
                     "served at https://trymaven.in/ig/<date>/slide_N.jpg",
    "composio_file": "Use child_image_files (s3key) via Composio's file upload.",
}


class Executor(Protocol):
    """Anything that can actually run an MCP tool call."""

    def generate_image(self, job: dict) -> dict: ...
    def publish_carousel(self, payloads: dict, image_urls: list[str],
                         caption: str) -> dict: ...


class NoopExecutor:
    """Default executor: does nothing, signals 'agent must run these'."""

    def generate_image(self, job: dict) -> dict:
        return {"executed": False,
                "reason": "no live executor; agent runs Higgsfield generate_image",
                "job": job}

    def publish_carousel(self, payloads: dict, image_urls: list[str],
                         caption: str) -> dict:
        return {"executed": False,
                "reason": "no live executor; agent runs Composio INSTAGRAM_* flow",
                "payloads": payloads}
