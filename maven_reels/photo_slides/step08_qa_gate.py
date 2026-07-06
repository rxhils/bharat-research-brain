"""Agent 9 — QA Gate.

Deterministic pre-approval gate. Thresholds (spec): facts >= 95,
design >= 90, readability >= 92, format pass, compliance pass, overall >= 92.
Simulated research can NEVER pass — the gate is where honesty is enforced.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from . import config, state
from .step02_fact_check import banned_language


def _score_facts(fc: dict, sel: dict, issues: list[str], fixes: list[str]) -> int:
    story = sel.get("selected_story") or {}
    if not story:
        issues.append("no verified story selected")
        fixes.append("re-run research on a trading day / with providers configured")
        return 0
    if story.get("simulated"):
        issues.append("SIMULATION story — facts cannot be verified")
        fixes.append("run with live research before review/export")
        return 0
    conf = story.get("fact_confidence", 0)
    srcs = [s for s in story.get("sources", []) if s.get("url")]
    score = 55 + min(len(srcs), 2) * 15 + (15 if conf >= 70 else 5)
    if conf >= 80:
        score += 10
    if not srcs:
        issues.append("selected story has no source URL")
        fixes.append("reject the story; every claim needs a source")
        score = 0
    return min(score, 100)


def _score_sources(fc: dict) -> int:
    return fc.get("source_confidence", 0)


def _score_design(design: dict, issues: list[str], fixes: list[str]) -> int:
    imgs = design.get("generated_images", [])
    if len(imgs) != config.SLIDE_COUNT:
        issues.append(f"{len(imgs)}/{config.SLIDE_COUNT} slides rendered")
        fixes.append("regenerate the full slide set")
        return 0
    score = 100
    for i in imgs:
        p = Path(i.get("path", ""))
        if not p.exists():
            issues.append(f"slide {i.get('slide_number')} file missing")
            score -= 40
            continue
        with Image.open(p) as im:
            if im.size != (config.SLIDE_W, config.SLIDE_H):
                issues.append(f"slide {i.get('slide_number')} is {im.size}, "
                              f"not {config.SLIDE_W}x{config.SLIDE_H}")
                score -= 30
        if not i.get("fonts_bundled", False):
            issues.append(f"slide {i.get('slide_number')} rendered without brand fonts")
            fixes.append("restore maven_reels/assets/fonts/*.ttf")
            score -= 15
        if str(i.get("background_source", "")).startswith("higgsfield_failed"):
            issues.append(f"slide {i.get('slide_number')} Higgsfield background "
                          "failed (local fallback used)")
            score -= 4
    return max(score, 0)


def _score_readability(script: dict, design: dict, issues: list[str],
                       fixes: list[str]) -> int:
    score = 100
    for s in script.get("slides", []):
        n = s["slide_number"]
        tw, bw = len(s["title"].split()), len(s["body"].split())
        if tw > config.TITLE_MAX_WORDS:
            issues.append(f"slide {n} title is {tw} words (max {config.TITLE_MAX_WORDS})")
            fixes.append(f"shorten slide {n} title")
            score -= 15
        if bw > config.BODY_MAX_WORDS:
            issues.append(f"slide {n} body is {bw} words (max {config.BODY_MAX_WORDS})")
            fixes.append(f"shorten slide {n} body")
            score -= 15
        if not s["title"].strip() or not s["body"].strip():
            issues.append(f"slide {n} has empty text")
            score -= 25
        if re.search(r"(.)\1{3,}", s["title"] + s["body"]):
            issues.append(f"slide {n} text looks corrupted/gibberish")
            score -= 25
    for i in design.get("generated_images", []):
        if i.get("body_px", 0) < 40 or i.get("title_px", 0) < 60:
            issues.append(f"slide {i.get('slide_number')} text too small for phones")
            score -= 10
    return max(score, 0)


def _format_pass(script: dict, design: dict, issues: list[str]) -> bool:
    slides = script.get("slides", [])
    ok = (len(slides) == config.SLIDE_COUNT
          and [s["slide_number"] for s in slides] == [1, 2, 3, 4, 5]
          and len(design.get("generated_images", [])) == config.SLIDE_COUNT)
    if not ok:
        issues.append("format: need exactly 5 slides in order 1-5, all rendered")
    return ok


def _compliance_pass(script: dict, issues: list[str], fixes: list[str]) -> bool:
    ok = True
    all_text = " ".join(f"{s['title']} {s['body']}" for s in script.get("slides", []))
    hits = banned_language(all_text + " " + script.get("caption", ""))
    if hits:
        issues.append(f"advisory/banned language present: {', '.join(sorted(set(hits)))}")
        fixes.append("rewrite without advisory language")
        ok = False
    slides = script.get("slides", [])
    last = slides[-1] if slides else {}
    disc = (config.DISCLAIMER.lower()[:20] in
            (last.get("source_note", "") + last.get("body", "")).lower()
            or "not investment advice" in (last.get("source_note", "")
                                           + last.get("body", "")).lower())
    if not disc:
        issues.append("slide 5 is missing the disclaimer")
        fixes.append("add the disclaimer to slide 5")
        ok = False
    if "not investment advice" not in script.get("caption", "").lower():
        issues.append("caption is missing the disclaimer")
        fixes.append("append the disclaimer to the caption")
        ok = False
    return ok


def run(job_id: str) -> dict:
    fc = state.load_artifact(job_id, "fact_check") or {}
    sel = state.load_artifact(job_id, "story_selector") or {}
    script = state.load_artifact(job_id, "slide_script") or {}
    design = state.load_artifact(job_id, "slide_design") or {}

    issues: list[str] = []
    fixes: list[str] = []
    scores = {
        "facts": _score_facts(fc, sel, issues, fixes),
        "source_quality": _score_sources(fc),
        "design": _score_design(design, issues, fixes),
        "readability": _score_readability(script, design, issues, fixes),
    }
    fmt_ok = _format_pass(script, design, issues)
    comp_ok = _compliance_pass(script, issues, fixes)
    scores["format"] = 100 if fmt_ok else 0
    scores["compliance"] = 100 if comp_ok else 0

    overall = round(sum(scores.values()) / len(scores))
    t = config.QA_THRESHOLDS
    passed = (scores["facts"] >= t["facts"] and scores["design"] >= t["design"]
              and scores["readability"] >= t["readability"] and fmt_ok
              and comp_ok and overall >= t["overall"])

    payload = {
        "passed": passed,
        "overall_score": overall,
        "scores": scores,
        "thresholds": t,
        "issues": issues,
        "required_fixes": sorted(set(fixes)),
        "generated_at": config.now_ist().isoformat(timespec="seconds"),
    }
    state.save_artifact(job_id, "qa_gate", payload)
    return payload
