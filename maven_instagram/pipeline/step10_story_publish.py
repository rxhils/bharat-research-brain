"""Step 10 — Publish the Story video to Instagram via the Composio MCP.

Flow (the agent/executor runs the actual MCP calls):
  1. Upload story.mp4 -> get an Instagram-fetchable ref (Composio file upload
     s3key, or a clean public HTTPS URL with no query string).
  2. INSTAGRAM_POST_IG_USER_MEDIA  media_type=STORIES, video_file/video_url.
  3. INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH  on the returned creation_id.

Notes:
  * Stories accept video; the ambient music is baked into the MP4 (Instagram's
    native music library is NOT available via the publishing API).
  * Video Stories take ~30-120s to process, so publish uses a longer wait.
"""
from __future__ import annotations

from . import state
from .config import COMPOSIO_TOOLS, IG_USER_ID, PUBLISH_MAX_RETRIES


def build_payloads(date: str, video_ref: dict) -> dict:
    """video_ref is either {"video_url": "..."} or
    {"video_file": {"name","mimetype","s3key"}}."""
    create_call = {
        "tool": COMPOSIO_TOOLS["create_child"],   # INSTAGRAM_POST_IG_USER_MEDIA
        "arguments": {
            "ig_user_id": IG_USER_ID,
            "media_type": "STORIES",
            **video_ref,
        },
    }
    publish_call = {
        "tool": COMPOSIO_TOOLS["publish"],
        "arguments": {
            "ig_user_id": IG_USER_ID,
            "creation_id": "<story creation_id from create call>",
            "max_wait_seconds": 180,
        },
        "retry": {"max": PUBLISH_MAX_RETRIES, "retry_on_error_codes": [9, 9007]},
    }
    payload = {
        "date": date,
        "flow": [
            {"stage": "create_story_container", "calls": [create_call]},
            {"stage": "publish_story", "calls": [publish_call]},
        ],
        "status": "payloads_built",
    }
    state.save_artifact(date, "story_publish", payload)
    return payload


def record_result(date: str, *, status: str, ig_media_id: str | None = None,
                  notes: str = "") -> dict:
    payload = (state.load_artifact(date, "story_publish")
               if state.artifact_exists(date, "story_publish") else {"date": date})
    payload.update({
        "status": status,               # published | ready_not_published | failed
        "story_media_id": ig_media_id,
        "notes": notes,
    })
    state.save_artifact(date, "story_publish", payload)
    return payload
