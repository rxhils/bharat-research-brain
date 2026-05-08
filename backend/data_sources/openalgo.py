"""OpenAlgo data source — STUB ONLY in Chunk 1.2.

OpenAlgo cross-check is deferred to a Phase 1.5 follow-up: requires auth
setup not yet performed. All methods return an empty list with metadata
flagged `is_stub=True`. The Universe Agent treats stub returns as
"tertiary unavailable" — does not raise, does not warn. Tracked in AGENTS.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from backend.data_sources._http import FetchMetadata


@dataclass(frozen=True)
class OpenAlgoSymbol:
    nse_symbol: str
    bse_symbol: str | None
    isin: str


class OpenAlgoClient:
    """STUB. Real implementation deferred to Phase 1.5 (see AGENTS.md)."""

    is_stub: bool = True

    async def fetch_symbol_master(self) -> tuple[list[OpenAlgoSymbol], FetchMetadata]:
        meta = FetchMetadata(
            source_url="<stub:openalgo>",
            downloaded_at_utc=datetime.now(UTC),
            file_sha256="0" * 64,
            row_count=0,
            http_status=0,
            content_length=0,
            cache_hit=False,
            is_stub=True,
        )
        return [], meta
