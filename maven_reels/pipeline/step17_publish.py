"""Step 17 — Publish Gate + Reels Courier.

Preflight (quality gate + approval + real reel.mp4) then the Composio Instagram
Reels publish payloads (media_type=REELS). The MCP calls run in the conductor;
this builds the exact payloads and records the real result (never fakes it).
"""
from __future__ import annotations

from . import state
from .config import COMPOSIO_TOOLS, IG_USER_ID, REEL_MAX_SECONDS


class PublishBlocked(RuntimeError):
    pass


def preflight(quality: dict, confirmed: bool, reel_video: dict | None,
              video_url: str | None) -> None:
    if not quality.get("overall_pass"):
        raise PublishBlocked(f"quality gate not passed: {quality.get('verdict')}")
    if not confirmed:
        raise PublishBlocked("human approval not given")
    if not reel_video or not reel_video.get("reel"):
        raise PublishBlocked("reel.mp4 not built")
    if reel_video.get("seconds", 0) > REEL_MAX_SECONDS + 5:
        raise PublishBlocked("reel too long for a Reel")
    if video_url and ("?" in video_url or not video_url.startswith("https://")):
        raise PublishBlocked("video url must be clean public HTTPS (no query string)")


def build_payloads(date: str, video_url: str, caption: str) -> dict:
    create = {"tool": COMPOSIO_TOOLS["create_media"],
              "arguments": {"ig_user_id": IG_USER_ID, "media_type": "REELS",
                            "video_url": video_url, "caption": caption,
                            "share_to_feed": True}}
    publish = {"tool": COMPOSIO_TOOLS["publish"],
               "arguments": {"ig_user_id": IG_USER_ID,
                             "creation_id": "<creation_id from create>",
                             "max_wait_seconds": 180}}
    verify = {"tool": COMPOSIO_TOOLS["get_media"],
              "arguments": {"ig_media_id": "<published id>",
                            "fields": "id,permalink,media_type,media_product_type"}}
    payload = {"date": date,
               "flow": [{"stage": "create_reel", "calls": [create]},
                        {"stage": "publish", "calls": [publish]},
                        {"stage": "verify", "calls": [verify]}],
               "status": "payloads_built"}
    state.save_artifact(date, "publish", payload)
    return payload


def record_result(date: str, *, status: str, ig_media_id: str | None = None,
                  permalink: str | None = None, notes: str = "") -> dict:
    payload = state.load_artifact(date, "publish") if state.artifact_exists(date, "publish") else {"date": date}
    payload.update({"status": status, "instagram_media_id": ig_media_id,
                    "instagram_post_url": permalink, "notes": notes})
    state.save_artifact(date, "publish", payload)
    return payload
