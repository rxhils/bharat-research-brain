"""Agent — Slide Design Judge (visual quality gate).

Scores the DESIGN of the rendered package: cover strength, visual richness,
story-specific motif relevance, layout variety, readability, typography,
premium feel, brand consistency, no fake AI text, no clutter. Deterministic —
computed from the compositor's honest render reports, never guessed.

Pass thresholds (spec): overall >= 92, slide_1_cover >= 94,
visual_richness >= 90, layout_variety >= 90, readability >= 92,
premium_feel >= 90.
"""
from __future__ import annotations

from . import config, state, visual_motifs

THRESHOLDS = {"overall": 92, "slide_1_cover": 94, "visual_richness": 90,
              "layout_variety": 90, "readability": 92, "premium_feel": 90}

_GRAPHIC_ELEMENTS = {  # elements that count as real visual storytelling
    "gauge_arc", "needle", "metric_card", "block_grid", "accent_block",
    "index_bar", "sector_bars", "pillar", "pulse_rings", "signal_dot",
    "node_grid", "links", "focus_node", "wave_line", "meter_track",
    "meter_marker", "phone", "market_layers", "focus_ring", "flow_cards",
    "arrows", "outcome_accent", "card_stack", "body_glass_card",
    "takeaway_glass_card", "brand_monogram", "cta_chip", "theme_chip",
    "cause_chips", "disclaimer_strip",
}
MAX_ELEMENTS = 9   # beyond this a slide reads as cluttered


def _cover_score(imgs: list[dict], issues: list[str], fixes: list[str]) -> int:
    hook = next((i for i in imgs if i.get("slide_number") == 1), None)
    if not hook:
        issues.append("no slide 1 rendered")
        return 0
    score = 60
    graphics = _GRAPHIC_ELEMENTS & set(hook.get("visual_elements", []))
    if graphics:
        score += 18
    else:
        issues.append("cover slide has no visual motif graphic")
        fixes.append("slide 1: use Make Cover Stronger / Add Finance Graphic")
    tpx = hook.get("title_px", 0)
    if tpx >= 100:
        score += 12
    elif tpx >= 88:                       # 4-line cover at ~90px still dominates
        score += 8
    else:
        issues.append("cover headline is not dominant enough")
        fixes.append("slide 1: shorten the title / Make Cover Stronger")
    if len(hook.get("visual_elements", [])) >= 5:
        score += 10
    return min(score, 100)


def _richness(imgs: list[dict], issues: list[str], fixes: list[str]) -> int:
    per = []
    for i in imgs:
        graphics = _GRAPHIC_ELEMENTS & set(i.get("visual_elements", []))
        n_total = len(i.get("visual_elements", []))
        per.append(min(100, 42 + len(graphics) * 16 + min(n_total, 7) * 2))
        if not graphics:
            issues.append(f"slide {i.get('slide_number')} has no graphic "
                          "element — looks like a plain text card")
            fixes.append(f"slide {i.get('slide_number')}: Add Finance Graphic")
    return round(sum(per) / len(per)) if per else 0


def _variety(imgs: list[dict], issues: list[str], fixes: list[str]) -> int:
    layouts = [i.get("layout") for i in imgs]
    distinct = len(set(layouts))
    if distinct <= 2:
        issues.append("slides share the same layout — no visual progression")
        fixes.append("Redesign Layout to differentiate slide roles")
    return round(distinct / max(len(layouts), 1) * 100)


def _relevance(imgs: list[dict], story: dict, issues: list[str],
               fixes: list[str]) -> int:
    if not story:
        return 0
    expected = visual_motifs.story_motif(story)
    story_slides = [i for i in imgs if i.get("slide_number") in (1, 2)]
    hits = sum(1 for i in story_slides if i.get("motif") == expected
               or i.get("motif") in visual_motifs.MOTIFS)
    exact = sum(1 for i in story_slides if i.get("motif") == expected)
    if exact == 0:
        issues.append(f"story slides don't use the story motif "
                      f"({visual_motifs.MOTIFS[expected]['name']})")
        fixes.append("slide 1: Change Motif to the story-matched motif")
        return 70 if hits else 40
    return 100


def _readability(script: dict, imgs: list[dict], issues: list[str],
                 fixes: list[str]) -> int:
    score = 100
    for s in script.get("slides", []):
        n = s["slide_number"]
        if len(s["title"].split()) > config.TITLE_MAX_WORDS:
            issues.append(f"slide {n} title too long")
            score -= 15
        if len(s["body"].split()) > config.BODY_MAX_WORDS:
            issues.append(f"slide {n} body too long")
            score -= 15
    for i in imgs:
        if i.get("body_px", 0) < 38 or i.get("title_px", 0) < 60:
            issues.append(f"slide {i.get('slide_number')} text too small")
            fixes.append(f"slide {i.get('slide_number')}: shorten text")
            score -= 12
    return max(score, 0)


def _premium(imgs: list[dict], issues: list[str], fixes: list[str]) -> int:
    score = 100
    for i in imgs:
        if not i.get("fonts_bundled", False):
            issues.append("brand fonts missing — default font looks cheap")
            fixes.append("restore maven_reels/assets/fonts/*.ttf")
            score -= 30
            break
    if not any("glass" in e for i in imgs
               for e in i.get("visual_elements", [])):
        issues.append("no glass-card depth anywhere in the set")
        score -= 15
    return max(score, 0)


def _clutter_ok(imgs: list[dict], issues: list[str], fixes: list[str]) -> int:
    score = 100
    for i in imgs:
        n = len(i.get("visual_elements", []))
        if n > MAX_ELEMENTS:
            issues.append(f"slide {i.get('slide_number')} has {n} elements — "
                          "cluttered")
            fixes.append(f"slide {i.get('slide_number')}: reduce density")
            score -= 20
    return max(score, 0)


def run(job_id: str) -> dict:
    design = state.load_artifact(job_id, "slide_design") or {}
    script = state.load_artifact(job_id, "slide_script") or {}
    sel = state.load_artifact(job_id, "story_selector") or {}
    story = sel.get("selected_story") or {}
    imgs = sorted(design.get("generated_images", []),
                  key=lambda i: i.get("slide_number", 0))

    issues: list[str] = []
    fixes: list[str] = []
    if len(imgs) != config.SLIDE_COUNT:
        issues.append(f"{len(imgs)}/{config.SLIDE_COUNT} slides rendered")

    scores = {
        "slide_1_cover": _cover_score(imgs, issues, fixes),
        "visual_richness": _richness(imgs, issues, fixes),
        "story_visual_relevance": _relevance(imgs, story, issues, fixes),
        "layout_variety": _variety(imgs, issues, fixes),
        "readability": _readability(script, imgs, issues, fixes),
        "typography": 95 if all(i.get("fonts_bundled") for i in imgs) and imgs else 40,
        "premium_feel": _premium(imgs, issues, fixes),
        "brand_consistency": 96 if imgs else 0,   # brand footer/eyebrow always drawn
        "no_fake_ai_text": 100 if all(
            i.get("text_fidelity") == "exact_local_compositor" for i in imgs)
            and imgs else 0,
        "no_clutter": _clutter_ok(imgs, issues, fixes),
    }
    overall = round(sum(scores.values()) / len(scores))
    t = THRESHOLDS
    passed = (overall >= t["overall"]
              and scores["slide_1_cover"] >= t["slide_1_cover"]
              and scores["visual_richness"] >= t["visual_richness"]
              and scores["layout_variety"] >= t["layout_variety"]
              and scores["readability"] >= t["readability"]
              and scores["premium_feel"] >= t["premium_feel"])
    if not passed and not issues:
        issues.append("design below premium thresholds")

    payload = {
        "passed": passed,
        "overall_score": overall,
        "scores": scores,
        "thresholds": t,
        "issues": issues,
        "required_fixes": sorted(set(fixes)),
        "too_plain": scores["visual_richness"] < t["visual_richness"]
        or scores["slide_1_cover"] < t["slide_1_cover"],
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "design_judge", payload)
    return payload
