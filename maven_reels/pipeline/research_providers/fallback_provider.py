"""Fallback provider — never fabricates. Its only job is a clear config error.

If every real provider fails or returns nothing, research reports a FAILED
status with an actionable message (configure keys / check network) — it never
invents stories and never says 'requires Claude Code conductor'.
"""
from __future__ import annotations

NAME = "fallback"


def configured() -> bool:
    return True


def config_error(errors: list[str]) -> dict:
    return {
        "research_status": "failed",
        "error": ("No research providers returned data. "
                  + ("; ".join(errors) if errors else
                     "Check network access to the RSS feeds, or set "
                     "TAVILY_API_KEY / NEWSAPI_KEY in the backend environment.")),
        "next_action": "Fix provider config / network, then click Run Reel again.",
    }
