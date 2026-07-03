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
FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _fontsdir_escaped() -> str:
    """Absolute bundled-fonts dir escaped for the ffmpeg filtergraph (Windows: / + \\:)."""
    return str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not found")
    return exe


# ---------------------------------------------------------------- ASS overlays
# Premium kinetic text: big word-pop hook (upper-mid, thin edge + soft shadow),
# voice-synced phrase subtitles on a translucent navy pill (no thick outline),
# one teal/green highlight word, subtle Maven brand mark. Driven by the Text
# Studio's kinetic plan + text_style_config.json.
def _ass_time(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _esc(text: str) -> str:
    return str(text).replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


# ASS colours are &HAABBGGRR (AA=alpha, 00 opaque .. FF clear)
WHITE_ASS = "&H00FCF8FA&"        # #F8FAFC
SUB_HI_ASS = "&H00C3D620&"       # #20D6C3 teal
HOOK_HI_ASS = "&H00A6E62F&"      # #2FE6A6 green
BOX_ASS = "&H8C20120A&"          # translucent navy #0A1220 pill fill
HOOK_EDGE_ASS = "&H90101010&"    # soft dark edge
BRAND_ASS = "&H30E6EDF5&"        # subtle light brand

_WIN_FONTS = {"segoe ui semibold", "segoe ui", "arial", "calibri", "tahoma", "verdana"}


def _resolve_font(families: list[str]) -> str:
    """First installed family from the config stack, else a clean Windows sans."""
    import os
    fdir = Path(os.getenv("WINDIR", "C:/Windows")) / "Fonts"
    have = {p.stem.lower().replace("-", " ") for p in fdir.glob("*.ttf")} if fdir.exists() else set()
    for f in families:
        fl = f.lower()
        if fl in _WIN_FONTS or fl in have or fl.replace(" ", "") in {h.replace(' ', '') for h in have}:
            return f
    return "Segoe UI Semibold"


def _emph_line(line: str, emphasis: list[str], hi: str, underline: bool = True) -> str:
    """Colour + underline the single key word/phrase (the main idea)."""
    ewords = {e.lower().strip(".,%—-") for e in (emphasis or []) if e}
    u1, u0 = ("\\u1", "\\u0") if underline else ("", "")
    out = []
    for w in _esc(line).split():
        if w.lower().strip(".,%—-") in ewords and ewords:
            out.append(f"{{{u1}\\c{hi}}}{w}{{{u0}\\c{WHITE_ASS}}}")
        else:
            out.append(w)
    return " ".join(out)


# centred positions (x=540). Hook slightly above centre; cards mid; subs lower.
_CENTER_X = W // 2
_Y = {"hook": 780, "phrase_card": 910, "subtitle": 1360, "cta": 910}


def _anim_tag(animation: str, y: int) -> str:
    """Meaning-driven entrance, all centred via \\an5."""
    x = _CENTER_X
    a = {
        "punch": f"\\an5\\pos({x},{y})\\fad(90,90)\\fscx58\\fscy58\\t(0,220,\\fscx100\\fscy100)",
        "rise":  f"\\an5\\move({x},{y+90},{x},{y},0,240)\\fad(120,90)",
        "drop":  f"\\an5\\move({x},{y-90},{x},{y},0,240)\\fad(120,90)",
        "slide": f"\\an5\\move({x-130},{y},{x},{y},0,240)\\fad(120,90)",
        "pulse": f"\\an5\\pos({x},{y})\\fad(90,90)\\t(0,140,\\fscx110\\fscy110)\\t(140,320,\\fscx100\\fscy100)",
        "pop":   f"\\an5\\pos({x},{y})\\fad(80,70)\\fscx92\\fscy92\\t(0,130,\\fscx100\\fscy100)",
    }
    return a.get(animation, a["pop"])


def _build_ass(*, hook: dict, subtitles: list[dict], cta: dict | None,
               brand: str, style: dict, total: float) -> str:
    font = _resolve_font(style.get("font_family", ["Segoe UI Semibold"]))
    hk, sb, br = style["hook"], style["subtitle"], style["brand"]
    # All text is CENTERED (Alignment=5); vertical placement + motion via tags.
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Archivo Black,{hk['font_size']},{WHITE_ASS},{WHITE_ASS},{HOOK_EDGE_ASS},&H00000000&,-1,0,0,0,100,100,-1,0,1,1,0,5,60,60,60,1
Style: Card,Bebas Neue,88,{WHITE_ASS},{WHITE_ASS},{HOOK_EDGE_ASS},&H00000000&,-1,0,0,0,100,100,0,0,1,1,0,5,60,60,60,1
Style: Sub,Montserrat SemiBold,{sb['font_size']},{WHITE_ASS},{WHITE_ASS},{BOX_ASS},{BOX_ASS},-1,0,0,0,100,100,0,0,3,16,0,5,90,90,60,1
Style: Brand,Montserrat SemiBold,{br['font_size']},{BRAND_ASS},{BRAND_ASS},&H00000000&,&H00000000&,-1,0,0,0,100,100,1,0,1,0,0,7,54,54,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    ev.append(f"Dialogue: 0,{_ass_time(0)},{_ass_time(total)},Brand,,0,0,0,,{_esc(brand)}")
    if hook and hook.get("text"):
        lines = "\\N".join(_emph_line(l, hook.get("emphasis_words", []), HOOK_HI_ASS,
                                      hook.get("underline", True))
                           for l in _wrap_ass(hook["text"], 15, 2))
        ev.append(f"Dialogue: 2,{_ass_time(hook.get('start', 0))},{_ass_time(hook.get('end', 1.6))},"
                  f"Hook,,0,0,0,,{{{_anim_tag(hook.get('animation', 'punch'), _Y['hook'])}}}{lines}")
    for c in subtitles:
        role = c.get("role", "subtitle")
        stylename = "Card" if role == "phrase_card" else "Sub"
        y = _Y["phrase_card"] if role == "phrase_card" else _Y["subtitle"]
        lines = "\\N".join(_emph_line(l, c.get("emphasis_words", []), SUB_HI_ASS,
                                      c.get("underline", True))
                           for l in (c.get("lines") or [c.get("text", "")]))
        ev.append(f"Dialogue: 3,{_ass_time(float(c['start']))},{_ass_time(float(c['end']))},"
                  f"{stylename},,0,0,0,,{{{_anim_tag(c.get('animation', 'pop'), y)}}}{lines}")
    return header + "\n".join(ev) + "\n"


def _wrap_ass(text: str, max_chars: int, max_lines: int) -> list[str]:
    lines, cur = [], ""
    for w in _esc(text).split():
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines[:max_lines] or [text]


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
        voiceover_mp3: str | None = None,
        text_plan: dict | None = None, text_style: dict | None = None) -> dict:
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

    # 3) overlays (ASS) — premium kinetic text from the Text Studio's plan.
    #    Falls back to the legacy hook/subtitles artifacts if no plan is passed.
    import json as _json  # noqa: PLC0415
    style = text_style or _json.loads(
        (Path(__file__).resolve().parent / "text_style_config.json").read_text(encoding="utf-8"))
    if text_plan:
        hook_block = text_plan.get("hook_text", {})
        sub_cues = text_plan.get("subtitles", [])
    else:  # legacy compatibility
        hook_block = {"text": hooks.get("on_screen_hook", "") or hooks.get("selected_hook", ""),
                      "start": 0.0, "end": float(shots[0]["duration"]) if shots else 1.6,
                      "emphasis_words": []}
        sub_cues = [{"start": c.get("start", 0), "end": c.get("end", 0),
                     "text": c.get("text", ""), "lines": None,
                     "emphasis_words": [c["emphasis"]] if c.get("emphasis") else []}
                    for c in (subtitles.get("subtitles", []) if isinstance(subtitles, dict) else [])]
    ass_path = rd / "_overlays.ass"
    ass_path.write_text(
        _build_ass(hook=hook_block, subtitles=sub_cues, cta=text_plan.get("cta") if text_plan else None,
                   brand=f"{config.BRAND_NAME} · {config.BRAND_SITE}", style=style, total=total),
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

    # 5) final pass: burn ASS + mix audio (run in rd so the ass filter + fontsdir
    #    get RELATIVE paths — dodges the spaces/drive-letter filter-escaping issue).
    #    Copy the bundled fonts into a space-free local dir the filter can point at.
    fonts_local = rd / "_fonts"
    fonts_local.mkdir(exist_ok=True)
    if FONTS_DIR.exists():
        for _f in FONTS_DIR.glob("*.ttf"):
            shutil.copy2(_f, fonts_local / _f.name)
    out = rd / "reel.mp4"
    vf = "ass=_overlays.ass:fontsdir=_fonts"
    if vo.exists() and bed is not None:
        cmd = [ff, "-y", "-i", str(stitched), "-i", str(vo), "-i", str(bed),
               "-filter_complex",
               f"[0:v]{vf}[v];[2:a]volume=0.14,lowpass=f=2800[m];"
               f"[1:a][m]amix=inputs=2:duration=first[a]",
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
        "subtitles_burned": bool(sub_cues), "hook_overlay": bool(hook_block.get("text")),
        "bytes": out.stat().st_size, "status": "completed",
        # compat keys so the existing auditor's mechanical checks keep working
        "reel": str(out), "cover": str(cover), "width": W, "height": H,
        "seconds": total, "has_voiceover": vo.exists(), "has_subtitles": bool(sub_cues),
    }
    state.save_artifact(date, "final_reel", meta)
    state.save_artifact(date, "reel_video", meta)   # single source for auditor/UI
    return meta
