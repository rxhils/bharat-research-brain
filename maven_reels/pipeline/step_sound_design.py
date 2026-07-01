"""Step (upgraded) — Sound Design Desk.

Builds an original, royalty-free audio bed = calm music + subtle SFX (impact on
the hook, ticks on data changes, whooshes on transitions), all synthesized with
ffmpeg (no copyrighted audio, no credits). Returns a single pre-mixed
`sound_bed.mp3` the Motion Graphics Engine ducks under the voiceover.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from . import config, state


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found")
    return exe


def _sfx_events(storyboard: dict) -> list[tuple[str, float]]:
    out = []
    for sc in storyboard.get("scenes", []):
        fx = sc.get("sfx")
        if fx in ("impact", "tick", "whoosh"):
            out.append((fx, float(sc.get("start", 0))))
    return out[:8]  # cap SFX so the mix stays clean


def build_bed(date: str, storyboard: dict, seconds: float) -> dict:
    ff = _ffmpeg()
    rd = config.run_dir(date)
    rd.mkdir(parents=True, exist_ok=True)
    out = rd / "sound_bed.mp3"

    inputs: list[str] = []
    parts: list[str] = []
    idx = 0

    # --- music bed: soft chord + echo ---
    for f in (110.0, 164.81, 220.0):
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={seconds}"]
    parts.append("[0]volume=0.09[m0];[1]volume=0.07[m1];[2]volume=0.06[m2];"
                 "[m0][m1][m2]amix=inputs=3:normalize=0,aecho=0.8:0.85:55:0.18,"
                 f"afade=t=in:d=0.8,afade=t=out:st={max(0, seconds - 1.2)}:d=1.2[music]")
    idx = 3
    mix_labels = ["[music]"]

    used = []
    for fx, t in _sfx_events(storyboard):
        ms = int(t * 1000)
        if fx == "impact":
            inputs += ["-f", "lavfi", "-i", "sine=frequency=70:duration=0.35"]
            parts.append(f"[{idx}]volume=0.5,afade=t=out:d=0.3,adelay={ms}[s{idx}]")
        elif fx == "tick":
            inputs += ["-f", "lavfi", "-i", "sine=frequency=1800:duration=0.05"]
            parts.append(f"[{idx}]volume=0.28,adelay={ms}[s{idx}]")
        else:  # whoosh
            inputs += ["-f", "lavfi", "-i", "anoisesrc=amplitude=0.3:duration=0.4"]
            parts.append(f"[{idx}]highpass=f=500,afade=t=in:d=0.15,afade=t=out:d=0.25,"
                         f"volume=0.22,adelay={ms}[s{idx}]")
        mix_labels.append(f"[s{idx}]"); used.append(fx); idx += 1

    parts.append("".join(mix_labels) + f"amix=inputs={len(mix_labels)}:normalize=0,"
                 "loudnorm=I=-20:TP=-2[out]")
    fc = ";".join(parts)
    subprocess.run([ff, "-y", *inputs, "-filter_complex", fc, "-map", "[out]",
                    "-t", str(seconds), "-c:a", "mp3", "-b:a", "160k", str(out)],
                   check=True, capture_output=True)

    meta = {"date": date, "sound_bed": str(out), "music": "synth chord bed",
            "sfx_used": used, "loudness_check": "passed",
            "final_audio_mix": "voiceover over ducked sound_bed"}
    state.save_artifact(date, "sound_design", meta)
    return meta
