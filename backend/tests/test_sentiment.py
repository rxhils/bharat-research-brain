"""Tests for the Sentiment Agent (Chunk 3.3) — pure mapping + update build.

FinBERT is never loaded in unit tests. A FakeFinBert returns deterministic
keyword-based scores so the agent's batch/update plumbing can be exercised
offline. The label mapping (positive->bull, negative->bear, neutral->neutral)
and the score sign convention are pinned here.
"""
from __future__ import annotations

from backend.agents.sentiment import build_updates
from backend.services.finbert import SentimentResult, to_sentiment_result


class FakeFinBert:
    """Deterministic stand-in for FinBertService — no model, no torch."""

    _BULL = ("profit", "surge", "jumps", "gains")
    _BEAR = ("loss", "slump", "falls", "drops")

    def score(self, text: str) -> SentimentResult:
        low = text.lower()
        if any(w in low for w in self._BULL):
            return SentimentResult(label="bull", score=0.9, confidence=0.9)
        if any(w in low for w in self._BEAR):
            return SentimentResult(label="bear", score=-0.8, confidence=0.8)
        return SentimentResult(label="neutral", score=0.0, confidence=0.5)

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        return [self.score(t) for t in texts]


# ---------------------------------------------------------------------------
# to_sentiment_result — label mapping + score sign
# ---------------------------------------------------------------------------
def test_positive_maps_to_bull() -> None:
    r = to_sentiment_result("positive", 0.87)
    assert r.label == "bull"
    assert r.score == 0.87
    assert r.confidence == 0.87


def test_negative_maps_to_bear() -> None:
    r = to_sentiment_result("negative", 0.73)
    assert r.label == "bear"
    assert r.score == -0.73
    assert r.confidence == 0.73


def test_neutral_maps_to_neutral_zero() -> None:
    r = to_sentiment_result("neutral", 0.66)
    assert r.label == "neutral"
    assert r.score == 0.0
    assert r.confidence == 0.66


def test_label_is_case_insensitive() -> None:
    assert to_sentiment_result("POSITIVE", 0.5).label == "bull"
    assert to_sentiment_result("Negative", 0.5).label == "bear"


# ---------------------------------------------------------------------------
# build_updates — zips scored results back to article ids
# ---------------------------------------------------------------------------
def test_build_updates() -> None:
    articles = [
        (1, "Acme posts record profit", None),
        (2, "Beta reports heavy loss", "margins slump"),
        (3, "Gamma holds AGM", None),
    ]
    fake = FakeFinBert()
    texts = [f"{h} {s or ''}".strip() for _id, h, s in articles]
    results = fake.score_batch(texts)
    updates = build_updates(articles, results)
    assert updates == [
        {"id": 1, "sentiment_label": "bull", "sentiment_score": 0.9},
        {"id": 2, "sentiment_label": "bear", "sentiment_score": -0.8},
        {"id": 3, "sentiment_label": "neutral", "sentiment_score": 0.0},
    ]
