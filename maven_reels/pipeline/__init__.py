"""Maven Reels pipeline — retention-first, viral-style 20-35s market explainers.

A second, independent content pipeline alongside the carousel pipeline
(maven_instagram). It never modifies maven_instagram; it reuses its compliance +
brand by read-only import. Artifacts live under outputs/maven_reels/<date>/.
"""
from __future__ import annotations

__all__ = ["config"]
