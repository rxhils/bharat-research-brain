"""Tests for the Meta-Auditor (Chunk 4.5) — 5 pure validation rules, no DB.

Each rule is a pure function over the report body (+ DB-derived expected values
passed in). Pass and fail cases are tested for every rule, plus the aggregate
`evaluate`. No DB, no network.
"""
from __future__ import annotations

from decimal import Decimal

from backend.agents.meta_auditor import (
    AuditResult,
    check_banned_words,
    check_citations,
    check_disclaimer,
    check_scores,
    check_source_dates,
    evaluate,
)

_STOCK = "\n".join(
    [
        "### 1. AJANTPHARM (Pharma) — bullish-watch",
        "Score: 82.25/100 | Risk: medium",
        "Technical  (90/100)",
        "  RSI 56.3 · none · above EMA200",
        "Fundamental (100/100)",
        "  ROE 25.4% · D/E 0.06x · PE 36.46x",
        "Macro      (55/100)",
        "  FII signal: inflow",
        "Sources: technical_signals 2026-05-22, fundamental_signals 2026-05-26",
        "----",
    ]
)
_GOOD_BODY = (
    "# Daily research note — 2026-05-26\n\n"
    "## Top stocks to watch\n\n" + _STOCK + "\n\n"
    "*For personal research only. Not investment advice. SEBI.*\n"
)

_SCORES = {"AJANTPHARM": Decimal("82.25")}
_DATES = {"AJANTPHARM": ("2026-05-22", "2026-05-26")}


# ---------------------------------------------------------------------------
# Rule 1 — citations present
# ---------------------------------------------------------------------------
def test_citations_pass() -> None:
    assert check_citations(_GOOD_BODY) == []


def test_citations_fail_missing_sources() -> None:
    body = _GOOD_BODY.replace(
        "Sources: technical_signals 2026-05-22, fundamental_signals 2026-05-26", ""
    )
    assert check_citations(body) != []


# ---------------------------------------------------------------------------
# Rule 2 — no fabricated numbers (report score matches DB within 1)
# ---------------------------------------------------------------------------
def test_scores_pass() -> None:
    assert check_scores(_GOOD_BODY, _SCORES) == []


def test_scores_fail_mismatch() -> None:
    assert check_scores(_GOOD_BODY, {"AJANTPHARM": Decimal("90")}) != []


def test_scores_fail_missing_db() -> None:
    assert check_scores(_GOOD_BODY, {}) != []


# ---------------------------------------------------------------------------
# Rule 3 — disclaimer present
# ---------------------------------------------------------------------------
def test_disclaimer_pass() -> None:
    assert check_disclaimer(_GOOD_BODY) == []


def test_disclaimer_fail() -> None:
    assert check_disclaimer("# report with no disclaimer") != []


# ---------------------------------------------------------------------------
# Rule 4 — no banned advisory words in stock sections
# ---------------------------------------------------------------------------
def test_banned_words_pass_approved_labels() -> None:
    # bullish-watch, needs-confirmation, inflow/outflow are all approved
    assert check_banned_words(_GOOD_BODY) == []


def test_banned_words_fail_buy() -> None:
    body = _GOOD_BODY.replace("Risk: medium", "Risk: medium — buy now")
    assert check_banned_words(body) != []


def test_banned_words_fail_invest_in() -> None:
    body = _GOOD_BODY.replace("Risk: medium", "Risk: medium — invest in this")
    assert check_banned_words(body) != []


def test_banned_words_not_fooled_by_substring() -> None:
    # 'buyer' contains 'buy' but is not a whole-word match -> no false positive
    body = _GOOD_BODY.replace("Risk: medium", "Risk: medium (largest buyer noted)")
    assert check_banned_words(body) == []


# ---------------------------------------------------------------------------
# Rule 5 — cited source dates match DB
# ---------------------------------------------------------------------------
def test_source_dates_pass() -> None:
    assert check_source_dates(_GOOD_BODY, _DATES) == []


def test_source_dates_fail_mismatch() -> None:
    assert (
        check_source_dates(_GOOD_BODY, {"AJANTPHARM": ("2026-05-21", "2026-05-26")})
        != []
    )


# ---------------------------------------------------------------------------
# evaluate — aggregate
# ---------------------------------------------------------------------------
def test_evaluate_all_pass() -> None:
    res = evaluate(_GOOD_BODY, _SCORES, _DATES)
    assert isinstance(res, AuditResult)
    assert res.passed is True
    assert res.rules_checked == 5
    assert res.rules_passed == 5
    assert res.failures == []


def test_evaluate_fails_closed() -> None:
    res = evaluate("# empty report", {}, {})
    assert res.passed is False
    assert res.rules_passed < 5
    assert res.failures
