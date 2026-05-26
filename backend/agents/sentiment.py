"""Sentiment Agent (Chunk 3.3) — score unscored news with FinBERT.

Reads `news_articles` rows that have no sentiment yet (sentiment_label IS NULL),
runs headline + summary through FinBERT in batches, and writes back
`sentiment_label` (bull|bear|neutral) + signed `sentiment_score`. Scoring is
CPU/GPU bound and synchronous, so it runs in a worker thread. All 108 stored
articles are scored regardless of whether they matched an ISIN.
"""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

from backend.services.finbert import FinBertService, SentimentResult

log = structlog.get_logger()


def _text_of(headline: str, summary: str | None) -> str:
    return f"{headline} {summary or ''}".strip()


def build_updates(
    articles: list[tuple[Any, str, str | None]],
    results: list[SentimentResult],
) -> list[dict[str, Any]]:
    """Zip scored results back to article ids -> UPDATE payloads."""
    return [
        {
            "id": a_id,
            "sentiment_label": r.label,
            "sentiment_score": round(r.score, 4),
        }
        for (a_id, _headline, _summary), r in zip(articles, results, strict=True)
    ]


class SentimentAgent:
    def __init__(self, finbert: FinBertService | None = None) -> None:
        self.finbert = finbert or FinBertService()

    async def run(
        self,
        *,
        batch_size: int = 32,
        isin: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, int]:
        from backend.db.repositories import news as news_repo
        from backend.db.session import SessionLocal

        total_scored = 0
        total_updated = 0
        label_counts: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}

        while True:
            async with SessionLocal() as session:
                rows = await news_repo.fetch_unscored(
                    session, isin=isin, limit=batch_size
                )
                articles = [(r.id, r.headline, r.summary) for r in rows]
            if not articles:
                break

            texts = [_text_of(h, s) for _id, h, s in articles]
            results = await asyncio.to_thread(self.finbert.score_batch, texts)
            updates = build_updates(articles, results)
            for u in updates:
                label_counts[u["sentiment_label"]] += 1
            total_scored += len(updates)

            if not dry_run:
                async with SessionLocal() as session:
                    total_updated += await news_repo.update_sentiment(session, updates)
                    await session.commit()
            else:
                # dry-run reads the same rows forever — score one batch and stop
                break

        log.info(
            "sentiment.run.done",
            scored=total_scored,
            updated=total_updated,
            dry_run=dry_run,
            isin=isin,
            **{f"label_{k}": v for k, v in label_counts.items()},
        )
        return {
            "scored": total_scored,
            "updated": total_updated,
            **label_counts,
        }

    async def run_isin(self, isin: str, *, batch_size: int = 32) -> dict[str, int]:
        return await self.run(batch_size=batch_size, isin=isin)
