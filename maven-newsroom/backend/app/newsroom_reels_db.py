"""Database Schema Agent — isolated SQLite persistence for Newsroom Reels.

Separate database file (newsroom_reels.db) from the shared newsroom.db so the
existing Carousel/Higgsfield-Reels tables are never touched. Every table uses
the reels_ prefix. Structured data lives here; all media files live on
E:\\MavenReels (paths stored as text, guarded by the Storage Validation Agent).
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("NEWSROOM_REELS_DB", BACKEND_DIR / "data" / "newsroom_reels.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS reels_daily_runs (
  run_id TEXT PRIMARY KEY, run_date TEXT UNIQUE,
  target_reels INTEGER DEFAULT 15, target_podcasts INTEGER DEFAULT 3,
  clips_per_podcast INTEGER DEFAULT 5, storage_root TEXT,
  status TEXT DEFAULT 'planned',        -- planned|running|complete|incomplete|blocked
  reels_ready INTEGER DEFAULT 0, block_reason TEXT,
  created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_sources (
  source_id TEXT PRIMARY KEY, name TEXT, platform TEXT, channel_url TEXT,
  authority_score INTEGER, india_relevance_score INTEGER,
  audio_video_quality_score INTEGER, educational_density_score INTEGER,
  engagement_quality_score INTEGER, historical_clip_yield_score INTEGER,
  sensationalism_penalty INTEGER, compliance_risk_score INTEGER,
  source_score INTEGER, passed INTEGER DEFAULT 0,
  last_scanned_at TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_episodes (
  episode_id TEXT PRIMARY KEY, source_id TEXT, run_id TEXT,
  title TEXT, url TEXT, published_at TEXT, duration_sec INTEGER,
  views INTEGER, views_per_hour REAL, comments_per_hour REAL, like_ratio REAL,
  episode_viral_score INTEGER, topic_relevance_score INTEGER,
  guest TEXT, status TEXT DEFAULT 'discovered',
  video_path TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_transcripts (
  transcript_id TEXT PRIMARY KEY, episode_id TEXT,
  method TEXT,                          -- youtube_captions|auto_captions|whisperx
  language TEXT, path TEXT, segment_count INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_segments (
  segment_id TEXT PRIMARY KEY, episode_id TEXT,
  start_ts TEXT, end_ts TEXT, duration_sec REAL, speaker TEXT,
  text TEXT, context_before TEXT, context_after TEXT, topic_tags TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_segment_scores (
  segment_id TEXT PRIMARY KEY,
  indian_relevance_score INTEGER, virality_score INTEGER,
  compliance_risk_score INTEGER, compliance_flags_json TEXT,
  context_safety_score INTEGER, video_perception_score INTEGER,
  uniqueness_score INTEGER, final_clip_score REAL,
  passed INTEGER DEFAULT 0, reject_reason TEXT, scored_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_clip_candidates (
  clip_id TEXT PRIMARY KEY, segment_id TEXT, episode_id TEXT, run_id TEXT,
  rank_in_episode INTEGER, start_ts TEXT, end_ts TEXT,
  clip_path TEXT, ffmpeg_command TEXT,
  status TEXT DEFAULT 'planned',        -- planned|built|watched|rejected|approved_for_render
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_video_watch_reports (
  report_id TEXT PRIMARY KEY, subject_type TEXT,  -- source|candidate|final
  subject_id TEXT, watch_score INTEGER, notes_json TEXT,
  passed INTEGER DEFAULT 0, report_path TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_edit_plans (
  plan_id TEXT PRIMARY KEY, clip_id TEXT,
  hook_text TEXT, hook_options_json TEXT, captions_path TEXT,
  storyboard_json TEXT, template TEXT, accent_color TEXT,
  ig_caption TEXT, hashtags TEXT, disclaimer TEXT, attribution TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_renders (
  render_id TEXT PRIMARY KEY, clip_id TEXT, run_id TEXT,
  render_path TEXT, thumbnail_path TEXT,
  width INTEGER DEFAULT 1080, height INTEGER DEFAULT 1920, fps INTEGER,
  duration_sec REAL, status TEXT DEFAULT 'pending',  -- pending|rendering|done|failed
  error TEXT, created_at TEXT, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_qa_reports (
  qa_id TEXT PRIMARY KEY, render_id TEXT,
  final_render_watch_score INTEGER, checks_json TEXT,
  passed INTEGER DEFAULT 0, fail_reasons TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_review_decisions (
  decision_id TEXT PRIMARY KEY, render_id TEXT, run_id TEXT,
  decision TEXT,                        -- approve|reject|revise
  reason TEXT, revise_instruction TEXT, decided_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_memory_patterns (
  pattern_id TEXT PRIMARY KEY, pattern_type TEXT,  -- source|topic|hook|template
  pattern_key TEXT, boost REAL DEFAULT 0,
  approvals INTEGER DEFAULT 0, rejections INTEGER DEFAULT 0,
  notes TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_publish_jobs (
  publish_id TEXT PRIMARY KEY, render_id TEXT, decision_id TEXT,
  status TEXT DEFAULT 'queued',         -- queued|stubbed|published|failed
  platform TEXT DEFAULT 'instagram', media_id TEXT, permalink TEXT,
  error TEXT, created_at TEXT, published_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_agent_logs (
  log_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT, agent TEXT, queue TEXT, level TEXT DEFAULT 'info',
  message TEXT, payload_json TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS reels_queue_jobs (
  job_id INTEGER PRIMARY KEY AUTOINCREMENT,
  queue TEXT NOT NULL, run_id TEXT, subject_id TEXT,
  payload_json TEXT, status TEXT DEFAULT 'queued',  -- queued|running|done|failed|dead
  attempts INTEGER DEFAULT 0, max_attempts INTEGER DEFAULT 3,
  error TEXT, created_at TEXT, started_at TEXT, finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_reels_queue_status ON reels_queue_jobs(queue, status);
CREATE INDEX IF NOT EXISTS idx_reels_segments_ep ON reels_segments(episode_id);
CREATE INDEX IF NOT EXISTS idx_reels_clips_run ON reels_clip_candidates(run_id);
CREATE INDEX IF NOT EXISTS idx_reels_logs_run ON reels_agent_logs(run_id);
"""


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def table_names() -> list[str]:
    with connect() as c:
        rows = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return sorted(r["name"] for r in rows)


def upsert(table: str, data: dict, conflict_keys: Iterable[str]) -> None:
    if not table.startswith("reels_"):
        raise ValueError(f"newsroom_reels_db only writes reels_ tables, got: {table}")
    cols = list(data.keys())
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c not in conflict_keys)
    sql = (f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT({','.join(conflict_keys)}) DO UPDATE SET {updates}")
    with connect() as c:
        c.execute(sql, [data[k] for k in cols])


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with connect() as c:
        row = c.execute(sql, params).fetchone()
    return dict(row) if row else None


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
