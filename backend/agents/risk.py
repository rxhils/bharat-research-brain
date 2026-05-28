"""Risk Agent (Chunk 4.2) — per-stock risk flags from existing DB data.

Pure SQL aggregation — NO external calls. For each active stock it derives ATR%
(from technical_signals + latest price), a news-volume spike flag (from
news_articles), and a 0-100 risk score tilted by the current macro regime
(from macro_signals). `days_to_results` is always NULL (earnings calendar not
built — flagged in AGENTS.md §16).

`compute_risk` is pure (testable with synthetic inputs); only `run_all` does I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import structlog

log = structlog.get_logger()

SOURCE = "risk_agent"

# Volatility / score thresholds (ATR as % of price).
_ATR_HIGH = Decimal("4")
_ATR_MEDIUM = Decimal("2")
_ATR_LOW = Decimal("1")

_BASE_SCORE = 50
_MIN_SPIKE_COUNT = 3
_SPIKE_MULTIPLE = 3


@dataclass(frozen=True)
class RiskRow:
    isin: str
    atr_pct: Decimal | None
    volatility_flag: str
    news_spike: bool
    days_to_results: int | None
    risk_score: Decimal
    source: str = SOURCE


def _volatility_flag(atr_pct: Decimal | None) -> str:
    if atr_pct is None:
        return "low"
    if atr_pct > _ATR_HIGH:
        return "high"
    if atr_pct > _ATR_MEDIUM:
        return "medium"
    return "low"


def _is_news_spike(count_24h: int, avg_7d: Decimal) -> bool:
    return count_24h >= _MIN_SPIKE_COUNT and count_24h > _SPIKE_MULTIPLE * avg_7d


def compute_risk(
    isin: str,
    atr_pct: Decimal | None,
    news_count_24h: int,
    news_avg_7d: Decimal,
    macro_regime: str,
    pledge_flag: str | None = None,
    days_to_results: int | None = None,
) -> RiskRow:
    """Pure risk scoring: base 50, then volatility/news/regime/pledge/earnings
    adjustments, clamped to 0-100. `days_to_results=None` (no calendar entry)
    leaves the earnings term at 0 — backward compatible with pre-Build-E callers."""
    flag = _volatility_flag(atr_pct)
    spike = _is_news_spike(news_count_24h, news_avg_7d)

    score = _BASE_SCORE
    if atr_pct is not None:
        if atr_pct > _ATR_HIGH:
            score += 25
        elif atr_pct > _ATR_MEDIUM:
            score += 10
        elif atr_pct < _ATR_LOW:
            score -= 10
    if spike:
        score += 15
    if macro_regime == "risk-off":
        score += 10
    # Promoter pledge (Chunk 4.9): a high pledge is a governance red flag.
    score += {"critical": 20, "high": 10, "moderate": 5}.get(pledge_flag or "", 0)
    # Earnings event-risk (Build E): the closer the results, the more uncertainty.
    if days_to_results is not None:
        if days_to_results <= 2:
            score += 15
        elif days_to_results <= 5:
            score += 10
        elif days_to_results <= 10:
            score += 5
    score = max(0, min(100, score))

    return RiskRow(
        isin=isin,
        atr_pct=atr_pct,
        volatility_flag=flag,
        news_spike=spike,
        days_to_results=days_to_results,
        risk_score=Decimal(score),
        source=SOURCE,
    )


class RiskAgent:
    name = "risk"

    async def run_all(
        self, *, isin: str | None = None, dry_run: bool = False
    ) -> list[RiskRow]:
        from backend.db.repositories import earnings as earnings_repo
        from backend.db.repositories import promoter as promoter_repo
        from backend.db.repositories import risk as risk_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            atr_by_isin = await risk_repo.fetch_atr_pct(session, isin=isin)
            news_by_isin = await risk_repo.fetch_news_counts(session, isin=isin)
            regime = await risk_repo.fetch_macro_regime(session)
            isins = await risk_repo.fetch_active_isins(session, isin=isin)
            pledge_by_isin = await promoter_repo.fetch_latest_flags(session)
            upcoming = await earnings_repo.fetch_upcoming(session)

        today = _today()
        rows: list[RiskRow] = []
        for i in isins:
            count_24h, avg_7d = news_by_isin.get(i, (0, Decimal(0)))
            result_date = upcoming.get(i)
            days_to_results = (result_date - today).days if result_date else None
            rows.append(
                compute_risk(
                    i, atr_by_isin.get(i), count_24h, avg_7d, regime,
                    pledge_by_isin.get(i), days_to_results,
                )
            )
        rows.sort(key=lambda r: r.risk_score, reverse=True)

        if not dry_run and rows:
            payload = [_to_dict(r, _today()) for r in rows]
            async with SessionLocal() as session:
                await risk_repo.bulk_upsert(session, payload)
                await session.commit()

        log.info(
            "risk.run.done",
            stocks=len(rows),
            regime=regime,
            dry_run=dry_run,
            high=sum(1 for r in rows if r.volatility_flag == "high"),
        )
        return rows


def _today() -> date:
    from backend.db.repositories._helpers import today_ist

    return today_ist()


def _to_dict(r: RiskRow, computed_date: date) -> dict[str, object]:
    return {
        "isin": r.isin,
        "computed_date": computed_date,
        "atr_pct": r.atr_pct,
        "volatility_flag": r.volatility_flag,
        "news_spike": r.news_spike,
        "days_to_results": r.days_to_results,
        "risk_score": r.risk_score,
        "source": r.source,
    }
