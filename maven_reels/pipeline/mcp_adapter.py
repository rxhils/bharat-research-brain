"""MCP execution boundary for the Reels pipeline (documentation).

Deterministic steps run in this Python process. The external actions run in the
Claude Code conductor (they can reach the MCP servers):
  * Scene stills + Cover  -> Higgsfield MCP  generate_image (nano_banana_pro, 9:16)
  * Voiceover             -> Higgsfield MCP  generate_audio (text2speech_v2_*)
  * Reel publish          -> Composio MCP    INSTAGRAM_POST_IG_USER_MEDIA (media_type=REELS)
  * Reel analytics        -> Composio MCP    INSTAGRAM_GET_IG_MEDIA_INSIGHTS
Local ffmpeg does the Cut Room assembly (step12_cut).
"""
from __future__ import annotations

HIGGSFIELD_SCENE = {"tool": "generate_image", "model": "nano_banana_pro", "aspect_ratio": "9:16"}
HIGGSFIELD_TTS = {"tool": "generate_audio", "model": "text2speech_v2_minimax"}
COMPOSIO_REELS = [
    "INSTAGRAM_POST_IG_USER_MEDIA  (media_type=REELS, video_url=<clean https mp4>, caption)",
    "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH  (creation_id)",
    "INSTAGRAM_GET_IG_MEDIA  (fields=id,permalink)",
]
# Reel MP4 needs a clean public HTTPS URL (no query string). Host via Higgsfield
# media_upload -> CDN url (proven with the carousel Story), then pass as video_url.
