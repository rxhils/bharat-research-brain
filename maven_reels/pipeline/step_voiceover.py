"""Step — Backend Voiceover (real TTS or free simulation).

Produces voiceover.mp3 for the reel FROM THE BACKEND, so a simulation run is no
longer unfairly blocked by a missing real voice. Three modes:

  real_tts          — a configured TTS provider (Higgsfield audio today; the
                      structure extends to ElevenLabs / OpenAI) synthesizes the
                      narration. production_ready=True. SPENDS CREDITS — only on
                      an operator-triggered real run.
  local_simulation  — no TTS key (or simulate=True): a free, estimated-duration
                      neutral placeholder track is synthesized with ffmpeg so the
                      reel has a timed audio slot. Clearly marked simulation;
                      production_ready=False. Does NOT fail the pipeline.
  no_voice_preview  — caller wants no VO at all (UI preview). No file written.

The auditor treats simulation VO as preview-OK but not production-ready.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state


def _est_duration(text: str) -> float:
    words = len(str(text).split())
    return max(12.0, min(float(config.REEL_MAX_SECONDS), words / 2.5))


def _simulate(dest: Path, seconds: float) -> None:
    """Free, estimated-duration placeholder track (very low neutral tone) so the
    reel has a real, timed audio slot without any TTS. Never claimed as a voice."""
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found (needed for simulation voiceover)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [exe, "-y", "-f", "lavfi", "-i", f"sine=frequency=180:duration={seconds:.2f}",
         "-af", "volume=0.04", "-c:a", "libmp3lame", "-q:a", "6", str(dest)],
        check=True, capture_output=True, timeout=60)


def run(date: str, *, script_edited: dict, mode: str | None = None,
        simulate: bool | None = None) -> dict:
    from . import capabilities, higgsfield_client as hf  # noqa: PLC0415

    narration = (script_edited.get("narration") or "").strip()
    dest = config.run_dir(date) / "voiceover.mp3"
    seconds = _est_duration(narration)

    # decide mode
    if mode == "no_voice_preview":
        payload = {"voiceover_mode": "no_voice_preview", "voiceover_path": None,
                   "duration": 0, "script_used": narration, "provider": None,
                   "production_ready": False, "notes": "Preview only — no voiceover requested."}
        state.save_artifact(date, "voiceover_v2", payload)
        return payload

    want_real = (not simulate) and (mode == "real_tts" or (mode is None and hf.available()))
    if want_real and hf.available():
        try:
            meta = hf.generate_audio_to_file(narration, dest, model="seed_audio")
            payload = {"voiceover_mode": "real_tts", "voiceover_path": str(dest),
                       "duration": seconds, "script_used": narration,
                       "spoken_text": narration,   # source of truth for on-screen text
                       "provider": "higgsfield", "production_ready": True,
                       "request_id": meta.get("request_id"),
                       "notes": "Real Higgsfield TTS voiceover."}
            state.save_artifact(date, "voiceover_v2", payload)
            return payload
        except Exception as exc:  # real failed → fall back to simulation, honestly
            note = f"Real TTS failed ({str(exc)[:120]}); used simulation placeholder."
    else:
        note = ("Simulation placeholder (no TTS key configured)."
                if not hf.available() else "Simulation placeholder (forced).")

    _simulate(dest, seconds)
    payload = {"voiceover_mode": "local_simulation", "voiceover_path": str(dest),
               "duration": seconds, "script_used": narration, "spoken_text": narration,
               "provider": "ffmpeg_sim", "production_ready": False, "notes": note}
    state.save_artifact(date, "voiceover_v2", payload)
    return payload
