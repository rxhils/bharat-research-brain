"""Structured event bus — one emit, four sinks.

emit_event() writes to: SQLite `events`, a per-job JSONL file, in-memory asyncio
queues (SSE), and the Telegram bridge (important events only). One event path so
the UI and Telegram never drift. Every event is enriched with the node's honest
class/type/intelligent fields from the registry.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from . import database as db
from .config import EVENTS_JSONL_DIR
from .registry import node as get_node
from .registry_photo_slides import photo_node as get_photo_node
from .registry_reels import reel_node as get_reel_node

IST = timezone(timedelta(hours=5, minutes=30))


def _resolve_node(job_id: str, node_id: str | None) -> dict:
    """Pick the right registry by job_id: reel jobs -> reel registry,
    photo-reel (preel-) jobs -> photo-slides registry, else carousel."""
    if not node_id:
        return {}
    jid = str(job_id)
    if jid.startswith("reel-"):
        return get_reel_node(node_id)
    if jid.startswith("preel-"):
        return get_photo_node(node_id)
    return get_node(node_id)

TELEGRAM_EVENTS = {
    "job.created", "job.started", "job.skipped_market_closed", "job.completed",
    "job.failed", "quality.passed", "quality.failed", "approval.required",
    "publish.completed", "publish.failed",
}
TELEGRAM_NODES = {"market_sentinel", "nano_studio", "ig_courier"}


def now_ist() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = {}
        self._telegram_enabled = False
        self._telegram_verbose = False

    def subscribe(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._subs.setdefault(job_id, set()).add(q)
        return q

    def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        subs = self._subs.get(job_id)
        if subs and q in subs:
            subs.discard(q)
            if not subs:
                self._subs.pop(job_id, None)

    def configure_telegram(self, enabled: bool, verbose: bool) -> None:
        self._telegram_enabled = enabled
        self._telegram_verbose = verbose

    def emit(self, job_id: str, node_id: str | None, event_type: str,
             message: str, *, status: str = "", progress: int = 0,
             payload: dict | None = None,
             artifact_refs: list | None = None) -> dict:
        meta = _resolve_node(job_id, node_id)
        event = {
            "event_id": uuid.uuid4().hex,
            "seq": db.next_seq(),
            "job_id": job_id,
            "node_id": node_id or "",
            "node_name": meta.get("name", ""),
            "actual_component": meta.get("actual_component", ""),
            "component_class": meta.get("component_class", ""),
            "component_type": meta.get("component_type", ""),
            "intelligent": int(bool(meta.get("intelligent", False))),
            "event_type": event_type,
            "status": status,
            "message": message,
            "progress": int(progress or 0),
            "payload_json": db.dumps(payload or {}),
            "artifact_refs_json": db.dumps(artifact_refs or []),
            "timestamp": now_ist(),
        }
        db.upsert("events", event, conflict_keys=["event_id"])
        self._write_jsonl(job_id, event)
        self._push(job_id, event)
        self._maybe_telegram(event)
        return event

    def _write_jsonl(self, job_id: str, event: dict) -> None:
        try:
            with (EVENTS_JSONL_DIR / f"{job_id}.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(db.dumps(event) + "\n")
        except Exception:
            pass

    def _push(self, job_id: str, event: dict) -> None:
        for q in list(self._subs.get(job_id, ())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def _maybe_telegram(self, event: dict) -> None:
        if not self._telegram_enabled:
            return
        et = event["event_type"]
        worthy = self._telegram_verbose or et in TELEGRAM_EVENTS
        if et == "node.completed" and not self._telegram_verbose:
            worthy = event["node_id"] in TELEGRAM_NODES
        if worthy:
            self.emit_telegram_stub(event)

    def emit_telegram_stub(self, event: dict) -> None:
        # No-op courier until a bot token is configured (kept honest).
        return None


bus = EventBus()


def emit_event(job_id: str, node_id: str | None, event_type: str, message: str,
               payload: dict | None = None, **kw) -> dict:
    """Module-level convenience matching the spec signature."""
    return bus.emit(job_id, node_id, event_type, message, payload=payload, **kw)
