"""SQLite persistence for jobs, nodes, events, artifacts and scores.

Single-file local DB. A short-lived connection per call (check_same_thread=False
+ WAL) lets the background runner and request handlers write without locking.
The schema is rebuilt from real run artifacts on startup, so it is safe to
delete newsroom.db at any time.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  run_type TEXT, date TEXT, status TEXT, current_node TEXT,
  market_status TEXT, scheduled_time TEXT, started_at TEXT, completed_at TEXT,
  approval_status TEXT, publish_status TEXT,
  instagram_post_id TEXT, instagram_post_url TEXT,
  summary TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT, node_id TEXT, node_name TEXT,
  component_class TEXT, component_type TEXT, intelligent INTEGER DEFAULT 0,
  actual_component TEXT, external INTEGER DEFAULT 0, in_graph INTEGER DEFAULT 1,
  role TEXT, status TEXT, ord INTEGER,
  started_at TEXT, completed_at TEXT, duration_ms INTEGER,
  retry_count INTEGER DEFAULT 0, progress INTEGER DEFAULT 0,
  input_artifact TEXT, output_artifact TEXT, summary TEXT, error TEXT,
  UNIQUE(job_id, node_id)
);
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY, seq INTEGER, job_id TEXT,
  node_id TEXT, node_name TEXT, actual_component TEXT,
  component_class TEXT, component_type TEXT, intelligent INTEGER DEFAULT 0,
  event_type TEXT, status TEXT, message TEXT, progress INTEGER DEFAULT 0,
  payload_json TEXT, artifact_refs_json TEXT, timestamp TEXT
);
CREATE TABLE IF NOT EXISTS artifacts (
  artifact_id TEXT PRIMARY KEY, job_id TEXT, node_id TEXT,
  artifact_type TEXT, name TEXT, path TEXT, preview_url TEXT,
  created_at TEXT, metadata_json TEXT
);
CREATE TABLE IF NOT EXISTS scores (
  job_id TEXT PRIMARY KEY,
  content_score INTEGER, design_score INTEGER, compliance_score INTEGER,
  aesthetic_score INTEGER, brand_score INTEGER,
  publish_allowed INTEGER, issues_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, seq);
CREATE INDEX IF NOT EXISTS idx_nodes_job ON nodes(job_id, ord);
CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id);
"""


@contextmanager
def connect():
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


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    for k, v in list(d.items()):
        if k.endswith("_json") and isinstance(v, str):
            try:
                d[k[:-5]] = json.loads(v)
            except Exception:
                d[k[:-5]] = None
    if "intelligent" in d:
        d["intelligent"] = bool(d["intelligent"])
    return d


def upsert(table: str, data: dict, conflict_keys: Iterable[str]) -> None:
    cols = list(data.keys())
    placeholders = ",".join("?" for _ in cols)
    updates = ",".join(f"{c}=excluded.{c}" for c in cols if c not in conflict_keys)
    sql = (f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) "
           f"ON CONFLICT({','.join(conflict_keys)}) DO UPDATE SET {updates}")
    with connect() as c:
        c.execute(sql, [data[k] for k in cols])


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as c:
        return [_row_to_dict(r) for r in c.execute(sql, params).fetchall()]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    with connect() as c:
        return _row_to_dict(c.execute(sql, params).fetchone())


def next_seq() -> int:
    with connect() as c:
        row = c.execute("SELECT COALESCE(MAX(seq),0)+1 AS n FROM events").fetchone()
        return int(row["n"])


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
