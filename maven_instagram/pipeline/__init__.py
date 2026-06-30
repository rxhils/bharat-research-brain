"""Maven Instagram carousel automation pipeline.

A modular, rerunnable daily workflow that researches the Indian market, plans a
3-slide carousel, generates premium images via the Higgsfield MCP, writes a
compliant caption + hashtags, runs a quality gate, and publishes a carousel to
Instagram via the Composio MCP.

Each step persists its output as JSON in ``outputs/maven_instagram/<date>/`` so
any step can be rerun independently without losing upstream work.
"""
from __future__ import annotations

__all__ = ["config"]
