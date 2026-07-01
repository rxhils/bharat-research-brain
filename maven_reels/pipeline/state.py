"""Shared run state + atomic JSON artifact persistence for the Reels pipeline."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def save_artifact(date: str, key: str, data: Any) -> Path:
    path = config.run_dir(date) / config.ARTIFACTS[key]
    _atomic_write_json(path, data)
    return path


def load_artifact(date: str, key: str) -> Any:
    path = config.run_dir(date) / config.ARTIFACTS[key]
    if not path.exists():
        raise FileNotFoundError(f"Reel artifact '{key}' not found at {path}.")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def artifact_exists(date: str, key: str) -> bool:
    return (config.run_dir(date) / config.ARTIFACTS[key]).exists()


@dataclass
class RunState:
    date: str
    completed: dict[str, bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @classmethod
    def load_or_new(cls, date: str) -> "RunState":
        if artifact_exists(date, "state"):
            raw = load_artifact(date, "state")
            return cls(date=raw["date"], completed=raw.get("completed", {}),
                       notes=raw.get("notes", []))
        return cls(date=date)

    def mark(self, step: str, done: bool = True) -> None:
        self.completed[step] = done
        self.save()

    def save(self) -> Path:
        return save_artifact(self.date, "state", {
            "date": self.date, "completed": self.completed, "notes": self.notes})
