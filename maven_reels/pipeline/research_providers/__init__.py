"""Backend research providers for the Reels pipeline.

The backend fetches TODAY's Indian market news itself — research never blocks
on the Claude Code conductor. Providers are tried in order; each returns
normalized story dicts (see base.Story fields). Zero-key RSS is always
available; Tavily/NewsAPI activate automatically when their env keys exist.
"""
from .base import Story, available_providers, fetch_all  # noqa: F401
