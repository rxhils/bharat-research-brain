"""Agent 5 — Higgsfield Image Slide Designer.

Plans + produces the 5 vertical 1080x1920 slide images.

Text rendering rule (spec): Higgsfield cannot reliably render exact text, so
Higgsfield only ever generates the premium BACKGROUND visual; the controlled
local compositor draws the exact text on top. Default runs spend ZERO credits
(local editorial gradient backgrounds). Real Higgsfield backgrounds require
REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION -> explicit operator confirmation, and
are reported honestly (never faked on failure).
"""
from __future__ import annotations

from . import compositor, config, state

_NEGATIVE = ("no text, no letters, no words, no numbers, no tickers, no logos, "
             "no watermarks, no charts with fake data, no buy/sell arrows, no "
             "trading-signal graphics, no cluttered dashboard, no people's faces")

_SLIDE_VISUAL = {
    "hook": "dramatic dark editorial finance backdrop, depth-lit newsroom glass "
            "and soft bokeh city lights, premium magazine cover energy",
    "what_happened": "minimal dark editorial background, soft studio gradient "
                     "with a single subtle light sweep, clean negative space",
    "why_it_happened": "abstract premium finance texture, blurred market "
                       "reflections on dark glass, calm and analytical",
    "why_it_matters": "wide subtle skyline dusk silhouette of an Indian metro "
                      "city, dark blue hour, understated and cinematic",
    "maven_takeaway": "elegant dark brand backdrop, soft radial glow center "
                      "frame, quiet confidence, premium fintech aesthetic",
}


def _prompts(slides: list[dict], style_name: str) -> list[dict]:
    accent = config.STYLE_VARIANTS.get(
        style_name, config.STYLE_VARIANTS[config.DEFAULT_STYLE])["accent"]
    out = []
    for s in slides:
        out.append({
            "slide_number": s["slide_number"],
            "model": "nano_banana_pro",
            "prompt": (f"Vertical 9:16 background plate for a premium Indian "
                       f"finance media slide. "
                       f"{_SLIDE_VISUAL.get(s['role'], _SLIDE_VISUAL['what_happened'])}. "
                       f"Deep navy palette with {accent} accent light, high "
                       "contrast, editorial, uncluttered — pure background, "
                       "large empty areas for typography."),
            "negative_prompt": _NEGATIVE,
            "requires_text_fidelity": True,   # -> text is composited locally
        })
    return out


def run(job_id: str, *, use_higgsfield: bool = False,
        credit_confirmed: bool = False,
        style_name: str = config.DEFAULT_STYLE,
        only_slides: list[int] | None = None) -> dict:
    script = state.load_artifact(job_id, "slide_script") or {}
    slides = script.get("slides", [])
    if len(slides) != config.SLIDE_COUNT:
        payload = {"model_plan": [], "slide_prompts": [], "generated_images": [],
                   "status": "blocked", "note": "script does not have exactly 5 slides",
                   "generated_at": config.now_ist().isoformat(timespec="seconds")}
        state.save_artifact(job_id, "slide_design", payload)
        return payload

    prompts = _prompts(slides, style_name)
    prev = state.load_artifact(job_id, "slide_design") or {}
    prev_imgs = {i.get("slide_number"): i for i in prev.get("generated_images", [])}

    hf_allowed = (use_higgsfield
                  and (credit_confirmed or not config.REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION))
    hf_available = False
    hf_note = "local compositor only (zero credits)"
    if use_higgsfield and not hf_allowed:
        hf_note = ("Higgsfield requested but credit confirmation missing — "
                   "REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION is on; rendered "
                   "locally instead (zero credits).")
    if hf_allowed:
        from maven_reels.pipeline import higgsfield_client as hc  # noqa: PLC0415
        hf_available = hc.available()
        if not hf_available:
            hf_note = ("Higgsfield confirmed but no credentials/CLI available — "
                       "rendered locally instead; nothing was faked.")

    images, sdir = [], state.slides_dir(job_id)
    bg_dir = state.job_dir(job_id) / "backgrounds"
    for slide, prompt in zip(slides, prompts, strict=True):
        n = slide["slide_number"]
        if only_slides and n not in only_slides and n in prev_imgs:
            images.append(prev_imgs[n])                     # keep untouched slides
            continue
        bg_path = None
        bg_status = "local_gradient"
        if hf_allowed and hf_available:
            bg_path = bg_dir / f"slide_{n}_bg.png"
            try:
                from maven_reels.pipeline import higgsfield_client as hc  # noqa: PLC0415
                hc.generate_image_to_file(prompt["prompt"], bg_path,
                                          model=prompt["model"], aspect_ratio="9:16")
                bg_status = "higgsfield_real"
            except Exception as exc:  # HiggsfieldError et al — report, don't fake
                bg_path, bg_status = None, f"higgsfield_failed: {exc}"
        report = compositor.render_slide(slide, sdir / f"slide_{n}.png",
                                         style_name=style_name, bg_image=bg_path)
        images.append({"slide_number": n, "path": report["path"],
                       "status": "generated", "background_source": bg_status,
                       **{k: report[k] for k in ("width", "height", "style",
                                                 "fonts_bundled", "title_px",
                                                 "body_px", "text_fidelity")}})

    payload = {
        "model_plan": [{"purpose": "background visual", "model": "nano_banana_pro",
                        "used": hf_allowed and hf_available},
                       {"purpose": "exact text", "model": "local_compositor",
                        "used": True}],
        "slide_prompts": prompts,
        "generated_images": images,
        "style": style_name,
        "higgsfield_note": hf_note,
        "credits_spent": bool(hf_allowed and hf_available
                              and any(i["background_source"] == "higgsfield_real"
                                      for i in images)),
        "status": "designed",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "slide_design", payload)
    return payload
