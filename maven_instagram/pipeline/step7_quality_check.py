"""Step 7 — Quality gate before publishing.

Three scores, all must clear their threshold (content>=90, design>=90,
compliance>=95) or the pipeline refuses to publish.

  * compliance_score  — fully automated (banned-word scan + disclaimer present).
  * content_quality   — fully automated (completeness: every slide has its
                        parts, sources cited, caption structured, hashtags ok).
  * design_quality    — mechanical checks here (3 images, exact 1080x1350 JPEG,
                        <8MB). The *aesthetic* judgement ("is it premium, not
                        basic AI") cannot be made by a script, so a visual
                        reviewer supplies ``aesthetic_score`` (0..100); we take
                        the min of mechanical and aesthetic. If none supplied,
                        design is marked "needs_visual_review" and gate fails.
"""
from __future__ import annotations

from pathlib import Path

from . import compliance, state
from .config import (IMAGE_MAX_BYTES, IMAGE_TARGET_H, IMAGE_TARGET_W,
                     QUALITY_GATES)


def _content_score(content_plan: dict, research: dict, caption: dict,
                   hashtags: dict) -> tuple[int, list[str]]:
    issues: list[str] = []
    score = 100
    for slide in content_plan["carousel_plan"]:
        if not slide.get("headline"):
            issues.append(f"slide {slide['slide']}: missing headline"); score -= 10
        if not (2 <= len(slide.get("bullets", [])) <= 3):
            issues.append(f"slide {slide['slide']}: needs 2-3 bullets"); score -= 8
        if not slide.get("takeaway"):
            issues.append(f"slide {slide['slide']}: missing takeaway"); score -= 8
        if "source" not in slide.get("source_footer", "").lower():
            issues.append(f"slide {slide['slide']}: missing source footer"); score -= 8
    if not all(s.get("sources") for s in research["top_3_stories"]):
        issues.append("a story is missing sources"); score -= 15
    if caption.get("char_count", 0) < 80:
        issues.append("caption too short"); score -= 10
    if not (10 <= len(hashtags.get("hashtags", [])) <= 18):
        issues.append("hashtag count out of range"); score -= 10
    return max(0, score), issues


def _design_score(images: dict, aesthetic_score: int | None) -> tuple[int, list[str], dict]:
    issues: list[str] = []
    mechanical = 100
    checked = []
    finals = images.get("finals", [])
    if len(finals) != 3:
        issues.append(f"expected 3 images, found {len(finals)}")
        mechanical -= 40
    for f in finals:
        p = Path(f.get("path", ""))
        ok = p.exists()
        dims_ok = f.get("width") == IMAGE_TARGET_W and f.get("height") == IMAGE_TARGET_H
        size_ok = 0 < f.get("bytes", 0) <= IMAGE_MAX_BYTES
        jpg_ok = str(p).lower().endswith((".jpg", ".jpeg"))
        if not ok:
            issues.append(f"missing file: {p}"); mechanical -= 15
        if not dims_ok:
            issues.append(f"{p.name}: not {IMAGE_TARGET_W}x{IMAGE_TARGET_H}"); mechanical -= 10
        if not size_ok:
            issues.append(f"{p.name}: byte size out of range"); mechanical -= 10
        if not jpg_ok:
            issues.append(f"{p.name}: not JPEG"); mechanical -= 10
        checked.append({"file": p.name, "exists": ok, "dims_ok": dims_ok,
                        "size_ok": size_ok, "jpeg": jpg_ok})
    mechanical = max(0, mechanical)

    if aesthetic_score is None:
        issues.append("aesthetic (visual) review not supplied — needs_visual_review")
        design = min(mechanical, 0)  # cannot pass without a visual review
    else:
        design = min(mechanical, aesthetic_score)
    return design, issues, {"mechanical": mechanical, "aesthetic": aesthetic_score,
                            "per_image": checked}


def run(date: str, *, research: dict, content_plan: dict, images: dict,
        caption: dict, hashtags: dict, aesthetic_score: int | None = None) -> dict:
    content_score, content_issues = _content_score(content_plan, research,
                                                    caption, hashtags)
    design_score, design_issues, design_detail = _design_score(images, aesthetic_score)

    comp = compliance.evaluate(
        {"content_plan": content_plan, "caption": caption},
        require_disclaimer_in=caption.get("caption", ""),
    )

    scores = {"content": content_score, "design": design_score,
              "compliance": comp.score}
    gates = QUALITY_GATES
    passed = {k: scores[k] >= gates[k] for k in gates}
    overall_pass = all(passed.values())

    payload = {
        "date": date,
        "quality_scores": scores,
        "gates": gates,
        "passed": passed,
        "overall_pass": overall_pass,
        "content_issues": content_issues,
        "design_issues": design_issues,
        "design_detail": design_detail,
        "compliance_violations": comp.violations,
        "verdict": "PUBLISH_OK" if overall_pass else "BLOCKED",
    }
    state.save_artifact(date, "quality", payload)
    return payload
