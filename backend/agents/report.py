"""Report Agent (Chunk 4.4) — the daily research note (deterministic, no LLM).

Pure structured formatting of the ranked watchlist + every signal table. No
Ollama, no external calls, zero hallucination risk — fast and reproducible.
Every block carries a source citation; the note ends with the mandatory
§2-rule-4 disclaimer; FII signals render as flow language so banned advisory
words never appear (§2 rule 2). `audit_passed` stays False until the
Meta-Auditor (Chunk 4.5).

`assemble_report` / `regime_implication` / `macd_direction` / `macro_summary_line`
/ `word_count` are pure (unit tested); `build_context` reads the DB; `run`
assembles + saves to Postgres + writes the Obsidian note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import structlog

log = structlog.get_logger()

SOURCE = "report_agent"
_IST = ZoneInfo("Asia/Kolkata")

DISCLAIMER = (
    "For personal research only. Not investment advice. Not registered with "
    "SEBI. All data from local DB."
)

_REGIME_IMPLICATION = {
    "risk-on": "favour growth and momentum",
    "risk-off": "favour quality and defensives",
    "neutral": "selective — stock-specific signals",
}

_FII_PHRASE = {
    "strong_buy": "strong inflow",
    "buy": "inflow",
    "neutral": "balanced flow",
    "sell": "outflow",
    "strong_sell": "strong outflow",
}

_LABELS = ("bullish-watch", "needs-confirmation", "neutral", "cautious", "avoid")


@dataclass(frozen=True)
class StockCtx:
    rank: int
    isin: str
    symbol: str
    sector: str | None
    label: str
    composite: Decimal
    t_score: Decimal | None
    f_score: Decimal | None
    m_score: Decimal | None
    risk_penalty: Decimal | None
    volatility_flag: str | None
    atr_pct: Decimal | None
    rsi: Decimal | None
    ema_cross: str | None
    vs_ema200: str | None
    macd_hist: Decimal | None
    roe: Decimal | None  # raw yfinance fraction
    de: Decimal | None  # raw yfinance percent
    pe: Decimal | None
    rev_growth: Decimal | None  # raw yfinance fraction
    sector_signal: str | None
    sector_mom_7d: Decimal | None
    fii_signal: str | None
    ts_date: date | None
    fs_date: date | None


@dataclass
class ReportContext:
    report_date: date
    generated_at_ist: str
    regime: str
    nifty_value: Decimal | None
    nifty_signal: str
    usd_inr: Decimal | None
    usd_signal: str
    crude_signal: str
    fii_5d_sum: Decimal | None
    fii_signal: str | None
    top_stocks: list[StockCtx]
    leading_sectors: list[str]
    lagging_sectors: list[str]
    neutral_sectors: list[str]
    risk_stocks: list[tuple[str, Decimal, str, Decimal | None]]
    signal_distribution: dict[str, int]
    fund_date: date | None
    top10: list[tuple[str, Decimal]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def word_count(text: str) -> int:
    return len(text.split())


def regime_implication(regime: str) -> str:
    return _REGIME_IMPLICATION.get(regime, _REGIME_IMPLICATION["neutral"])


def macd_direction(macd_hist: Decimal | None) -> str:
    if macd_hist is None or macd_hist == 0:
        return "flat"
    return "positive" if macd_hist > 0 else "negative"


def _fii_phrase(signal: str | None) -> str:
    if signal is None:
        return "n/a"
    return _FII_PHRASE.get(signal, "balanced flow")


def _num(value: Decimal | None, places: str = "0.01", suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value.quantize(Decimal(places))}{suffix}"


def _score(value: Decimal | None) -> str:
    return f"{value.quantize(Decimal('1'))}" if value is not None else "n/a"


def _pct_from_fraction(value: Decimal | None) -> str:
    return f"{(value * 100).quantize(Decimal('0.1'))}%" if value is not None else "n/a"


def macro_summary_line(ctx: ReportContext) -> str:
    return (
        f"Regime {ctx.regime}; Nifty {_num(ctx.nifty_value)} ({ctx.nifty_signal}); "
        f"USD/INR {_num(ctx.usd_inr)} ({ctx.usd_signal}); Crude {ctx.crude_signal}; "
        f"FII 5d {_num(ctx.fii_5d_sum)} Cr ({_fii_phrase(ctx.fii_signal)})"
    )


def _stock_block(s: StockCtx) -> str:
    roe = _pct_from_fraction(s.roe)
    de = f"{(s.de / 100).quantize(Decimal('0.01'))}x" if s.de is not None else "n/a"
    pe = f"{s.pe.quantize(Decimal('0.01'))}x" if s.pe is not None else "n/a"
    rsi = _num(s.rsi, "0.1")
    rp = s.risk_penalty if s.risk_penalty is not None else Decimal(0)
    return "\n".join(
        [
            f"### {s.rank}. {s.symbol} ({s.sector or 'n/a'}) — {s.label}",
            f"Score: {_num(s.composite)}/100 | Risk: {s.volatility_flag or 'n/a'}",
            "",
            f"Technical  ({_score(s.t_score)}/100)",
            f"  RSI {rsi} · {s.ema_cross or 'no-cross'} · {s.vs_ema200 or 'n/a'} EMA200",
            f"  MACD histogram: {macd_direction(s.macd_hist)}",
            "",
            f"Fundamental ({_score(s.f_score)}/100)",
            f"  ROE {roe} · D/E {de} · PE {pe}",
            f"  Revenue growth: {_pct_from_fraction(s.rev_growth)}",
            "",
            f"Macro      ({_score(s.m_score)}/100)",
            f"  Sector {s.sector_signal or 'n/a'} ({_num(s.sector_mom_7d)}% 7d)",
            f"  FII signal: {_fii_phrase(s.fii_signal)}",
            "",
            f"Risk penalty: -{_num(rp)} pts",
            f"  ATR {_num(s.atr_pct)}% | Volatility: {s.volatility_flag or 'n/a'}",
            "",
            f"Sources: technical_signals {s.ts_date or 'n/a'}, "
            f"fundamental_signals {s.fs_date or 'n/a'}",
            "----",
            "",
        ]
    )


def assemble_report(ctx: ReportContext) -> str:
    """Build the full deterministic markdown note from context (pure)."""
    lines: list[str] = [
        f"# Daily research note — {ctx.report_date.isoformat()}",
        f"Generated: {ctx.generated_at_ist} IST | Regime: {ctx.regime}",
        "",
        "## Macro snapshot",
        f"Nifty 50:  {_num(ctx.nifty_value)} ({ctx.nifty_signal})",
        f"USD/INR:   {_num(ctx.usd_inr)} ({ctx.usd_signal})",
        f"Crude:     {ctx.crude_signal}",
        f"FII 5d:    {_num(ctx.fii_5d_sum)} Cr ({_fii_phrase(ctx.fii_signal)})",
        f"Regime:    {ctx.regime} — {regime_implication(ctx.regime)}",
        "",
        f"## Top stocks to watch — {ctx.report_date.isoformat()}",
        "",
    ]
    for s in ctx.top_stocks[:5]:
        lines.append(_stock_block(s))

    lines += [
        "## Sector rotation",
        f"Leading:  {', '.join(ctx.leading_sectors) or 'none'}",
        f"Lagging:  {', '.join(ctx.lagging_sectors) or 'none'}",
        f"Neutral:  {', '.join(ctx.neutral_sectors) or 'none'}",
        "",
        "## Risk flags",
        "Stocks to approach with caution today:",
    ]
    for sym, score, flag, atr in ctx.risk_stocks[:3]:
        lines.append(
            f"  {sym} risk {score:.0f}/100 ({flag} volatility, ATR {_num(atr)}%)"
        )
    lines += ["", "## Signal distribution"]
    for label in _LABELS:
        count = ctx.signal_distribution.get(label, 0)
        lines.append(f"  {label + ':':<19} {count} stocks")
    lines += ["", "---", f"*{DISCLAIMER}*", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class ReportAgent:
    name = "report"

    async def build_context(self, as_of_date: date) -> ReportContext:
        from backend.db.repositories import report as report_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            macro = await report_repo.fetch_macro(session)
            fii_5d, fii_signal = await report_repo.fetch_fii_latest(session)
            top = await report_repo.fetch_top_stocks(session, limit=5)
            top10 = await report_repo.fetch_top10(session)
            leading, lagging, neutral = await report_repo.fetch_sector_buckets(session)
            risk = await report_repo.fetch_risk_top(session, limit=3)
            dist = await report_repo.fetch_signal_distribution(session)
            fund_date = await report_repo.fetch_fund_date(session)

        return ReportContext(
            report_date=as_of_date,
            generated_at_ist=datetime.now(_IST).strftime("%H:%M"),
            regime=macro.get("regime", "neutral"),
            nifty_value=macro.get("nifty_value"),
            nifty_signal=macro.get("nifty_signal", "unknown"),
            usd_inr=macro.get("usd_inr"),
            usd_signal=macro.get("usd_signal", "unknown"),
            crude_signal=macro.get("crude_signal", "unknown"),
            fii_5d_sum=fii_5d,
            fii_signal=fii_signal,
            top_stocks=top,
            leading_sectors=leading,
            lagging_sectors=lagging,
            neutral_sectors=neutral,
            risk_stocks=risk,
            signal_distribution=dist,
            fund_date=fund_date,
            top10=top10,
        )

    async def run(
        self,
        *,
        as_of_date: date | None = None,
        dry_run: bool = False,
        out_dir: str | None = None,
    ) -> str:
        from backend.db.repositories._helpers import today_ist

        as_of = as_of_date or today_ist()
        ctx = await self.build_context(as_of)
        body = assemble_report(ctx)

        if dry_run:
            log.info(
                "report.run.dry_run", date=as_of.isoformat(), words=word_count(body)
            )
            return body

        await self._save(ctx, body)
        if out_dir:
            await self._write_vault(out_dir, as_of, body)
        log.info("report.run.done", date=as_of.isoformat(), words=word_count(body))
        return body

    async def _save(self, ctx: ReportContext, body: str) -> None:
        from backend.db.repositories import report as report_repo
        from backend.db.session import SessionLocal

        row: dict[str, Any] = {
            "report_date": ctx.report_date,
            "body_md": body,
            "word_count": word_count(body),
            "top_stocks": [{"isin": i, "score": float(sc)} for i, sc in ctx.top10],
            "macro_summary": macro_summary_line(ctx),
            "audit_passed": False,  # set True by the Meta-Auditor (Chunk 4.5)
        }
        async with SessionLocal() as session:
            await report_repo.upsert_report(session, row)
            await session.commit()

    @staticmethod
    async def _write_vault(out_dir: str, as_of: date, body: str) -> None:
        import asyncio
        from pathlib import Path

        def _write() -> None:
            base = Path(out_dir)
            base.mkdir(parents=True, exist_ok=True)
            (base / f"{as_of.isoformat()}.md").write_text(body, encoding="utf-8")

        await asyncio.to_thread(_write)
