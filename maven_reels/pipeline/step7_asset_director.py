"""Step 7 — Asset Director.

Decides the REUSABLE visual assets the motion edit needs (not finished slides).
Backgrounds/assets are generated with little/no text (all important text is
overlaid crisply by the Motion Graphics Engine). Output: 08_assets.json; Scene
Studio then generates these via Higgsfield.
"""
from __future__ import annotations

from . import state

_BASE_NEG = ("cheap AI look, cartoon, meme, random candlestick spam, fake logos, "
            "fake numbers, clutter, unreadable text, gibberish text, watermark, "
            "bull/bear mascots, buy/sell arrows, 3D coins, overdesigned")
_STYLE = ("premium Indian market dashboard, clean dark navy/black, subtle "
          "teal/green/blue accents, soft grid lines, minimal chart lines, high-end "
          "editorial finance aesthetic, lots of negative space, NO readable text")


def run(date: str, storyboard: dict) -> dict:
    kinds = {s["kind"] for s in storyboard["scenes"]}
    assets = [
        {"asset_id": "asset_bg_dark", "type": "background",
         "purpose": "primary dark motion background",
         "prompt": f"Vertical 9:16 premium finance motion-graphic background. {_STYLE}.",
         "negative_prompt": _BASE_NEG,
         "used_in_scenes": [s["scene"] for s in storyboard["scenes"] if s.get("asset") == "asset_bg_dark"]},
        {"asset_id": "asset_bg_panel", "type": "panel",
         "purpose": "subtle dashboard panel backdrop for chips/cards",
         "prompt": f"Vertical 9:16 subtle market dashboard panel backdrop. {_STYLE}.",
         "negative_prompt": _BASE_NEG,
         "used_in_scenes": [s["scene"] for s in storyboard["scenes"] if s.get("asset") == "asset_bg_panel"]},
        {"asset_id": "asset_bg_end", "type": "endcard",
         "purpose": "Maven end-card backdrop",
         "prompt": f"Vertical 9:16 calm Maven end-card backdrop. {_STYLE}.",
         "negative_prompt": _BASE_NEG,
         "used_in_scenes": [s["scene"] for s in storyboard["scenes"] if s.get("asset") == "asset_bg_end"]},
    ]
    payload = {"date": date, "note": "Motion Graphics Engine overlays all text; "
               "assets are clean backgrounds only. v1 renders on the engine's own "
               "animated dark background, so these are optional enhancements.",
               "kinds_in_reel": sorted(kinds), "assets_needed": assets}
    state.save_artifact(date, "assets", payload)
    return payload
