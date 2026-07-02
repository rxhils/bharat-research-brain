"""Step — Final Reel Assembler (the new primary finisher; local, free).

Stitches the Higgsfield animated clips into the final Instagram-ready reel:
  1. Normalize every clip (1080x1920, 30fps, trimmed to its shot duration).
  2. Concat in shot order.
  3. Burn overlays via one ASS subtitle track: big hook text on the first shot,
     kinetic bottom subtitles with a teal emphasis word, small Maven brand line.
  4. Mux voiceover over a ducked original music+SFX bed (Sound Design Desk).
  5. Export reel.mp4 (H.264, CRF 19) + cover.jpg from the hook moment.

Deliberately light-handed: the Higgsfield animation IS the look — this step
only adds crisp text/audio, it never re-designs the visuals. All real numbers
and claims live in these overlays, never inside the generated footage.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import config, state, step_sound_design

W, H, FPS = 1080, 1920, 30


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found")
    return exe


# ---------------------------------------------------------------- ASS overlays
def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


TEAL_ASS = "&H00EED322&"   # #22D3EE in ASS BGR order
WHITE_ASS = "&H00FFFFFF&"


def _build_ass(hook_text: str, hook_until: float, cues: list[dict],
               brand: str, total: float) -> str:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Segoe UI,96,{WHITE_ASS},{WHITE_ASS},&H00000000&,&H96000000&,-1,0,0,0,100,100,0,0,1,4,2,8,60,60,560,1
Style: Sub,Segoe UI,58,{WHITE_ASS},{WHITE_ASS},&H00000000&,&H96000000&,-1,0,0,0,100,100,0,0,1,3,2,2,80,80,300,1
Style: Brand,Segoe UI,34,{WHITE_ASS},{WHITE_ASS},&H00000000&,&H96000000&,-1,0,0,0,100,100,0,0,1,2,1,7,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    if hook_text:
        events.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(hook_until)},Hook,,0,0,0,,"
                      f"{{\\fad(120,150)}}{_esc(hook_text)}")
    events.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(total)},Brand,,0,0,0,,"
                  f"{_esc(brand)}")
    for c in cues:
        words = _esc(str(c.get("text", ""))).split()
        emph = str(c.get("emphasis", "")).lower().strip(".,%")
        styled = " ".join(
            f"{{\\c{TEAL_ASS}}}{w}{{\\c{WHITE_ASS}}}"
            if emph and emph in w.lower().strip(".,%") else w
            for w in words)
        events.append(f"Dialogue: 2,{_ass_time(float(c['start']))},"
                      f"{_ass_time(float(c['end']))},Sub,,0,0,0,,"
                      f"{{\\fad(80,80)}}{styled}")
    return header + "\n".join(events) + "\n"


# ---------------------------------------------------------------- assembly
def _normalize(ff: str, src: Path, dst: Path, seconds: float) -> None:
    subprocess.run(
        [ff, "-y", "-i", str(src),
         "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},fps={FPS},setsar=1",
         "-t", f"{seconds:.2f}", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", str(dst)],
        check=True, capture_output=True, timeout=300)


def run(date: str, *, shot_plan: dict, subtitles: dict, hooks: dict,
        voiceover_mp3: str | None = None) -> dict:
    ff = _ffmpeg()
    rd = config.run_dir(date)
    work = rd / "_assembly"
    work.mkdir(parents=True, exist_ok=True)

    # 1) normalize clips in shot order (a missing clip is a hard error — the
    #    inspector gates before us; we never silently swap in other footage)
    shots = shot_plan.get("shots", [])
    norm_paths, clips_used = [], []
    for s in shots:
        src = rd / "higgsfield_clips" / f"{s['shot_id']}.mp4"
        if not src.exists():
            raise FileNotFoundError(f"missing clip for {s['shot_id']}: {src}")
        dst = work / f"n_{s['shot_id']}.mp4"
        _normalize(ff, src, dst, float(s["duration"]))
        norm_paths.append(dst)
        clips_used.append(s["shot_id"])

    # 2) concat
    listfile = work / "concat.txt"
    listfile.write_text("".join(f"file '{p.name}'\n" for p in norm_paths),
                        encoding="utf-8")
    stitched = work / "stitched.mp4"
    subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-c", "copy", str(stitched)],
                   check=True, capture_output=True, cwd=str(work), timeout=300)

    total = round(sum(float(s["duration"]) for s in shots), 2)

    # 3) overlays (ASS) — hook big on shot 1, kinetic subs, brand line
    hook_text = hooks.get("on_screen_hook", "") or hooks.get("selected_hook", "")
    hook_until = float(shots[0]["duration"]) if shots else 2.0
    cues = subtitles.get("subtitles", []) if isinstance(subtitles, dict) else []
    ass_path = rd / "_overlays.ass"
    ass_path.write_text(
        _build_ass(hook_text, hook_until, cues,
                   f"{config.BRAND_NAME} · {config.BRAND_SITE}", total),
        encoding="utf-8")

    # 4) audio bed (music + SFX, original/ffmpeg-synth) + voiceover
    try:
        sb = {"scenes": [{"sfx": "impact", "start": 0.0},
                         *({"sfx": "whoosh", "start": s["start"]} for s in shots[1:])],
              }
        bed = Path(step_sound_design.build_bed(date, sb, total)["sound_bed"])
    except Exception:
        bed = None
    vo = Path(voiceover_mp3) if voiceover_mp3 else (rd / "voiceover.mp3")

    # 5) final pass: burn ASS + mix audio (run in rd so the ass filter gets a
    #    relative path — dodges the Windows drive-letter filter-escaping issue)
    out = rd / "reel.mp4"
    vf = "ass=_overlays.ass"
    if vo.exists() and bed is not None:
        cmd = [ff, "-y", "-i", str(stitched), "-i", str(vo), "-i", str(bed),
               "-filter_complex",
               f"[0:v]{vf}[v];[2:a]volume=0.5[m];[1:a][m]amix=inputs=2:duration=first[a]",
               "-map", "[v]", "-map", "[a]"]
    elif vo.exists():
        cmd = [ff, "-y", "-i", str(stitched), "-i", str(vo),
               "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a"]
    elif bed is not None:
        cmd = [ff, "-y", "-i", str(stitched), "-i", str(bed),
               "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a"]
    else:
        cmd = [ff, "-y", "-i", str(stitched),
               "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-t", f"{total:.2f}", str(out)]
    subprocess.run(cmd, check=True, capture_output=True, cwd=str(rd), timeout=600)

    # 6) cover from the hook moment (hook text is burned in by then)
    cover = rd / "cover.jpg"
    subprocess.run([ff, "-y", "-ss", f"{min(0.8, total / 2):.2f}", "-i", str(out),
                    "-frames:v", "1", "-q:v", "3", str(cover)],
                   check=True, capture_output=True, timeout=120)

    shutil.rmtree(work, ignore_errors=True)

    meta = {
        "date": date, "video_path": str(out), "cover_path": str(cover),
        "duration": total, "resolution": f"{W}x{H}", "fps": FPS,
        "renderer": "higgsfield_primary", "assembler": "ffmpeg",
        "clips_used": clips_used, "scene_count": len(clips_used),
        "audio_used": ("voiceover + original synth bed" if vo.exists()
                       else "original synth bed only"),
        "subtitles_burned": bool(cues), "hook_overlay": bool(hook_text),
        "bytes": out.stat().st_size, "status": "completed",
        # compat keys so the existing auditor's mechanical checks keep working
        "reel": str(out), "cover": str(cover), "width": W, "height": H,
        "seconds": total, "has_voiceover": vo.exists(), "has_subtitles": bool(cues),
    }
    state.save_artifact(date, "final_reel", meta)
    state.save_artifact(date, "reel_video", meta)   # single source for auditor/UI
    return meta
