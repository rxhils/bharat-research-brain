"""Agent 5 — Higgsfield Image Slide Designer.

Plans + produces the 5 designed 1080x1920 slide images. Each slide gets a
STORY-SPECIFIC visual motif (gauge / heatmap / flow / lens / pulse / grid /
mood / split) and a role-specific layout. Text is ALWAYS drawn by the local
compositor (exact, zero credits); Higgsfield may only supply the background
plate — gated behind explicit operator credit confirmation and reported
honestly (never faked on failure).
"""
from __future__ import annotations

from . import compositor, config, state, visual_motifs

NEGATIVE_PROMPT = (
    "plain navy background, empty card, generic dashboard, fake ticker text, "
    "fake stock numbers, company logos, gibberish, distorted letters, "
    "cluttered charts, buy/sell arrows, meme style, cheap Canva look, "
    "low-quality AI design, readable text, numbers, watermarks, faces")

_ROLE_BRIEF = {
    "hook": "bold central composition with a dramatic finance graphic — this is "
            "the scroll-stopping cover",
    "what_happened": "news-brief panel mood, clean card-stack depth",
    "why_it_happened": "explanatory flow composition, three connected panels",
    "why_it_matters": "retail investor point-of-view, focused and personal",
    "maven_takeaway": "calm premium brand end-card, quiet confidence",
}


def _prompts(slides: list[dict], story: dict, style_name: str,
             motif_overrides: dict[str, str]) -> list[dict]:
    accent = config.STYLE_VARIANTS.get(
        style_name, config.STYLE_VARIANTS[config.DEFAULT_STYLE])["accent"]
    theme = story.get("sector_or_theme", "Indian markets")
    out = []
    for s in slides:
        motif_id = visual_motifs.motif_for(
            s["role"], story, motif_overrides.get(str(s["slide_number"])))
        motif = visual_motifs.MOTIFS.get(motif_id, {})
        motif_line = motif.get("higgsfield_background_prompt",
                               "abstract premium market depth")
        out.append({
            "slide_number": s["slide_number"],
            "model": "nano_banana_pro",
            "design_pack": style_name,
            "motif": motif_id,
            "prompt": (
                f"Create a premium vertical 1080x1920 Indian finance media "
                f"background for an Instagram Reel slide. Theme: {theme} — "
                f"{story.get('headline', '')[:80]}. Slide role: "
                f"{s['role'].replace('_', ' ')} — {_ROLE_BRIEF.get(s['role'], '')}. "
                f"Visual motif: {motif_line}. Dark editorial finance style, "
                f"subtle market-grid depth, {accent} accent glow, premium "
                "business-news aesthetic, strong empty safe area for headline "
                "text, no fake logos, no fake tickers, no readable text, "
                "no numbers, no clutter."),
            "negative_prompt": NEGATIVE_PROMPT,
            "requires_text_fidelity": True,   # -> text is composited locally
        })
    return out


def run(job_id: str, *, use_higgsfield: bool = False,
        credit_confirmed: bool = False,
        style_name: str = config.DEFAULT_STYLE,
        only_slides: list[int] | None = None,
        options: dict | None = None) -> dict:
    script = state.load_artifact(job_id, "slide_script") or {}
    slides = script.get("slides", [])
    if len(slides) != config.SLIDE_COUNT:
        payload = {"model_plan": [], "slide_prompts": [], "generated_images": [],
                   "status": "blocked", "note": "script does not have exactly 5 slides",
                   "generated_at": config.now_ist().isoformat(timespec="seconds")}
        state.save_artifact(job_id, "slide_design", payload)
        return payload

    sel = state.load_artifact(job_id, "story_selector") or {}
    story = sel.get("selected_story") or {}
    prev = state.load_artifact(job_id, "slide_design") or {}
    opts = {**prev.get("options", {}), **(options or {})}
    motif_overrides = opts.get("motif_overrides", {})
    prompts = _prompts(slides, story, style_name, motif_overrides)
    prev_imgs = {i.get("slide_number"): i for i in prev.get("generated_images", [])}

    hf_allowed = (use_higgsfield
                  and (credit_confirmed
                       or not config.REQUIRE_HIGGSFIELD_CREDIT_CONFIRMATION))
    hf_available = False
    hf_note = "local designed compositor only (zero credits)"
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
        bg_status = "local_designed"
        if hf_allowed and hf_available:
            bg_path = bg_dir / f"slide_{n}_bg.png"
            try:
                from maven_reels.pipeline import higgsfield_client as hc  # noqa: PLC0415
                hc.generate_image_to_file(prompt["prompt"], bg_path,
                                          model=prompt["model"],
                                          aspect_ratio="9:16")
                bg_status = "higgsfield_real"
            except Exception as exc:  # HiggsfieldError et al — report, don't fake
                bg_path, bg_status = None, f"higgsfield_failed: {exc}"
        report = compositor.render_slide(
            slide, sdir / f"slide_{n}.png", style_name=style_name,
            bg_image=bg_path, story=story, motif_id=prompt["motif"],
            options=opts)
        images.append({"slide_number": n, "path": report["path"],
                       "status": "generated", "background_source": bg_status,
                       **{k: report[k] for k in (
                           "width", "height", "style", "layout", "motif",
                           "visual_elements", "fonts_bundled", "title_px",
                           "body_px", "text_fidelity")}})

    payload = {
        "model_plan": [{"purpose": "background visual", "model": "nano_banana_pro",
                        "used": hf_allowed and hf_available},
                       {"purpose": "designed layout + exact text",
                        "model": "local_compositor", "used": True}],
        "slide_prompts": prompts,
        "generated_images": images,
        "style": style_name,
        "options": opts,
        "higgsfield_note": hf_note,
        "credits_spent": bool(hf_allowed and hf_available
                              and any(i["background_source"] == "higgsfield_real"
                                      for i in images)),
        "status": "designed",
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "slide_design", payload)
    return payload
