"""Settings persistence — a single JSON file, merged over DEFAULT_SETTINGS."""
from __future__ import annotations

import copy
import json

from .config import DEFAULT_SETTINGS, SETTINGS_PATH


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_settings() -> dict:
    stored = {}
    if SETTINGS_PATH.exists():
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            stored = {}
    return _deep_merge(DEFAULT_SETTINGS, stored)


def update_settings(patch: dict) -> dict:
    merged = _deep_merge(get_settings(), patch or {})
    SETTINGS_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return merged
