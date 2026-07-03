"""Backend capability checker — can the localhost backend run a full Reel by itself?

The Reels pipeline is designed to run end-to-end from the localhost UI with NO
Claude Code involvement. Whether a *real* animated Reel (paid Higgsfield clips)
can be produced depends only on which provider credentials are configured in the
environment — never on a human being present in a chat.

This module answers, deterministically and for free:
  - which capabilities are live (research, content, higgsfield, tts, composio)
  - whether the backend can run a full reel on its own (real or simulation)
  - EXACTLY what is missing, in operator-actionable language

The UI reads this to decide what to show. It must NEVER say "requires Claude
Code conductor" — if something is missing it names the env var to set in
Settings instead.
"""
from __future__ import annotations

import os
import shutil


def _has(*names: str) -> bool:
    return any((os.getenv(n) or "").strip() for n in names)


def _higgsfield_keys() -> bool:
    """Higgsfield Cloud API auth is `Key KEY_ID:KEY_SECRET`. Accept either the
    split pair or a single combined `KEY_ID:KEY_SECRET` value."""
    if _has("HIGGSFIELD_API_KEY") and _has("HIGGSFIELD_API_SECRET"):
        return True
    combined = (os.getenv("HIGGSFIELD_API_KEY") or "").strip()
    return ":" in combined  # single "id:secret" form


def check() -> dict:
    """Full capability report. Pure/free — reads env + PATH only."""
    from . import higgsfield_client as hf
    from .research_providers.base import available_providers

    ffmpeg_ok = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

    # Research: RSS is zero-key and always present, so research is always live.
    providers = [getattr(p, "NAME", "?") for p in available_providers()]
    research_ok = bool(providers)

    # Content (hook/angle/script/subtitles): the reel engine is deterministic —
    # it does not require an LLM API to produce a reel. An LLM key only enhances
    # it. So content generation is always available from the backend.
    llm_key = _has("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST")
    content_ok = True

    # Higgsfield transport: 'cli' (login, no key) > 'rest' (API key) > 'none'.
    hf_transport = hf.transport()
    higgsfield_ok = hf_transport != "none"
    cli_installed = bool(hf.cli_bin())
    logged_in = hf.cli_logged_in()
    # TTS: real when a real Higgsfield transport (CLI or REST) is live, or a
    # dedicated TTS key is set; otherwise a free local placeholder is used.
    real_tts = higgsfield_ok or _has("ELEVENLABS_API_KEY", "OPENAI_API_KEY")
    tts_ok = True  # simulation always available; real_tts flag distinguishes prod
    tts_mode = "real_tts" if real_tts else "local_simulation"
    composio_ok = _has("COMPOSIO_API_KEY", "COMPOSIO_KEY")

    missing: list[dict] = []
    if not ffmpeg_ok:
        missing.append({"capability": "assembly",
                        "message": "ffmpeg/ffprobe not found on PATH. Install FFmpeg to assemble Reels."})
    if not higgsfield_ok:
        if cli_installed and not logged_in:
            hf_msg = ("Higgsfield CLI found but not logged in. Run `higgsfield auth "
                      "login` to generate real animated clips. Until then, Run Reel "
                      "produces a free simulation preview.")
        else:
            hf_msg = ("Install the Higgsfield CLI and run `higgsfield auth login` "
                      "(or set HIGGSFIELD_API_KEY) to generate real animated clips. "
                      "Until then, Run Reel produces a free simulation preview.")
        missing.append({"capability": "higgsfield", "message": hf_msg})
    if not real_tts:
        missing.append({"capability": "tts",
                        "message": "Voiceover provider missing. Preview runs with a "
                                   "simulated placeholder, but production voiceover is "
                                   "not ready. Log in with the Higgsfield CLI (or add a "
                                   "TTS key) in Settings."})
    if not composio_ok:
        missing.append({"capability": "composio",
                        "message": "Composio not connected. Add COMPOSIO_API_KEY in Settings "
                                   "to publish Reels to Instagram."})

    # The backend can ALWAYS run a full reel end-to-end — in simulation when
    # Higgsfield keys are absent (free, for preview/wiring), or for real when
    # they are present. Only assembly (ffmpeg) is a hard requirement.
    can_run_full = research_ok and content_ok and ffmpeg_ok
    can_run_real = can_run_full and higgsfield_ok

    return {
        "research_provider_available": research_ok,
        "research_providers": providers,
        "llm_provider_available": content_ok,
        "llm_api_configured": llm_key,          # optional enhancer, not required
        "content_engine": "llm" if llm_key else "deterministic",
        "higgsfield_available": higgsfield_ok,
        "higgsfield_transport": hf_transport,          # 'cli' | 'rest' | 'none'
        "higgsfield_cli_installed": cli_installed,
        "higgsfield_logged_in": logged_in,
        "tts_available": tts_ok,
        "tts_mode": tts_mode,
        "voiceover_production_ready": real_tts,
        "composio_available": composio_ok,
        "ffmpeg_available": ffmpeg_ok,
        "can_run_full_reel_from_backend": can_run_full,
        "can_generate_real_clips": can_run_real,
        "real_generation_available": higgsfield_ok,
        "simulation_available": ffmpeg_ok,
        "vision_inspection_available": ffmpeg_ok,   # can extract frames for review
        "vision_review_available": False,           # no backend vision model yet
        "can_run_production_reel": bool(can_run_real and real_tts),
        "generation_mode": "real" if can_run_real else "simulation",
        "missing": missing,
    }


def generation_mode() -> str:
    """'real' when Higgsfield keys + ffmpeg are present, else 'simulation'."""
    return check()["generation_mode"]
