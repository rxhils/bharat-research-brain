"""Structured-ish logging for the pipeline.

Logs go to both stderr and a per-run logfile. Every record carries the run date
and the step name so a failure at 14:47 IST on a Friday is debuggable later.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False


def get_logger(step: str, date: str, log_dir: Path) -> logging.Logger:
    """Return a logger that writes to console + ``<run_dir>/run.log``."""
    global _CONFIGURED
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"maven_ig.{step}")
    logger.setLevel(logging.INFO)

    if not _CONFIGURED:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
        )
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(fmt)

        file_handler = logging.FileHandler(log_dir / "run.log", encoding="utf-8")
        file_handler.setFormatter(fmt)

        root = logging.getLogger("maven_ig")
        root.setLevel(logging.INFO)
        root.handlers.clear()
        root.addHandler(console)
        root.addHandler(file_handler)
        root.propagate = False
        _CONFIGURED = True

    return logger
