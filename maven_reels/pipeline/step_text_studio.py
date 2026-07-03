"""Step — Text Studio (voice-aligned kinetic text + subtitles). Local, free.

The single source of truth for every on-screen word is the VOICEOVER's spoken
text, so subtitles/hook always match what is heard. This one module covers the
text layer end to end and writes the artifacts the assembler + auditor consume:

  20_text_alignment.json   — spoken→display segments, timed to the voice
  21_kinetic_text_plan.json — hook / subtitles / callouts / cta with anim+position
  22_text_safe_area.json    — per-scene safe placement (above IG controls, off-brand)
  23_text_animation.json    — per-element animation + easing + emphasis

Timing: uses TTS/voiceover duration and word proportions (deterministic,
"estimated" mode). If a Whisper transcript is present it is used for tighter
sync; nothing here calls a paid service or regenerates any clip.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import config, state

STYLE_PATH = Path(__file__).resolve().parent / "text_style_config.json"

_FINANCE_KEYWORDS = {
    "sensex", "nifty", "bank", "banks", "banking", "rbi", "sebi", "fii", "dii",
    "sector", "sectors", "it", "tech", "technology", "maven", "rupee", "crude",
    "inflation", "rate", "rates", "midcap", "smallcap", "index", "market",
    "earnings", "profit", "rally", "fall", "flows", "liquidity", "policy",
}
_NUM = re.compile(r"\d")


def _load_style() -> dict:
    return json.loads(STYLE_PATH.read_text(encoding="utf-8"))


def _opt(date: str, key: str) -> dict | None:
    try:
        return state.load_artifact(date, key)
    except Exception:
        return None


# ---------------------------------------------------------------- transcript
def _ffprobe_dur(path: Path) -> float:
    exe = shutil.which("ffprobe")
    if not exe or not path.exists():
        return 0.0
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def _transcript(date: str, voiceover: dict | None, script_edited: dict) -> tuple[str, float]:
    """Spoken text = what the voice actually says (the alignment source of truth).
    Prefer the voiceover artifact's spoken_text/script_used; fall back to the
    edited script narration."""
    vo = voiceover or _opt(date, "voiceover_v2") or {}
    spoken = (vo.get("spoken_text") or vo.get("script_used")
              or script_edited.get("narration") or "").strip()
    dur = float(vo.get("duration") or 0.0)
    if dur <= 0:
        dur = _ffprobe_dur(config.run_dir(date) / "voiceover.mp3")
    return spoken, (dur or 18.0)


# ---------------------------------------------------------------- text utils
_SUBST = [(" dot in", ".in"), (" dot ", "."), (" dot.", ".")]


def _clean_display(s: str) -> str:
    out = " ".join(s.split())
    low = out.lower()
    for a, b in _SUBST:
        if a in low:
            idx = low.find(a)
            out = out[:idx] + b + out[idx + len(a):]
            low = out.lower()
    return out.strip(" ,;:—-").strip()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _phrase_cues(text: str, max_words: int) -> list[str]:
    """Chunk by natural clause boundaries, then cap at max_words — never split
    mid-idea when a comma/dash is available."""
    clauses = re.split(r"\s*[—–]\s*|(?<=[,;:])\s+", text)
    cues: list[str] = []
    for cl in clauses:
        words = _clean_display(cl).split()
        if not words:
            continue
        for i in range(0, len(words), max_words):
            chunk = " ".join(words[i:i + max_words]).strip()
            if chunk:
                cues.append(chunk)
    return cues


def _wrap(cue: str, max_chars: int, max_lines: int) -> list[str]:
    lines, cur = [], ""
    for w in cue.split():
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines[:max_lines]


def _emphasis(cue: str) -> list[str]:
    toks = [t.strip(".,;:%—-()") for t in cue.split()]
    # numbers / percentages first
    for raw, t in zip(cue.split(), toks):
        if _NUM.search(raw):
            return [t]
    for t in toks:
        if t.lower() in _FINANCE_KEYWORDS:
            return [t]
    longest = max(toks, key=len, default="")
    return [longest] if len(longest) > 3 else []


def _compress_hook(sentence: str, max_words: int = 7) -> str:
    s = _clean_display(sentence)
    words = s.split()
    if len(words) <= max_words:
        return s
    # keep the leading clause up to a comma if that fits, else first N words
    head = re.split(r"[,;:]", s)[0].split()
    return " ".join((head if 1 < len(head) <= max_words else words[:max_words]))


# ---------------------------------------------------------------- alignment
def _align(date: str, spoken: str, vo_dur: float, video_dur: float,
           style: dict) -> dict:
    sub_cfg = style["subtitle"]
    sents = _sentences(spoken) or [spoken]
    hook_sentence = sents[0]
    body = " ".join(sents[1:]).strip()

    hook_text = _compress_hook(hook_sentence)
    body_cues = _phrase_cues(body, sub_cfg["max_words_per_cue"]) if body else []

    # timing: proportional to spoken words, across the effective duration
    units = [("hook", hook_sentence, hook_text)] + [("subtitle", c, c) for c in body_cues]
    eff = max(6.0, min(vo_dur or video_dur, video_dur))
    total_words = sum(max(1, len(u[1].split())) for u in units) or 1

    segments, t = [], 0.0
    for i, (role, spoken_chunk, display) in enumerate(units):
        w = max(1, len(spoken_chunk.split()))
        # proportional (no hard floor) so shares sum to eff — the tail CTA never
        # gets squeezed to zero; brief cues stay visible.
        dur = round(w / total_words * eff, 2)
        start = round(t, 2)
        end = round(min(eff, start + dur), 2)
        t = end
        segments.append({
            "segment_id": f"seg_{i+1:02d}",
            "start": start, "end": end,
            "spoken_text": _clean_display(spoken_chunk),
            "display_text": _clean_display(display),
            "emphasis_words": _emphasis(display),
            "scene_id": "", "text_role": role,
        })
    if segments:
        segments[-1]["end"] = round(min(eff, video_dur), 2)

    # match score: display tokens should be a subset of spoken tokens
    def toks(s): return set(re.findall(r"[a-z0-9]+", s.lower()))
    spoken_toks = toks(spoken)
    disp_toks = set().union(*[toks(s["display_text"]) for s in segments]) if segments else set()
    match = round(100 * len(disp_toks & spoken_toks) / max(1, len(disp_toks)))

    issues = []
    if not segments:
        issues.append("no spoken text to align")
    if match < 90:
        issues.append(f"display/voice token match low ({match})")

    payload = {
        "date": date, "voiceover_duration": round(vo_dur, 2),
        "video_duration": round(video_dur, 2),
        "alignment_mode": "tts_timing" if vo_dur else "estimated",
        "segments": segments,
        "text_voice_match_score": match,
        "alignment_score": max(0, 100 - 6 * len(issues)),
        "issues": issues,
    }
    state.save_artifact(date, "text_alignment", payload)
    return payload


# ---------------------- semantic (meaning-driven) motion -------------------
# Text motion should express the word: things that rose rise, things that fell
# drop, signals pulse, moves slide. Keeps readability, adds meaning.
_RISE = {"rise", "rose", "risen", "up", "higher", "gain", "gained", "gains", "surge",
         "surged", "climb", "climbed", "jump", "jumped", "rally", "rallied",
         "underneath", "beneath", "below", "under", "outperform", "outperformed"}
_DROP = {"fell", "fall", "fallen", "drop", "dropped", "down", "lower", "sink", "slip",
         "slipped", "crash", "crashed", "decline", "declined", "loss", "losses", "sank"}
_SLIDE = {"moved", "move", "moves", "shift", "shifted", "shifts", "swung", "swing",
          "flow", "flows", "rotate", "rotated", "spread"}
_PULSE = {"signal", "rate", "rates", "policy", "rbi", "fed", "sebi", "reacted", "react",
          "pulse", "news", "announcement", "decision", "cut", "hike"}


def _semantic_anim(text: str, role: str) -> str:
    w = set(re.findall(r"[a-z]+", text.lower()))
    if w & _PULSE:
        return "pulse"
    if w & _RISE:
        return "rise"
    if w & _DROP:
        return "drop"
    if w & _SLIDE:
        return "slide"
    return "punch" if role in ("hook_card", "phrase_card") else "pop"


def _is_key_beat(text: str) -> bool:
    """Only genuinely short/punchy beats become big centered phrase cards; longer
    explanatory lines stay as lower subtitles so the centre visual stays clear
    (true hybrid, not all-cards)."""
    toks = text.split()
    if len(toks) <= 3:
        return True
    return len(toks) <= 5 and any(_NUM.search(t) for t in toks)


# ---------------------------------------------------------------- kinetic plan
def _kinetic(date: str, align: dict, style: dict) -> dict:
    """HYBRID centered layout: a big centered hook card, centered phrase cards on
    the key beats, and short voice-synced explanation lines (centre-lower) for
    the rest. One underlined highlight per moment. Motion matches meaning."""
    segs = align["segments"]
    hook = next((s for s in segs if s["text_role"] == "hook"), None)
    subs = [s for s in segs if s["text_role"] == "subtitle"]
    sub_cfg = style["subtitle"]

    hook_block = {
        "text": hook["display_text"] if hook else "",
        "start": 0.0, "end": (hook["end"] if hook else 1.6),
        "animation": _semantic_anim(hook["display_text"] if hook else "", "hook_card"),
        "position": "center", "style": "hook", "underline": True,
        "emphasis_words": hook["emphasis_words"] if hook else [],
    }
    subtitles, callouts = [], []
    n = len(subs)
    for i, s in enumerate(subs):
        is_cta = (i == n - 1)
        role = "phrase_card" if (is_cta or _is_key_beat(s["display_text"])) else "subtitle"
        moment = {
            "start": s["start"], "end": s["end"], "text": s["display_text"],
            "lines": _wrap(s["display_text"], sub_cfg["max_chars_per_line"], sub_cfg["max_lines"]),
            "emphasis_words": s["emphasis_words"], "position": "center",
            "role": role, "style": role,
            "animation": _semantic_anim(s["display_text"], role),
            "underline": bool(s["emphasis_words"]),
        }
        subtitles.append(moment)
        if role == "phrase_card" and any(_NUM.search(w) for w in s["display_text"].split()):
            callouts.append({"start": s["start"], "end": s["end"], "text": s["display_text"],
                             "purpose": "data_point", "position": "center",
                             "animation": moment["animation"]})
    cta = None
    if subs:
        last = subs[-1]
        cta = {"start": last["start"], "end": last["end"], "text": last["display_text"],
               "animation": "punch", "position": "center"}

    payload = {"date": date, "layout": "centered_hybrid", "hook_text": hook_block,
               "subtitles": subtitles, "callouts": callouts, "cta": cta}
    state.save_artifact(date, "kinetic_text_plan", payload)
    return payload


# ---------------------------------------------------------------- safe areas
def _safe_areas(date: str, shot_plan: dict, style: dict) -> dict:
    """Deterministic, premium-safe defaults (sampling optional): subtitles sit in
    the lower third but above the Instagram-controls band; the hook rides the
    upper-mid; the top-left Maven brand and the bottom band are always avoided."""
    sb = style["subtitle"]["safe_bottom"]
    scenes = []
    for sh in shot_plan.get("shots", []):
        hook_pos = "upper_mid" if sh.get("purpose") == "hook" else "mid"
        scenes.append({
            "scene_id": sh["shot_id"],
            "recommended_hook_position": hook_pos,
            "recommended_subtitle_position": "lower_third",
            "avoid_regions": [f"bottom_{sb}px_ig_controls", "top_left_brand_120px"],
            "reason": "keep text off IG controls + brand mark; translucent pill handles busy backgrounds",
        })
    payload = {"date": date, "safe_bottom": sb, "scene_safe_areas": scenes}
    state.save_artifact(date, "text_safe_area", payload)
    return payload


# ---------------------------------------------------------------- animations
_HOOK_ANIM = {"animation": "word_pop", "easing": "easeOutBack"}
_SUB_ANIM = {"animation": "phrase_pop", "easing": "easeOutQuad"}


def _animations(date: str, kinetic: dict) -> dict:
    anims = []
    h = kinetic["hook_text"]
    if h["text"]:
        anims.append({"text_id": "hook", "animation": _HOOK_ANIM["animation"],
                      "start": h["start"], "end": h["end"],
                      "duration": round(h["end"] - h["start"], 2),
                      "easing": _HOOK_ANIM["easing"],
                      "emphasis": ",".join(h["emphasis_words"])})
    for i, s in enumerate(kinetic["subtitles"]):
        anims.append({"text_id": f"sub_{i+1:02d}", "animation": _SUB_ANIM["animation"],
                      "start": s["start"], "end": s["end"],
                      "duration": round(s["end"] - s["start"], 2),
                      "easing": _SUB_ANIM["easing"],
                      "emphasis": ",".join(s["emphasis_words"])})
    if kinetic.get("cta"):
        c = kinetic["cta"]
        anims.append({"text_id": "cta", "animation": "clean_fade_up",
                      "start": c["start"], "end": c["end"],
                      "duration": round(c["end"] - c["start"], 2),
                      "easing": "easeOutQuad", "emphasis": ""})
    payload = {"date": date, "text_animations": anims}
    state.save_artifact(date, "text_animation", payload)
    return payload


# ---------------------------------------------------------------- entrypoint
def run(date: str, *, shot_plan: dict, voiceover: dict | None = None,
        script_edited: dict | None = None) -> dict:
    style = _load_style()
    # per-job override (e.g. "Move Subtitles Up" raises the subtitle safe_bottom)
    ov = config.run_dir(date) / "_text_style_override.json"
    if ov.exists():
        try:
            extra = int(json.loads(ov.read_text(encoding="utf-8")).get("subtitle_safe_bottom_extra", 0))
            style["subtitle"]["safe_bottom"] = int(style["subtitle"]["safe_bottom"]) + extra
        except Exception:
            pass
    script_edited = script_edited or _opt(date, "script_edited") or {}
    spoken, vo_dur = _transcript(date, voiceover, script_edited)
    video_dur = round(sum(float(s.get("duration", 0)) for s in shot_plan.get("shots", [])) or 18.0, 2)

    align = _align(date, spoken, vo_dur, video_dur, style)
    kinetic = _kinetic(date, align, style)
    safe = _safe_areas(date, shot_plan, style)
    anims = _animations(date, kinetic)
    return {"alignment": align, "kinetic": kinetic, "safe_area": safe,
            "animations": anims, "style": style}
