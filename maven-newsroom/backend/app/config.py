"""Backend configuration and filesystem anchors.

The backend lives at <repo>/maven-newsroom/backend. The pipeline and its run
artifacts live at <repo>/maven_instagram and <repo>/outputs/maven_instagram.
"""
from __future__ import annotations

import os
from pathlib import Path

# <repo>/maven-newsroom/backend/app/config.py -> parents[3] == <repo>
REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_DIR = REPO_ROOT / "maven_instagram"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "maven_instagram"

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = Path(os.environ.get("NEWSROOM_DB", DATA_DIR / "newsroom.db"))
EVENTS_JSONL_DIR = DATA_DIR / "events"
SETTINGS_PATH = DATA_DIR / "settings.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_JSONL_DIR.mkdir(parents=True, exist_ok=True)

# CORS: the Next.js dashboard.
FRONTEND_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Defaults surfaced on /settings (persisted to settings.json once edited).
DEFAULT_SETTINGS = {
    "schedule_time_ist": "17:00",
    "schedule_label": "5:00 PM IST",
    "run_name": "Closing Bell Run",
    "trigger_agent": "Closing Bell",
    "trading_day_check_enabled": True,
    "auto_publish_enabled": False,
    "human_approval_required": True,
    "thresholds": {"content": 90, "design": 90, "compliance": 95},
    "brand": {
        "name": "Maven",
        "handle": "@try.maven",
        "site": "trymaven.in",
        "palette": ["#05070A", "#0B1117", "#0E1621", "#1FB6A6",
                    "#27C281", "#F2994A", "#EF4444", "#8B5CF6"],
        "logo_path": "",
    },
    "integrations": {
        "instagram": {"account": "try.maven", "type": "BUSINESS",
                      "status": "connected", "via": "Composio MCP"},
        "higgsfield": {"model": "nano_banana_pro", "status": "connected",
                       "via": "Higgsfield MCP"},
        "composio": {"status": "connected", "via": "Composio MCP"},
        "telegram": {"status": "not_configured", "verbose": False},
    },
    "output_folder": str(OUTPUT_ROOT),
    "database_path": str(DB_PATH),
}

# Indian market holidays (NSE/BSE). Extend as needed; used by the trading-day
# check. Format: YYYY-MM-DD.
NSE_HOLIDAYS_2026 = {
    "2026-01-26", "2026-03-06", "2026-03-21", "2026-04-01", "2026-04-03",
    "2026-04-14", "2026-05-01", "2026-08-15", "2026-10-02", "2026-11-09",
    "2026-12-25",
}
