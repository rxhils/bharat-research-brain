"""Backend Higgsfield Cloud API client — the localhost backend's own path to
animated clips + TTS, so a normal Reel run needs NO Claude Code.

Two modes, chosen automatically by `capabilities.check()`:

  REAL       — HIGGSFIELD_API_KEY/SECRET set. Calls the Higgsfield Cloud API
               over HTTPS (POST generate -> poll /requests/{id}/status ->
               download result). This SPENDS CREDITS. It runs only when the
               operator triggers a run from the localhost UI.
  SIMULATION — no keys (or force_simulate=True). Synthesizes a moving 9:16
               placeholder clip / silent audio locally with ffmpeg. FREE.
               Lets the entire backend pipeline (plan -> generate -> download ->
               inspect -> assemble -> audit -> review) run and be tested end to
               end without spending anything.

API surface confirmed from the official Higgsfield SDK (higgsfield-ai/higgsfield-js):
  base    https://platform.higgsfield.ai   (override: HIGGSFIELD_API_BASE)
  auth    Authorization: Key <KEY_ID>:<KEY_SECRET>
  status  GET /requests/{request_id}/status  -> {status, video:{url}, images:[]}
          status in queued|in_progress|completed|failed|nsfw
Endpoint paths are env-overridable so an operator on a different plan/gateway
can point this at their own routes without a code change.

This module NEVER auto-runs paid generation at import/build time. Callers must
pass an explicit intent; the simulation path is the safe default.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config (all env-overridable)
# ---------------------------------------------------------------------------
API_BASE = (os.getenv("HIGGSFIELD_API_BASE") or "https://platform.higgsfield.ai").rstrip("/")
GEN_PATH = os.getenv("HIGGSFIELD_GENERATE_PATH") or "/v1/text2video"
GEN_PATH_I2V = os.getenv("HIGGSFIELD_I2V_PATH") or "/v1/image2video/dop"
AUDIO_PATH = os.getenv("HIGGSFIELD_AUDIO_PATH") or "/v1/text2speech"
STATUS_PATH = os.getenv("HIGGSFIELD_STATUS_PATH") or "/requests/{id}/status"
POLL_INTERVAL = float(os.getenv("HIGGSFIELD_POLL_INTERVAL") or 6)
POLL_TIMEOUT = float(os.getenv("HIGGSFIELD_POLL_TIMEOUT") or 600)

_DONE = {"completed"}
_FAILED = {"failed", "nsfw", "error", "cancelled"}


class HiggsfieldError(RuntimeError):
    pass


def _auth_header() -> str | None:
    key = (os.getenv("HIGGSFIELD_API_KEY") or "").strip()
    secret = (os.getenv("HIGGSFIELD_API_SECRET") or "").strip()
    if key and secret:
        return f"Key {key}:{secret}"
    if ":" in key:                       # single combined "id:secret" form
        return f"Key {key}"
    return None


def available() -> bool:
    return _auth_header() is not None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _request(method: str, path: str, body: dict | None = None) -> dict:
    auth = _auth_header()
    if not auth:
        raise HiggsfieldError("Higgsfield API keys not configured")
    url = API_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", auth)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise HiggsfieldError(f"HTTP {e.code} on {method} {path}: {detail}") from e
    except urllib.error.URLError as e:
        raise HiggsfieldError(f"network error on {method} {path}: {e.reason}") from e
    return json.loads(raw) if raw.strip() else {}


def _extract_request_id(resp: dict) -> str:
    for k in ("request_id", "id", "requestId", "job_id"):
        if resp.get(k):
            return str(resp[k])
    # some responses nest under 'data'
    data = resp.get("data") or {}
    for k in ("request_id", "id"):
        if data.get(k):
            return str(data[k])
    raise HiggsfieldError(f"no request id in generate response: {json.dumps(resp)[:300]}")


def _extract_media_url(resp: dict) -> str | None:
    # {video:{url}} | {results:{raw:{url}}} | {jobs:[{results:{raw:{url}}}]} | {audio:{url}}
    for path in (("video", "url"), ("audio", "url"), ("results", "raw", "url"),
                 ("result", "url"), ("output", "url")):
        cur = resp
        for k in path:
            cur = cur.get(k) if isinstance(cur, dict) else None
            if cur is None:
                break
        if isinstance(cur, str) and cur.startswith("http"):
            return cur
    jobs = resp.get("jobs") or (resp.get("results") if isinstance(resp.get("results"), list) else None)
    if isinstance(jobs, list) and jobs:
        return _extract_media_url(jobs[0])
    return None


# ---------------------------------------------------------------------------
# Real generation
# ---------------------------------------------------------------------------
def submit_video(prompt: str, *, model: str, duration: int, aspect_ratio: str = "9:16",
                 image_url: str | None = None) -> str:
    """POST a generation request. Returns request_id. SPENDS CREDITS."""
    if image_url:
        body = {"model": model, "prompt": prompt, "duration": duration,
                "aspect_ratio": aspect_ratio,
                "input_images": [{"type": "image_url", "image_url": image_url}]}
        resp = _request("POST", GEN_PATH_I2V, body)
    else:
        body = {"model": model, "prompt": prompt, "duration": duration,
                "aspect_ratio": aspect_ratio}
        resp = _request("POST", GEN_PATH, body)
    return _extract_request_id(resp)


def submit_audio(text: str, *, model: str = "seed_audio", voice_id: str | None = None,
                 speech_rate: float | None = None) -> str:
    body: dict = {"model": model, "prompt": text, "format": "wav"}
    if voice_id:
        body["voice_id"] = voice_id
    if speech_rate is not None:
        body["speech_rate"] = speech_rate
    return _extract_request_id(_request("POST", AUDIO_PATH, body))


def poll(request_id: str) -> dict:
    """One status check: {status, media_url?}."""
    resp = _request("GET", STATUS_PATH.format(id=request_id))
    status = str(resp.get("status") or resp.get("state") or "").lower()
    return {"status": status, "media_url": _extract_media_url(resp), "raw": resp}


def wait(request_id: str, *, timeout: float = POLL_TIMEOUT) -> str:
    """Block until completed; returns the media URL. Raises on failure/timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        st = poll(request_id)
        if st["status"] in _DONE and st["media_url"]:
            return st["media_url"]
        if st["status"] in _FAILED:
            raise HiggsfieldError(f"generation {request_id} failed: {st['status']}")
        time.sleep(POLL_INTERVAL)
    raise HiggsfieldError(f"generation {request_id} timed out after {timeout}s")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "MavenNewsroom/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    if dest.stat().st_size == 0:
        raise HiggsfieldError(f"downloaded 0 bytes from {url}")
    return dest


def generate_video_to_file(prompt: str, dest: Path, *, model: str, duration: int,
                           aspect_ratio: str = "9:16", image_url: str | None = None) -> dict:
    """Full real flow: submit -> wait -> download. Returns metadata dict."""
    rid = submit_video(prompt, model=model, duration=duration,
                       aspect_ratio=aspect_ratio, image_url=image_url)
    url = wait(rid)
    download(url, dest)
    return {"request_id": rid, "media_url": url, "path": str(dest),
            "bytes": dest.stat().st_size, "mode": "real"}


def generate_audio_to_file(text: str, dest: Path, *, model: str = "seed_audio",
                           voice_id: str | None = None, speech_rate: float | None = None) -> dict:
    rid = submit_audio(text, model=model, voice_id=voice_id, speech_rate=speech_rate)
    url = wait(rid)
    download(url, dest)
    return {"request_id": rid, "media_url": url, "path": str(dest),
            "bytes": dest.stat().st_size, "mode": "real"}


# ---------------------------------------------------------------------------
# Simulation (free, ffmpeg) — deterministic per (seed, purpose) so scenes differ
# ---------------------------------------------------------------------------
_SIM_PALETTE = {
    "hook": ("0x0A1220", "0x27C281"), "context": ("0x0A1220", "0x22D3EE"),
    "data": ("0x0B1020", "0x38BDF8"), "reason": ("0x0A1220", "0x27C281"),
    "impact": ("0x0B1220", "0x22D3EE"), "cta": ("0x0A1220", "0x27C281"),
}


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise HiggsfieldError("ffmpeg not found (needed for simulation clips)")
    return exe


def simulate_video_to_file(dest: Path, *, purpose: str = "hook", duration: float = 4.0,
                           seed: int = 0) -> dict:
    """Synthesize a MOVING 9:16 placeholder clip (drifting gradient + pulsing
    glow) so the pipeline can run/verify free. Clearly a preview, never claimed
    to be a real Higgsfield clip."""
    ff = _ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    hi = _SIM_PALETTE.get(purpose, ("0x0A1220", "0x22D3EE"))[1]
    # animated gradient via gradients source + a moving radial via geq brightness
    vf = (f"gradients=s=720x1280:c0={_SIM_PALETTE.get(purpose, ('0x0A1220',))[0]}:"
          f"c1={hi}:x0=360:y0=0:x1=360:y1=1280:d={duration}:speed=0.02,"
          f"format=yuv420p")
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", vf, "-t", f"{duration:.2f}",
         "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p", str(dest)],
        check=True, capture_output=True, timeout=120)
    return {"request_id": f"sim-{purpose}-{seed}", "media_url": None,
            "path": str(dest), "bytes": dest.stat().st_size, "mode": "simulation"}


def simulate_audio_to_file(dest: Path, *, duration: float = 18.0) -> dict:
    """Silent placeholder audio track (free)."""
    ff = _ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
         "-t", f"{duration:.2f}", "-c:a", "libmp3lame", "-q:a", "9", str(dest)],
        check=True, capture_output=True, timeout=60)
    return {"path": str(dest), "bytes": dest.stat().st_size, "mode": "simulation"}
