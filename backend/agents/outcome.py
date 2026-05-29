"""Outcome Agent (Phase 5, Chunk 5.1) — does the system's signals predict moves?

Every run it (1) records the day's tracked ranking picks with their entry price +
pick-date signal snapshot, (2) fills 1d/5d exits for older picks from
prices_eod_adjusted, (3) appends XGBoost training rows once a 5d outcome is known,
(4) writes per-agent accuracy memory files to the vault, and (5) logs an accuracy
summary.

mle no-leakage: features are the pick-date snapshot (data available <= pick_date);
future prices are used ONLY as the label (return/direction), never as a feature.

The pure helpers (`compute_return`, `encode_*`, `compute_accuracy`,
`render_memory`) are unit-tested in isolation; the agent methods do the I/O via
`outcome_repo` and never embed business logic the repo should own (AGENTS.md §7).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

import structlog

from backend.db.repositories import outcome as outcome_repo
from backend.db.repositories.outcome import (
    AccuracySummary,
    OutcomeRow,
    TrainingRow,
)

log = structlog.get_logger()

_R4 = Decimal("0.0001")
_R2 = Decimal("0.01")

_FII_ENCODING = {
    "strong_buy": 2,
    "buy": 1,
    "neutral": 0,
    "sell": -1,
    "strong_sell": -2,
}
_REGIME_ENCODING = {"risk-on": 1, "neutral": 0, "risk-off": -1}

# Memory-file score buckets (per-agent reliability).
_HIGH_SCORE = Decimal("70")
_LOW_SCORE = Decimal("40")
_MEMORY_AGENTS = ("technical", "fundamental", "macro", "sector", "vcp")


# ---------------------------------------------------------------------------
# Pure helpers (unit tested)
# ---------------------------------------------------------------------------
def compute_return(entry: Decimal, exit_price: Decimal) -> tuple[Decimal, bool]:
    """(% return, direction_correct). A flat move (0%) is NOT correct (> 0 only)."""
    ret = ((exit_price - entry) / entry * 100).quantize(_R4, rounding=ROUND_HALF_EVEN)
    return ret, ret > 0


def encode_fii_signal(signal: str | None) -> int:
    """strong_buy=2 .. strong_sell=-2; unknown/None -> 0."""
    return _FII_ENCODING.get(signal or "", 0)


def encode_macro_regime(regime: str | None) -> int:
    """risk-on=1, neutral=0, risk-off=-1; unknown/None -> 0."""
    return _REGIME_ENCODING.get(regime or "", 0)


def _pct(correct: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0.00")
    return (Decimal(correct) / Decimal(total) * 100).quantize(
        _R2, rounding=ROUND_HALF_EVEN
    )


def compute_accuracy(rows: list[OutcomeRow]) -> AccuracySummary:
    """Directional accuracy over all tracked picks (denominator = total picks).

    A pick with no verdict yet counts against accuracy (not-yet-correct), so the
    number only rises as real winners land — never inflated by dropping pendings.
    """
    total = len(rows)
    correct_1d = sum(1 for r in rows if r.direction_correct_1d is True)
    correct_5d = sum(1 for r in rows if r.direction_correct_5d is True)

    by_signal: dict[str, dict[str, object]] = {}
    labels = {r.signal_label for r in rows}
    for label in sorted(labels):
        sub = [r for r in rows if r.signal_label == label]
        c1 = sum(1 for r in sub if r.direction_correct_1d is True)
        c5 = sum(1 for r in sub if r.direction_correct_5d is True)
        by_signal[label] = {
            "picks": len(sub),
            "correct_1d": c1,
            "correct_5d": c5,
            "accuracy_1d_pct": _pct(c1, len(sub)),
            "accuracy_5d_pct": _pct(c5, len(sub)),
        }

    return AccuracySummary(
        total_picks=total,
        correct_1d=correct_1d,
        correct_5d=correct_5d,
        accuracy_1d_pct=_pct(correct_1d, total),
        accuracy_5d_pct=_pct(correct_5d, total),
        by_signal=by_signal,
    )


def render_memory(
    agent_name: str,
    summary: AccuracySummary,
    *,
    as_of: date,
    high_score_acc: Decimal | None = None,
    low_score_acc: Decimal | None = None,
) -> str:
    """Render an agent's memory.md content (pure — no file I/O)."""
    high = (
        f"{high_score_acc}% accurate" if high_score_acc is not None else "n/a (no data)"
    )
    low = f"{low_score_acc}% accurate" if low_score_acc is not None else "n/a (no data)"
    findings = _recent_findings(summary)
    return (
        f"# {agent_name.title()} Memory — updated {as_of.isoformat()}\n\n"
        "## Accuracy summary (last 30 days)\n"
        f"Total picks tracked: {summary.total_picks}\n"
        f"1d directional accuracy: {summary.accuracy_1d_pct}%\n"
        f"5d directional accuracy: {summary.accuracy_5d_pct}%\n\n"
        "## Signal reliability\n"
        f"High {agent_name} score (>70): {high}\n"
        f"Low {agent_name} score (<40): {low}\n\n"
        "## Recent findings\n"
        f"{findings}\n\n"
        "---\n"
        "*For personal research and educational purposes only. Not investment "
        "advice.*\n"
    )


def _recent_findings(summary: AccuracySummary) -> str:
    if summary.total_picks == 0:
        return "- No tracked picks yet."
    lines = [
        f"- {label}: {d['picks']} picks, "
        f"1d {d['accuracy_1d_pct']}% / 5d {d['accuracy_5d_pct']}%"
        for label, d in summary.by_signal.items()
    ]
    return "\n".join(lines)


@dataclass
class OutcomeResult:
    picks_recorded: int
    exits_filled: int
    training_rows_added: int
    accuracy_summary: AccuracySummary


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class OutcomeAgent:
    name = "outcome"

    async def record_picks(self, session: object, pick_date: date) -> int:
        """Record the day's tracked picks (entry + snapshot, no exits). Count."""
        rows = await outcome_repo.fetch_rankings_for_picks(session, pick_date)  # type: ignore[arg-type]
        if not rows:
            log.info("outcome.record_picks.none", pick_date=pick_date.isoformat())
            return 0
        for row in rows:
            await outcome_repo.upsert_outcome(session, row)  # type: ignore[arg-type]
        log.info(
            "outcome.record_picks.done",
            pick_date=pick_date.isoformat(),
            picks=len(rows),
        )
        return len(rows)

    async def fill_exits(self, session: object, as_of: date) -> int:
        """Fill 1d/5d exits from prices_eod_adjusted for `as_of`. Count updated.

        A pick whose entry or exit price is missing in the DB is skipped (logged),
        never crashing the run — first runs legitimately have no 5d history yet.
        """
        filled = 0
        pending_1d = await outcome_repo.fetch_pending_1d(session, as_of)  # type: ignore[arg-type]
        pending_5d = await outcome_repo.fetch_pending_5d(session, as_of)  # type: ignore[arg-type]
        prices = await outcome_repo.fetch_adj_close(session, as_of)  # type: ignore[arg-type]

        for row in pending_1d:
            exit_price = prices.get(row.isin)
            if exit_price is None or row.entry_price in (None, 0):
                log.warning(
                    "outcome.fill_exits.skip_1d",
                    isin=row.isin,
                    as_of=as_of.isoformat(),
                )
                continue
            ret, correct = compute_return(row.entry_price, exit_price)
            row.exit_price_1d = exit_price
            row.return_1d_pct = ret
            row.direction_correct_1d = correct
            await outcome_repo.upsert_outcome(session, row)  # type: ignore[arg-type]
            filled += 1

        for row in pending_5d:
            exit_price = prices.get(row.isin)
            if exit_price is None or row.entry_price in (None, 0):
                log.warning(
                    "outcome.fill_exits.skip_5d",
                    isin=row.isin,
                    as_of=as_of.isoformat(),
                )
                continue
            ret, correct = compute_return(row.entry_price, exit_price)
            row.exit_price_5d = exit_price
            row.return_5d_pct = ret
            row.direction_correct_5d = correct
            await outcome_repo.upsert_outcome(session, row)  # type: ignore[arg-type]
            filled += 1

        log.info("outcome.fill_exits.done", as_of=as_of.isoformat(), filled=filled)
        return filled

    async def write_training_rows(self, session: object, as_of: date) -> int:
        """Append XGBoost rows for picks whose 5d outcome is now known. Count.

        Idempotent (upsert on isin, pick_date). Features come from the OutcomeRow
        snapshot; granular features not captured there (rsi/macd/pe/roe/fii/
        days_to_results/vcp_score) stay NULL for now — flagged follow-up.
        """
        rows = await outcome_repo.fetch_recent_outcomes(session, days=30)  # type: ignore[arg-type]
        added = 0
        for r in rows:
            if r.exit_price_5d is None or r.return_5d_pct is None:
                continue
            training = TrainingRow(
                isin=r.isin,
                pick_date=r.pick_date,
                f_technical_score=r.technical_score,
                f_fundamental_score=r.fundamental_score,
                f_macro_score=r.macro_score,
                f_macro_regime_encoded=Decimal(encode_macro_regime(r.macro_regime)),
                f_india_vix=r.india_vix,
                f_delivery_pct=r.delivery_pct,
                target_return_5d=r.return_5d_pct,
                target_direction_5d=r.direction_correct_5d,
            )
            await outcome_repo.upsert_training_row(session, training)  # type: ignore[arg-type]
            added += 1
        log.info("outcome.training_rows.done", as_of=as_of.isoformat(), added=added)
        return added

    async def write_memory_files(
        self,
        session: object,
        *,
        vault_dir: str | None = None,
        as_of: date | None = None,
    ) -> None:
        """Write per-agent accuracy memory files to <vault>/agents/<name>/memory.md.

        Gated on `vault_dir`: the backend container cannot reach the host vault, so
        when no vault is mounted this logs and returns (same pattern as the report/
        auditor steps). Never crashes the run.
        """
        if not vault_dir:
            log.info("outcome.memory.skipped", reason="no vault_dir mounted")
            return
        from backend.db.repositories._helpers import today_ist

        stamp = as_of or today_ist()
        rows = await outcome_repo.fetch_recent_outcomes(session, days=30)  # type: ignore[arg-type]
        summary = compute_accuracy(rows)

        import asyncio
        from pathlib import Path

        def _write() -> None:
            base = Path(vault_dir) / "agents"
            for name in _MEMORY_AGENTS:
                high, low = _score_bucket_accuracy(rows, name)
                content = render_memory(
                    name, summary, as_of=stamp, high_score_acc=high, low_score_acc=low
                )
                d = base / name
                d.mkdir(parents=True, exist_ok=True)
                (d / "memory.md").write_text(content, encoding="utf-8")

        await asyncio.to_thread(_write)
        log.info(
            "outcome.memory.written", agents=len(_MEMORY_AGENTS), dir=str(vault_dir)
        )

    async def run(
        self,
        session: object | None = None,
        today: date | None = None,
        *,
        vault_dir: str | None = None,
    ) -> OutcomeResult:
        """Main entry: record picks, fill exits, append training, write memory."""
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        as_of = today or today_ist()

        async with SessionLocal() as s:
            picks = await self.record_picks(s, as_of)
            exits = await self.fill_exits(s, as_of)
            training = await self.write_training_rows(s, as_of)
            await s.commit()

            await self.write_memory_files(s, vault_dir=vault_dir, as_of=as_of)

            rows = await outcome_repo.fetch_recent_outcomes(s, days=30)
        summary = compute_accuracy(rows)

        log.info(
            "outcome.run.done",
            picks_recorded=picks,
            exits_filled=exits,
            training_rows_added=training,
            accuracy_1d_pct=str(summary.accuracy_1d_pct),
            accuracy_5d_pct=str(summary.accuracy_5d_pct),
            total_picks=summary.total_picks,
        )
        return OutcomeResult(
            picks_recorded=picks,
            exits_filled=exits,
            training_rows_added=training,
            accuracy_summary=summary,
        )


def _score_bucket_accuracy(
    rows: list[OutcomeRow], agent_name: str
) -> tuple[Decimal | None, Decimal | None]:
    """1d accuracy for high (>70) vs low (<40) buckets of an agent's score column.

    Score-based agents (technical/fundamental/macro) bucket on their score; vcp
    buckets on vcp_detected; sector has no per-stock score -> (None, None).
    """

    def _acc(subset: list[OutcomeRow]) -> Decimal | None:
        verdicts = [r for r in subset if r.direction_correct_1d is not None]
        if not verdicts:
            return None
        correct = sum(1 for r in verdicts if r.direction_correct_1d is True)
        return _pct(correct, len(verdicts))

    attr = {
        "technical": "technical_score",
        "fundamental": "fundamental_score",
        "macro": "macro_score",
    }.get(agent_name)
    if attr is not None:
        high = [
            r
            for r in rows
            if getattr(r, attr) is not None and getattr(r, attr) > _HIGH_SCORE
        ]
        low = [
            r
            for r in rows
            if getattr(r, attr) is not None and getattr(r, attr) < _LOW_SCORE
        ]
        return _acc(high), _acc(low)
    if agent_name == "vcp":
        high = [r for r in rows if r.vcp_detected is True]
        low = [r for r in rows if r.vcp_detected is False]
        return _acc(high), _acc(low)
    return None, None  # sector: no per-stock score column in outcome_log
