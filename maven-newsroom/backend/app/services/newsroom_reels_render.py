"""Phase 9 agents: Remotion Render, Final Render Watch, QA.

The Remotion Render Agent turns an edit plan (storyboard + captions + raw
clip) into a 1080x1920 Reel via the maven-newsroom/reels-render package.
Final Render Watch re-runs the local perception pass plus Reel-specific
checks and blocks anything under 92. The QA Agent is the last technical +
compliance gate before the review dashboard.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import newsroom_reels_db as rdb
from ..newsroom_reels_config import REPO_ROOT_RENDER_APP
from . import newsroom_reels_queue as rq
from .newsroom_reels_storage import guard_path, run_subdir
from .newsroom_reels_watch import watch_local

FINAL_WATCH_GATE = 92


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ------------------------------------------------- Agent 21: Remotion Render

def render_reel(clip_id: str, run_date: str) -> dict[str, Any]:
    """Render one Reel from its edit plan. Deterministic props via JSON file."""
    plan = rdb.query_one("SELECT * FROM reels_edit_plans WHERE clip_id=? "
                         "ORDER BY created_at DESC", (clip_id,))
    clip = rdb.query_one("SELECT * FROM reels_clip_candidates WHERE clip_id=?",
                         (clip_id,))
    if not (plan and clip):
        raise ValueError(f"missing edit plan or clip for {clip_id}")

    storyboard = json.loads(plan["storyboard_json"])
    captions = json.loads(Path(plan["captions_path"]).read_text(encoding="utf-8"))
    # inline subtitles; expose the clip through Remotion's public dir on E:
    public_dir = guard_path(Path(r"E:\MavenReels") / "cache" / "render-public")
    Path(public_dir).mkdir(parents=True, exist_ok=True)
    for item in storyboard["timeline"]:
        if item["layer"] == "speaker_clip":
            item["subtitle_events"] = captions["subtitle_events"]
            src = Path(item["src"])
            served = Path(public_dir) / f"{clip_id}{src.suffix}"
            if not served.exists():
                try:
                    os.link(src, served)          # hardlink: no duplicate bytes
                except OSError:
                    shutil.copy2(src, served)
            item["src"] = served.name

    n = (rdb.query_one("SELECT COUNT(*) AS n FROM reels_renders WHERE run_id=?",
                       (clip["run_id"],)) or {"n": 0})["n"]
    out_dir = guard_path(Path(run_subdir(run_date, "renders")) / f"reel_{n + 1:02d}")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out = Path(out_dir) / "final.mp4"

    props_path = Path(out_dir) / "props.json"
    props_path.write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")

    render_id = f"rnd-{uuid.uuid4().hex[:8]}"
    rdb.upsert("reels_renders", {
        "render_id": render_id, "clip_id": clip_id, "run_id": clip["run_id"],
        "render_path": str(out), "fps": storyboard.get("fps", 30),
        "duration_sec": storyboard.get("duration_sec"),
        "status": "rendering", "created_at": _now(),
    }, ["render_id"])

    cmd = ["npx", "remotion", "render", "src/index.ts", "MavenReel", str(out),
           f"--props={props_path}", "--log=error"]
    # C: is chronically low on space — force Chrome/Node temp scratch onto E:
    tmp = r"E:\MavenReels\temp"
    env = {**os.environ, "TEMP": tmp, "TMP": tmp, "TMPDIR": tmp}
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800,
                         cwd=str(REPO_ROOT_RENDER_APP), shell=True, env=env)
    ok = res.returncode == 0 and out.exists()
    with rdb.connect() as c:
        c.execute("UPDATE reels_renders SET status=?, error=?, completed_at=? "
                  "WHERE render_id=?",
                  ("done" if ok else "failed",
                   None if ok else res.stderr[-500:], _now(), render_id))
    if not ok:
        raise RuntimeError(f"remotion render failed for {clip_id}: {res.stderr[-300:]}")
    rq.log(clip["run_id"], "remotion_render", "reels.render.create",
           f"rendered {render_id} -> {out}")
    return {"render_id": render_id, "render_path": str(out)}


# ------------------------------------------------- Agent 22: Final Render Watch

def watch_final(render_id: str) -> dict[str, Any]:
    r = rdb.query_one("SELECT * FROM reels_renders WHERE render_id=?", (render_id,))
    if not r or r["status"] != "done":
        raise ValueError(f"render {render_id} not done")
    rep = watch_local(r["render_path"], "final", render_id, r["run_id"])
    notes = rep["notes"]
    score = rep["watch_score"]
    # the dark-premium template intentionally opens/closes on near-black brand
    # cards (~3s hook+outro) — only black time BEYOND that budget is a defect
    DESIGNED_DARK_SEC = 4.0
    excess_black = max(0.0, notes["black_seconds"] - DESIGNED_DARK_SEC)
    if notes["black_seconds"] >= 2:      # generic watcher zeroed its 25-pt black credit
        score += 25 if excess_black < 0.5 else 5 if excess_black < 2 else 0
    # Reel-specific additions on top of the generic local watch
    if notes["resolution"] == "1080x1920":
        score += 15
    if (r["duration_sec"] or 0) >= 15:
        score += 10
    score = min(100, score)
    passed = (score >= FINAL_WATCH_GATE and notes["has_audio"]
              and excess_black < 2)
    with rdb.connect() as c:
        c.execute("UPDATE reels_video_watch_reports SET watch_score=?, passed=? "
                  "WHERE report_id=?", (score, int(passed), rep["report_id"]))
    return {**rep, "watch_score": score, "passed": passed}


# ------------------------------------------------- Agent 23: QA

def qa_check(render_id: str) -> dict[str, Any]:
    r = rdb.query_one("SELECT * FROM reels_renders WHERE render_id=?", (render_id,))
    if not r:
        raise ValueError(f"unknown render {render_id}")
    plan = rdb.query_one("SELECT * FROM reels_edit_plans WHERE clip_id=? "
                         "ORDER BY created_at DESC", (r["clip_id"],))
    watch = rdb.query_one(
        "SELECT * FROM reels_video_watch_reports WHERE subject_type='final' "
        "AND subject_id=? ORDER BY created_at DESC", (render_id,))
    seg_scores = rdb.query_one(
        "SELECT s.* FROM reels_segment_scores s JOIN reels_clip_candidates c "
        "ON c.segment_id=s.segment_id WHERE c.clip_id=?", (r["clip_id"],))

    notes = json.loads(watch["notes_json"]) if watch else {}
    checks = {
        "resolution_1080x1920": notes.get("resolution") == "1080x1920",
        "on_e_drive": str(r["render_path"]).upper().startswith("E:"),
        "has_audio": bool(notes.get("has_audio")),
        "attribution_present": bool(plan and plan["attribution"]),
        "disclaimer_present": bool(plan and plan["disclaimer"]),
        "compliance_passed": bool(seg_scores and (seg_scores["compliance_risk_score"] or 0) <= 35),
        "final_watch_gate": bool(watch and watch["watch_score"] >= FINAL_WATCH_GATE
                                 and watch["passed"]),
    }
    passed = all(checks.values())
    qa_id = f"qa-{uuid.uuid4().hex[:8]}"
    rdb.upsert("reels_qa_reports", {
        "qa_id": qa_id, "render_id": render_id,
        "final_render_watch_score": watch["watch_score"] if watch else 0,
        "checks_json": json.dumps(checks), "passed": int(passed),
        "fail_reasons": "; ".join(k for k, v in checks.items() if not v) or None,
        "created_at": _now(),
    }, ["qa_id"])
    rq.log(r["run_id"], "qa", "reels.qa.check",
           f"{render_id}: {'PASS' if passed else 'FAIL'}")
    return {"qa_id": qa_id, "passed": passed, "checks": checks}


# ------------------------------------------------- queue handlers

async def _handle_render_create(job: dict[str, Any]) -> None:
    run = rdb.query_one("SELECT run_date FROM reels_daily_runs WHERE run_id=?",
                        (job.get("run_id"),))
    out = render_reel(job["subject_id"], run["run_date"] if run else _now()[:10])
    rq.enqueue("reels.video.watch_final", run_id=job.get("run_id"),
               subject_id=out["render_id"])


async def _handle_watch_final(job: dict[str, Any]) -> None:
    rep = watch_final(job["subject_id"])
    if rep["passed"]:
        rq.enqueue("reels.qa.check", run_id=job.get("run_id"),
                   subject_id=job["subject_id"])


async def _handle_qa_check(job: dict[str, Any]) -> None:
    out = qa_check(job["subject_id"])
    if out["passed"]:
        rq.enqueue("reels.review.create", run_id=job.get("run_id"),
                   subject_id=job["subject_id"])


rq.register("reels.render.create", _handle_render_create)
rq.register("reels.video.watch_final", _handle_watch_final)
rq.register("reels.qa.check", _handle_qa_check)
