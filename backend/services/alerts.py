"""Alert dispatch — STUB ONLY in Phase 1.

Real Telegram + email (SMTP) delivery is deferred to Phase 2 (CLAUDE.md §10).
For now `send_alert` is a no-op that logs the alert and reports that it was
NOT delivered, so callers can wire alerting today without any network I/O,
secrets, or public channels (CLAUDE.md §2 rules 6 + 8).
"""
from __future__ import annotations

from typing import Literal

import structlog

log = structlog.get_logger()

AlertLevel = Literal["info", "warn", "error"]


async def send_alert(
    message: str,
    *,
    level: AlertLevel = "info",
    title: str | None = None,
) -> bool:
    """Stub alert sink. Logs the alert and returns False (not delivered).

    Phase 2 will replace the body with Telegram bot + SMTP delivery. The
    signature is intentionally stable so callers do not change then.
    """
    log.info(
        "alert.suppressed_stub",
        level=level,
        title=title,
        message=message,
        note="alerts are a Phase 2 feature; nothing was sent",
    )
    return False
