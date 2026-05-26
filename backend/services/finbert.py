"""FinBERT financial-sentiment service (Chunk 3.3).

Wraps ProsusAI/finbert (transformers) for in-process scoring of news text.
The model is heavy (torch), so it is imported and loaded lazily — importing
this module stays cheap and unit tests use a fake instead of the real model.

Label convention (the agent + DB CHECK constraint expect these three):
  positive -> "bull"    score = +confidence
  negative -> "bear"    score = -confidence
  neutral  -> "neutral" score =  0.0
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog

log = structlog.get_logger()

_MODEL = "ProsusAI/finbert"
_MAX_LEN = 512


@dataclass(frozen=True)
class SentimentResult:
    label: str  # one of: bull | bear | neutral
    score: float  # signed: +conf (bull), -conf (bear), 0.0 (neutral)
    confidence: float  # raw model probability for the winning class (0..1)


def to_sentiment_result(model_label: str, confidence: float) -> SentimentResult:
    """Map a raw FinBERT label + confidence to our signed convention."""
    label = model_label.strip().lower()
    if label == "positive":
        return SentimentResult(label="bull", score=confidence, confidence=confidence)
    if label == "negative":
        return SentimentResult(label="bear", score=-confidence, confidence=confidence)
    return SentimentResult(label="neutral", score=0.0, confidence=confidence)


class FinBertService:
    """Lazy-loading FinBERT pipeline. Sync scoring (CPU/GPU bound).

    The caller (SentimentAgent) wraps `score_batch` in `asyncio.to_thread`
    so the event loop is never blocked.
    """

    def __init__(self) -> None:
        self._pipe: object | None = None

    def load(self) -> None:
        if self._pipe is not None:
            return
        from transformers import pipeline  # lazy: torch is a ~2GB optional dep

        log.info("finbert.load.start", model=_MODEL)
        self._pipe = pipeline(
            "sentiment-analysis",
            model=_MODEL,
            truncation=True,
            max_length=_MAX_LEN,
        )
        log.info("finbert.load.done", model=_MODEL)

    def score(self, text: str) -> SentimentResult:
        return self.score_batch([text])[0]

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        self.load()
        assert self._pipe is not None
        raw = self._pipe(texts)  # type: ignore[operator]
        return [to_sentiment_result(r["label"], float(r["score"])) for r in raw]
