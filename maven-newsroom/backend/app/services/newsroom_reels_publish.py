"""Phase 11 agents: Feedback Memory + Publishing Queue.

Feedback Memory learns from approve/reject/revise decisions: it boosts or
penalizes source/topic/hook patterns so future clip planning prefers what the
operator approves without becoming repetitive.

Publishing Queue takes ONLY approved, QA-passed renders and creates spaced
publish jobs. Publishing is stubbed (status='stubbed') until Instagram
credentials are wired; rejected, draft, or QA-failed reels can never be
queued.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from .. import newsroom_reels_db as rdb
from . import newsroom_reels_queue as rq
from .newsroom_reels_creative import _main_topic

# IST publish slots, spaced through the day (spec §11)
PUBLISH_SLOTS_IST = ["09:00", "10:30", "12:00", "13:30", "15:00", "16:30",
                     "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ------------------------------------------------- Agent 26: Feedback Memory

def _patterns_for_render(render_id: str) -> list[tuple[str, str]]:
    row = rdb.query_one(
        "SELECT p.hook_text, g.text, src.name AS source_name, p.template "
        "FROM reels_renders r "
        "JOIN reels_clip_candidates c ON c.clip_id = r.clip_id "
        "LEFT JOIN reels_edit_plans p ON p.clip_id = r.clip_id "
        "LEFT JOIN reels_segments g ON g.segment_id = c.segment_id "
        "LEFT JOIN reels_episodes e ON e.episode_id = c.episode_id "
        "LEFT JOIN reels_sources src ON src.source_id = e.source_id "
        "WHERE r.render_id=?", (render_id,))
    if not row:
        return []
    pats: list[tuple[str, str]] = []
    if row["source_name"]:
        pats.append(("source", row["source_name"]))
    if row["text"]:
        pats.append(("topic", _main_topic(row["text"])))
    if row["hook_text"]:
        first_two = " ".join(row["hook_text"].split()[:2]).lower()
        pats.append(("hook", first_two))
    if row["template"]:
        pats.append(("template", row["template"]))
    return pats


def update_memory(render_id: str, decision: str, reason: str | None = None) -> int:
    """Boost approved patterns, penalize rejected ones. Returns rows touched."""
    delta = 1.0 if decision == "approve" else -1.0 if decision in ("reject", "revise") else 0.0
    touched = 0
    for ptype, key in _patterns_for_render(render_id):
        pattern_id = f"{ptype}:{key}"
        existing = rdb.query_one(
            "SELECT * FROM reels_memory_patterns WHERE pattern_id=?", (pattern_id,))
        approvals = (existing["approvals"] if existing else 0) + (1 if delta > 0 else 0)
        rejections = (existing["rejections"] if existing else 0) + (1 if delta < 0 else 0)
        boost = round((existing["boost"] if existing else 0.0) + delta, 2)
        notes = existing["notes"] if existing else None
        if reason and delta < 0:
            notes = f"{notes + '; ' if notes else ''}{decision}: {reason}"[:500]
        rdb.upsert("reels_memory_patterns", {
            "pattern_id": pattern_id, "pattern_type": ptype, "pattern_key": key,
            "boost": boost, "approvals": approvals, "rejections": rejections,
            "notes": notes, "updated_at": _now(),
        }, ["pattern_id"])
        touched += 1
    return touched


def pattern_boost(ptype: str, key: str) -> float:
    row = rdb.query_one("SELECT boost FROM reels_memory_patterns WHERE pattern_id=?",
                        (f"{ptype}:{key}",))
    return row["boost"] if row else 0.0


# ------------------------------------------------- Agent 27: Publishing Queue

def queue_publish(render_id: str, decision_id: str | None = None) -> dict[str, Any]:
    """Create a publish job — hard-gated on approval + QA pass."""
    dec = rdb.query_one(
        "SELECT * FROM reels_review_decisions WHERE render_id=? "
        "ORDER BY decided_at DESC", (render_id,))
    if not dec or dec["decision"] != "approve":
        raise PermissionError(f"render {render_id} is not approved — will not publish")
    qa = rdb.query_one("SELECT passed FROM reels_qa_reports WHERE render_id=? "
                       "ORDER BY created_at DESC", (render_id,))
    if not qa or not qa["passed"]:
        raise PermissionError(f"render {render_id} has not passed QA — will not publish")
    existing = rdb.query_one(
        "SELECT * FROM reels_publish_jobs WHERE render_id=?", (render_id,))
    if existing:
        return existing

    used = {j["media_id"] for j in rdb.query_all(
        "SELECT media_id FROM reels_publish_jobs WHERE created_at LIKE ?",
        (f"{_now()[:10]}%",))}
    slot = next((s for s in PUBLISH_SLOTS_IST if f"slot-{s}" not in used),
                PUBLISH_SLOTS_IST[-1])

    publish_id = f"pub-{uuid.uuid4().hex[:8]}"
    job = {
        "publish_id": publish_id, "render_id": render_id,
        "decision_id": decision_id or dec["decision_id"],
        # stub until Instagram credentials are wired; media_id records the slot
        "status": "stubbed", "platform": "instagram",
        "media_id": f"slot-{slot}", "created_at": _now(),
    }
    rdb.upsert("reels_publish_jobs", job, ["publish_id"])
    rq.log(None, "publishing_queue", "reels.publish.approved",
           f"{render_id} queued for IST slot {slot} (stubbed — credentials pending)")
    return job


# ------------------------------------------------- queue handlers

async def _handle_memory_update(job: dict[str, Any]) -> None:
    p = job.get("payload", {})
    update_memory(job["subject_id"], p.get("decision", ""), p.get("reason"))


async def _handle_publish_approved(job: dict[str, Any]) -> None:
    queue_publish(job["subject_id"], job.get("payload", {}).get("decision_id"))


async def _handle_review_create(job: dict[str, Any]) -> None:
    rq.log(job.get("run_id"), "review", "reels.review.create",
           f"render {job['subject_id']} ready for review on /newsroom/reels")


rq.register("reels.memory.update", _handle_memory_update)
rq.register("reels.publish.approved", _handle_publish_approved)
rq.register("reels.review.create", _handle_review_create)
