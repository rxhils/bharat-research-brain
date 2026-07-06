"""Original music bed for auto-published slideshow reels (zero credits).

Composes a copyright-safe instrumental with ffmpeg lavfi: an uplifting
Am-F-C-G chord progression (~114 BPM feel) with octave shimmer, sub-bass
pulse, hats and a riser into the final slide. Used ONLY for the optional
API-published MP4 — native manual uploads take the Viral Audio Scout's
trending pick inside Instagram instead.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

CHORDS = [
    [110.00, 164.81, 220.00, 261.63],   # Am
    [87.31, 130.81, 174.61, 220.00],    # F
    [130.81, 196.00, 261.63, 329.63],   # C
    [98.00, 146.83, 196.00, 246.94],    # G
]


class AudioBedError(RuntimeError):
    pass


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise AudioBedError("ffmpeg not found on PATH")
    return exe


def build_bed(dest: Path, seconds: float = 16.4) -> Path:
    """Render the chord-progression bed to an .m4a at `dest`."""
    seg = seconds / len(CHORDS)
    inputs: list[str] = []
    fc: list[str] = []
    idx = 0
    seg_labels = []
    for ci, chord in enumerate(CHORDS):
        voices = []
        for f in chord:
            for freq, vol in ((f, 0.16), (f * 2, 0.05)):
                inputs += ["-f", "lavfi", "-i",
                           f"sine=frequency={freq}:duration={seg}"]
                fc.append(f"[{idx}:a]volume={vol}[v{idx}]")
                voices.append(f"[v{idx}]")
                idx += 1
        lab = f"[seg{ci}]"
        fc.append("".join(voices) + f"amix=inputs={len(voices)}:normalize=0,"
                  f"afade=t=in:st=0:d=0.04,"
                  f"afade=t=out:st={seg - 0.06:.2f}:d=0.06{lab}")
        seg_labels.append(lab)
    fc.append("".join(seg_labels) + f"concat=n={len(CHORDS)}:v=0:a=1,"
              "tremolo=f=1.9:d=0.25,lowpass=f=2400[pad]")
    inputs += ["-f", "lavfi", "-i", f"sine=frequency=55:duration={seconds}"]
    fc.append(f"[{idx}:a]tremolo=f=1.9:d=0.96,volume=0.5[sub]")
    idx += 1
    inputs += ["-f", "lavfi", "-i",
               f"anoisesrc=color=white:amplitude=0.2:duration={seconds}"]
    fc.append(f"[{idx}:a]highpass=f=8200,tremolo=f=3.8:d=1,volume=0.10[hat]")
    idx += 1
    riser_at = max(seconds - 6.9, 0)
    inputs += ["-f", "lavfi", "-i",
               "anoisesrc=color=pink:amplitude=0.3:duration=3.0"]
    fc.append(f"[{idx}:a]highpass=f=1200,afade=t=in:st=0:d=2.6,"
              f"afade=t=out:st=2.6:d=0.4,volume=0.10,"
              f"adelay={int(riser_at * 1000)}|{int(riser_at * 1000)}[riser]")
    idx += 1
    fc.append("[pad][sub][hat][riser]amix=inputs=4:normalize=0,"
              f"afade=t=in:st=0:d=0.6,afade=t=out:st={seconds - 2:.2f}:d=2.0,"
              "loudnorm=I=-16:TP=-1.5:LRA=9[out]")
    cmd = [_ffmpeg(), "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[out]", "-ar", "44100", "-c:a", "aac", "-b:a", "192k",
           str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not dest.exists():
        raise AudioBedError(f"bed render failed: {proc.stderr[-300:]}")
    return dest


def mux(video: Path, bed: Path, dest: Path) -> Path:
    """Mux the bed under the slideshow video (video stream copied)."""
    proc = subprocess.run(
        [_ffmpeg(), "-y", "-i", str(video), "-i", str(bed), "-map", "0:v",
         "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(dest)],
        capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not dest.exists():
        raise AudioBedError(f"mux failed: {proc.stderr[-300:]}")
    return dest
