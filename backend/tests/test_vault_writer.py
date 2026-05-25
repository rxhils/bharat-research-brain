"""Tests for the Vault Writer's pure note-generation (Chunk 1.6).

`render_note` is pure (no file I/O): given a NoteData and optional existing
file content, it returns the full markdown note, regenerating the
agent-managed header and preserving anything the operator wrote after the
annotations marker.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.agents.vault_writer import (
    ANNOTATION_MARKER,
    EventLine,
    NoteData,
    note_filename,
    render_note,
)


def _data(**over: object) -> NoteData:
    base: dict[str, object] = dict(
        symbol="HDFCBANK",
        title="HDFC Bank Ltd",
        isin="INE040A01034",
        sector="Financials",
        industry="Financial Services",
        listed_on=date(1995, 11, 8),
        latest_close=Decimal("1642.50"),
        latest_date=date(2026, 5, 23),
        indices=["NIFTY50", "NIFTYBANK", "NIFTY100"],
        events_total=3,
        recent_events=[
            EventLine(date(2024, 10, 28), "split", "factor 2:1"),
            EventLine(date(2023, 7, 14), "dividend", "₹19/share"),
        ],
        mcap_category="large",
        last_updated=date(2026, 5, 26),
    )
    base.update(over)
    return NoteData(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Frontmatter + body present
# ---------------------------------------------------------------------------
def test_render_contains_frontmatter_and_body() -> None:
    note = render_note(_data())
    assert "symbol: HDFCBANK" in note
    assert "isin: INE040A01034" in note
    assert "sector: Financials" in note
    assert "title: HDFC Bank Ltd" in note
    assert "# HDFC Bank Ltd" in note
    assert ANNOTATION_MARKER in note
    assert "Data sourced from:" in note  # default footer
    assert note.strip().endswith("---")


# ---------------------------------------------------------------------------
# 2. Null price renders null, not a fabricated number
# ---------------------------------------------------------------------------
def test_render_null_price() -> None:
    note = render_note(_data(latest_close=None, latest_date=None))
    assert "latest_close: null" in note
    assert "latest_date: null" in note
    assert "No price data" in note


# ---------------------------------------------------------------------------
# 3. Index membership in frontmatter (block list) + body
# ---------------------------------------------------------------------------
def test_render_indices() -> None:
    note = render_note(_data())
    assert "indices:" in note
    assert "  - NIFTY50" in note
    assert "  - NIFTYBANK" in note
    assert "NIFTY50, NIFTYBANK, NIFTY100" in note  # body line


def test_render_no_indices() -> None:
    note = render_note(_data(indices=[]))
    assert "indices: []" in note


# ---------------------------------------------------------------------------
# 4. Corporate events rendered as dated bullet lines
# ---------------------------------------------------------------------------
def test_render_events() -> None:
    note = render_note(_data())
    assert "corporate_events: 3" in note
    assert "- 2024-10-28 · split · factor 2:1" in note
    assert "- 2023-07-14 · dividend · ₹19/share" in note


def test_render_no_events() -> None:
    note = render_note(_data(events_total=0, recent_events=[]))
    assert "corporate_events: 0" in note


# ---------------------------------------------------------------------------
# 5. Tags include stocks + sector + size (when mcap known)
# ---------------------------------------------------------------------------
def test_render_tags_with_mcap() -> None:
    note = render_note(_data(mcap_category="large"))
    assert "tags: [stocks, Financials, large-cap]" in note


def test_render_tags_without_mcap() -> None:
    note = render_note(_data(mcap_category=None))
    assert "tags: [stocks, Financials]" in note


# ---------------------------------------------------------------------------
# 6. Re-render preserves operator annotations after the marker
# ---------------------------------------------------------------------------
def test_preserve_annotations() -> None:
    existing = (
        "---\nsymbol: HDFCBANK\nlatest_close: 1.00\n---\n# Old\n"
        f"## Notes\n<!-- agent-managed above this line -->\n{ANNOTATION_MARKER}\n"
        "MY HAND-WRITTEN THESIS\nbuy more on dips\n"
    )
    note = render_note(_data(latest_close=Decimal("1642.50")), existing=existing)
    assert "MY HAND-WRITTEN THESIS" in note
    assert "buy more on dips" in note
    assert "latest_close: 1642.50" in note  # header regenerated
    assert "latest_close: 1.00" not in note  # old header gone


def test_default_footer_when_no_existing() -> None:
    note = render_note(_data(), existing=None)
    assert "Data sourced from:" in note


# ---------------------------------------------------------------------------
# 7. Filename derives from symbol
# ---------------------------------------------------------------------------
def test_note_filename() -> None:
    assert note_filename("HDFCBANK") == "HDFCBANK.md"
