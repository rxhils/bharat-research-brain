"""Step 8 — Publish the carousel to Instagram via the Composio MCP.

Two-stage Graph API flow (all tool slugs in config.COMPOSIO_TOOLS):
  1. For each slide -> INSTAGRAM_POST_IG_USER_MEDIA with is_carousel_item=true,
     collecting child creation_ids.
  2. INSTAGRAM_CREATE_CAROUSEL_CONTAINER with the ordered child ids + caption.
  3. INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH on the parent creation_id.
  4. INSTAGRAM_GET_IG_MEDIA to fetch the permalink.

This module builds the exact tool payloads and records results; the MCP calls
themselves are executed by the Composio MCP (the agent runtime), since Instagram
needs publicly-fetchable JPEG URLs. The publish is GATED on Step 7 passing and on
explicit human confirmation.
"""
from __future__ import annotations

from . import state
from .config import (COMPOSIO_TOOLS, IG_CAPTION_MAX, IG_CAROUSEL_MAX,
                     IG_CAROUSEL_MIN, IG_USER_ID, PUBLISH_MAX_RETRIES,
                     PUBLISH_RETRY_COOLDOWN_S)


class PublishBlocked(RuntimeError):
    """Raised when a precondition for publishing is not met."""


def preflight(quality: dict, confirmed: bool, image_urls: list[str],
              caption: str) -> None:
    """Hard gate. Raises PublishBlocked unless everything is satisfied."""
    if not quality.get("overall_pass"):
        raise PublishBlocked(f"quality gate not passed: {quality.get('verdict')}")
    if not confirmed:
        raise PublishBlocked("human publish confirmation not given")
    if not (IG_CAROUSEL_MIN <= len(image_urls) <= IG_CAROUSEL_MAX):
        raise PublishBlocked(f"carousel needs {IG_CAROUSEL_MIN}-{IG_CAROUSEL_MAX} items")
    for u in image_urls:
        if not u.startswith("https://"):
            raise PublishBlocked(f"image url not https: {u}")
        if "?" in u:
            raise PublishBlocked(f"image url has query string (IG rejects): {u}")
    if len(caption) > IG_CAPTION_MAX:
        raise PublishBlocked("caption exceeds 2,200 chars")


def build_payloads(date: str, image_urls: list[str], caption: str) -> dict:
    """Return the ordered Composio tool-call payloads for the publish flow."""
    child_calls = [
        {
            "tool": COMPOSIO_TOOLS["create_child"],
            "arguments": {
                "ig_user_id": IG_USER_ID,
                "image_url": url,
                "is_carousel_item": True,
            },
            "slide": i + 1,
        }
        for i, url in enumerate(image_urls)
    ]

    carousel_call = {
        "tool": COMPOSIO_TOOLS["create_carousel"],
        "arguments": {
            "ig_user_id": IG_USER_ID,
            "caption": caption,
            "children": "<ordered list of child creation_ids from step 1>",
        },
    }

    publish_call = {
        "tool": COMPOSIO_TOOLS["publish"],
        "arguments": {
            "ig_user_id": IG_USER_ID,
            "creation_id": "<parent creation_id from carousel container>",
            "max_wait_seconds": 60,
        },
        "retry": {"max": PUBLISH_MAX_RETRIES,
                  "cooldown_s": PUBLISH_RETRY_COOLDOWN_S,
                  "retry_on_error_codes": [9, 9007]},
    }

    verify_call = {
        "tool": COMPOSIO_TOOLS["get_media"],
        "arguments": {"ig_media_id": "<published media id>",
                      "fields": "id,permalink,media_type,timestamp"},
    }

    payload = {
        "date": date,
        "flow": [
            {"stage": "create_children", "calls": child_calls},
            {"stage": "create_carousel", "calls": [carousel_call]},
            {"stage": "publish", "calls": [publish_call]},
            {"stage": "verify_permalink", "calls": [verify_call]},
        ],
        "status": "payloads_built",
    }
    state.save_artifact(date, "publish", payload)
    return payload


def record_result(date: str, *, status: str, ig_media_id: str | None = None,
                  permalink: str | None = None, notes: str = "") -> dict:
    """Persist the outcome of an actual publish attempt (no faking)."""
    payload = state.load_artifact(date, "publish") if state.artifact_exists(date, "publish") else {"date": date}
    payload.update({
        "status": status,  # published | ready_not_published | failed
        "instagram_media_id": ig_media_id,
        "instagram_post_url": permalink,
        "notes": notes,
    })
    state.save_artifact(date, "publish", payload)
    return payload
