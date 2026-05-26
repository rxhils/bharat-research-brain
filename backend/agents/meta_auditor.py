"""Meta-Auditor (Chunk 4.5) — validates every daily report before it counts.

Enforces 5 rules (CLAUDE.md §9/§11): citations present, no fabricated numbers,
disclaimer present, no banned advisory words (§2 rule 2), and source dates that
match the DB. Fails CLOSED — `audit_passed` is only flipped True when ALL rules
pass. No new table; updates `daily_reports.audit_passed` and writes an audit log
to the vault. The 5 rule checks + `evaluate` are pure (unit tested); only
`audit_report` / `run` touch the DB.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

import structlog

log = structlog.get_logger()

SOURCE = "meta_auditor"
_SCORE_TOLERANCE = Decimal("1")

# Banned advisory words (§2 rule 2). Whole-word, case-insensitive. The approved
# labels (bullish-watch, needs-confirmation) and FII flow words (inflow/outflow)
# contain none of these as whole words, so they are never flagged.
_BANNED_WORDS = ("buy", "sell", "purchase", "recommended")
_BANNED_PHRASES = ("invest in",)

_HEADING_RE = re.compile(r"###\s*\d+\.\s+(\S+)\s+\(")
_SCORE_RE = re.compile(r"Score:\s*([\d.]+)\s*/\s*100")
_CITATION_RE = re.compile(r"Sources:\s+\w+\s+\d{4}-\d{2}-\d{2}")
_TS_DATE_RE = re.compile(r"technical_signals\s+(\d{4}-\d{2}-\d{2})")
_FS_DATE_RE = re.compile(r"fundamental_signals\s+(\d{4}-\d{2}-\d{2})")


@dataclass
class AuditResult:
    passed: bool
    rules_checked: int
    rules_passed: int
    failures: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _stock_sections(body: str) -> list[tuple[str, str]]:
    """(symbol, section_text) for each stock block (delimited by '----')."""
    out: list[tuple[str, str]] = []
    for chunk in body.split("----"):
        m = _HEADING_RE.search(chunk)
        if m:
            out.append((m.group(1), chunk))
    return out


# ---------------------------------------------------------------------------
# Rule 1 — citations present
# ---------------------------------------------------------------------------
def check_citations(body: str) -> list[str]:
    sections = _stock_sections(body)
    if not sections:
        return ["rule1: no stock sections found"]
    return [
        f"rule1: {sym} stock section missing 'Sources: <table> <date>'"
        for sym, text in sections
        if not _CITATION_RE.search(text)
    ]


# ---------------------------------------------------------------------------
# Rule 2 — no fabricated numbers (report score within tolerance of DB)
# ---------------------------------------------------------------------------
def check_scores(body: str, db_scores: dict[str, Decimal]) -> list[str]:
    sections = _stock_sections(body)
    if not sections:
        return ["rule2: no stock sections found"]
    failures: list[str] = []
    for sym, text in sections:
        m = _SCORE_RE.search(text)
        if m is None:
            failures.append(f"rule2: {sym} has no Score: line")
            continue
        reported = Decimal(m.group(1))
        if sym not in db_scores:
            failures.append(
                f"rule2: {sym} not found in stock_rankings (cannot verify)"
            )
            continue
        if abs(reported - db_scores[sym]) > _SCORE_TOLERANCE:
            failures.append(
                f"rule2: {sym} score {reported} differs from DB {db_scores[sym]} by >1"
            )
    return failures


# ---------------------------------------------------------------------------
# Rule 3 — disclaimer present
# ---------------------------------------------------------------------------
def check_disclaimer(body: str) -> list[str]:
    if "Not investment advice" not in body:
        return ["rule3: missing 'Not investment advice' disclaimer"]
    return []


# ---------------------------------------------------------------------------
# Rule 4 — no banned advisory words in stock sections
# ---------------------------------------------------------------------------
def check_banned_words(body: str) -> list[str]:
    failures: list[str] = []
    for sym, text in _stock_sections(body):
        low = text.lower()
        for word in _BANNED_WORDS:
            if re.search(rf"\b{word}\b", low):
                failures.append(f"rule4: {sym} contains banned advisory word '{word}'")
        for phrase in _BANNED_PHRASES:
            if phrase in low:
                failures.append(f"rule4: {sym} contains banned phrase '{phrase}'")
    return failures


# ---------------------------------------------------------------------------
# Rule 5 — cited source dates match DB
# ---------------------------------------------------------------------------
def check_source_dates(body: str, db_dates: dict[str, tuple[str, str]]) -> list[str]:
    sections = _stock_sections(body)
    if not sections:
        return ["rule5: no stock sections found"]
    failures: list[str] = []
    for sym, text in sections:
        if sym not in db_dates:
            failures.append(f"rule5: {sym} not found in DB (cannot verify dates)")
            continue
        exp_ts, exp_fs = db_dates[sym]
        ts = _TS_DATE_RE.search(text)
        fs = _FS_DATE_RE.search(text)
        if ts is None or ts.group(1) != exp_ts:
            failures.append(
                f"rule5: {sym} technical_signals date "
                f"{ts.group(1) if ts else 'missing'} != DB {exp_ts}"
            )
        if fs is None or fs.group(1) != exp_fs:
            failures.append(
                f"rule5: {sym} fundamental_signals date "
                f"{fs.group(1) if fs else 'missing'} != DB {exp_fs}"
            )
    return failures


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------
def evaluate(
    body: str,
    db_scores: dict[str, Decimal],
    db_dates: dict[str, tuple[str, str]],
) -> AuditResult:
    rule_failures = [
        check_citations(body),
        check_scores(body, db_scores),
        check_disclaimer(body),
        check_banned_words(body),
        check_source_dates(body, db_dates),
    ]
    rules_passed = sum(1 for f in rule_failures if not f)
    failures = [msg for fs in rule_failures for msg in fs]
    return AuditResult(
        passed=rules_passed == len(rule_failures),
        rules_checked=len(rule_failures),
        rules_passed=rules_passed,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class MetaAuditor:
    name = "meta_auditor"

    async def audit_report(self, report_date: date) -> AuditResult:
        from backend.db.repositories import report as report_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            report = await report_repo.fetch_report(session, report_date=report_date)
            if report is None:
                return AuditResult(
                    passed=False,
                    rules_checked=5,
                    rules_passed=0,
                    failures=[f"no report found for {report_date.isoformat()}"],
                )
            top = await report_repo.fetch_top_stocks(session, limit=5)

        db_scores = {s.symbol: s.composite for s in top}
        db_dates = {
            s.symbol: (
                s.ts_date.isoformat() if s.ts_date else "",
                s.fs_date.isoformat() if s.fs_date else "",
            )
            for s in top
        }
        return evaluate(report.body_md, db_scores, db_dates)

    async def run(
        self, *, report_date: date | None = None, out_dir: str | None = None
    ) -> AuditResult:
        from backend.db.repositories import report as report_repo
        from backend.db.session import SessionLocal

        as_of = report_date or await self._latest_report_date()
        if as_of is None:
            return AuditResult(
                passed=False,
                rules_checked=5,
                rules_passed=0,
                failures=["no reports exist to audit"],
            )

        result = await self.audit_report(as_of)
        async with SessionLocal() as session:
            await report_repo.set_audit_passed(session, as_of, result.passed)
            await session.commit()
        if out_dir:
            await self._write_audit_log(out_dir, as_of, result)

        log.info(
            "meta_auditor.run.done",
            date=as_of.isoformat(),
            passed=result.passed,
            rules_passed=result.rules_passed,
            failures=len(result.failures),
        )
        return result

    @staticmethod
    async def _latest_report_date() -> date | None:
        from backend.db.repositories import report as report_repo
        from backend.db.session import SessionLocal

        async with SessionLocal() as session:
            rows = await report_repo.fetch_reports(session, limit=1)
        return rows[0].report_date if rows else None

    @staticmethod
    async def _write_audit_log(out_dir: str, as_of: date, result: AuditResult) -> None:
        import asyncio
        from pathlib import Path

        lines = [
            f"# Audit — {as_of.isoformat()}",
            "",
            f"Result: {'PASS' if result.passed else 'FAIL'}",
            f"Rules passed: {result.rules_passed}/{result.rules_checked}",
            f"Checked at: {result.checked_at.isoformat()}",
            "",
            "## Failures",
        ]
        lines += [f"- {f}" for f in result.failures] or ["- none"]
        lines += [
            "",
            "*Meta-Auditor enforces CLAUDE.md §9/§11. Not investment advice.*",
            "",
        ]
        body = "\n".join(lines)

        def _write() -> None:
            base = Path(out_dir)
            base.mkdir(parents=True, exist_ok=True)
            (base / f"{as_of.isoformat()}-audit.md").write_text(body, encoding="utf-8")

        await asyncio.to_thread(_write)
