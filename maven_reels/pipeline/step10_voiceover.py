"""Step 10 — Voice Studio.

Builds the Higgsfield TTS call spec for the reel narration (calm, confident,
clear — not hype). The conductor runs the actual TTS on the Higgsfield MCP and
drops voiceover.mp3 into the run dir; this module records the spec + result.
"""
from __future__ import annotations

from . import config, state
from .config import TTS_MODEL


def build_voiceover_job(date: str, script_edited: dict) -> dict:
    narration = script_edited["narration"]
    payload = {
        "date": date,
        "tts": {
            "tool": "higgsfield.generate_audio",
            "model": TTS_MODEL,
            "voice_hint": "calm, confident, clear, mid-pace male/neutral; not hype",
            "note": "confirm exact voice_id via models_explore(type:'audio')",
            "prompt": narration,
        },
        "narration": narration,
        "target_mp3": str(config.run_dir(date) / "voiceover.mp3"),
        "status": "job_built",
    }
    state.save_artifact(date, "voiceover", payload)
    return payload


def record_voiceover(date: str, *, mp3_path: str, seconds: float | None = None,
                     media_id: str | None = None) -> dict:
    payload = state.load_artifact(date, "voiceover") if state.artifact_exists(date, "voiceover") else {"date": date}
    payload.update({"status": "generated", "mp3": mp3_path,
                    "seconds": seconds, "higgsfield_media_id": media_id})
    state.save_artifact(date, "voiceover", payload)
    return payload
