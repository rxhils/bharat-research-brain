"""Vault Writer — renders one Obsidian note per stock (Chunk 1.6).

The note-generation is pure (`render_note`) and unit tested. Data assembly
(`assemble_notes`) pulls from the DB in the container. The actual file writes
to `C:/claude/vault/.../01_Stocks/` are performed by Claude Code via the
filesystem MCP (the container has no access to the host vault path), driven by
the CLI's `--emit` NDJSON output.

Re-write rule: the agent-managed header (everything up to and including the
annotations marker) is regenerated; everything the operator wrote after the
marker is preserved.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CorporateAction, IndexConstituent, PriceEod, Stock
from backend.db.repositories._helpers import today_ist

ANNOTATION_MARKER = "<!-- your annotations below -->"
_AGENT_MARKER = "<!-- agent-managed above this line -->"
_DEFAULT_FOOTER = (
    "\n\nData sourced from: Universe Agent, Price Agent, "
    "Corporate Events Agent.\n\n---\n"
)
_RECENT_EVENTS = 5


@dataclass(frozen=True)
class EventLine:
    ex_date: date
    action_type: str
    detail: str


@dataclass(frozen=True)
class NoteData:
    symbol: str
    title: str
    isin: str
    sector: str | None
    industry: str | None
    listed_on: date | None
    latest_close: Decimal | None
    latest_date: date | None
    indices: list[str]
    events_total: int
    recent_events: list[EventLine]
    mcap_category: str | None
    last_updated: date


def note_filename(symbol: str) -> str:
    return f"{symbol}.md"


def _num(d: Decimal) -> str:
    """Compact decimal string without scientific notation (2.0000 -> '2')."""
    return format(d.normalize(), "f")


def _yaml_date(d: date | None) -> str:
    return d.isoformat() if d is not None else "null"


def event_detail(
    action_type: str,
    *,
    ratio_numerator: Decimal | None,
    ratio_denominator: Decimal | None,
    amount_inr: Decimal | None,
) -> str:
    if action_type == "split" and ratio_numerator is not None:
        den = ratio_denominator if ratio_denominator is not None else Decimal(1)
        return f"factor {_num(ratio_numerator)}:{_num(den)}"
    if action_type == "dividend" and amount_inr is not None:
        return f"₹{_num(amount_inr)}/share"
    if ratio_numerator is not None and ratio_denominator is not None:
        return f"ratio {_num(ratio_numerator)}:{_num(ratio_denominator)}"
    if amount_inr is not None:
        return f"₹{_num(amount_inr)}"
    return action_type


def _render_agent_section(d: NoteData) -> str:
    tags = ["stocks"]
    if d.sector:
        tags.append(d.sector)
    if d.mcap_category:
        tags.append(f"{d.mcap_category}-cap")

    lines = ["---"]
    lines.append(f"title: {d.title}")
    lines.append(f"symbol: {d.symbol}")
    lines.append(f"isin: {d.isin}")
    lines.append(f"sector: {d.sector or 'null'}")
    lines.append(f"industry: {d.industry or 'null'}")
    lines.append(f"listed_on: {_yaml_date(d.listed_on)}")
    lines.append(
        f"latest_close: {f'{d.latest_close:.2f}' if d.latest_close is not None else 'null'}"
    )
    lines.append(f"latest_date: {_yaml_date(d.latest_date)}")
    if d.indices:
        lines.append("indices:")
        lines.extend(f"  - {code}" for code in d.indices)
    else:
        lines.append("indices: []")
    lines.append(f"corporate_events: {d.events_total}")
    lines.append(f"last_updated: {d.last_updated.isoformat()}")
    lines.append(f"tags: [{', '.join(tags)}]")
    lines.append("---")
    lines.append("")
    lines.append(f"# {d.title}")
    lines.append("")
    lines.append(f"**Symbol:** {d.symbol} · **ISIN:** {d.isin}")
    lines.append(f"**Sector:** {d.sector or '—'} · **Industry:** {d.industry or '—'}")
    lines.append(f"**Listed:** {_yaml_date(d.listed_on)}")
    lines.append("")
    lines.append("## Index membership")
    lines.append(f"- {', '.join(d.indices)}" if d.indices else "- (none)")
    lines.append("")
    lines.append("## Latest price")
    if d.latest_close is not None and d.latest_date is not None:
        lines.append(f"₹{d.latest_close:,.2f} as of {d.latest_date.isoformat()}")
    else:
        lines.append("No price data available.")
    lines.append("")
    lines.append("## Corporate events (last 5 years)")
    if d.recent_events:
        lines.extend(
            f"- {e.ex_date.isoformat()} · {e.action_type} · {e.detail}"
            for e in d.recent_events
        )
    else:
        lines.append("No corporate events recorded.")
    lines.append("")
    lines.append("## Notes")
    lines.append(_AGENT_MARKER)
    lines.append(ANNOTATION_MARKER)
    return "\n".join(lines)


def render_note(data: NoteData, existing: str | None = None) -> str:
    """Full note. Regenerates the agent header; preserves post-marker content."""
    header = _render_agent_section(data)
    if existing and ANNOTATION_MARKER in existing:
        suffix = existing.split(ANNOTATION_MARKER, 1)[1]
    else:
        suffix = _DEFAULT_FOOTER
    return header + suffix


# ---------------------------------------------------------------------------
# DB assembly (runs in the container)
# ---------------------------------------------------------------------------
async def assemble_notes(
    session: AsyncSession,
    *,
    symbol: str | None = None,
    limit: int | None = None,
) -> list[NoteData]:
    stmt = select(Stock).where(Stock.delisted_on.is_(None))
    if symbol is not None:
        stmt = stmt.where(Stock.nse_symbol == symbol)
    stmt = stmt.order_by(Stock.nse_symbol)
    if limit is not None:
        stmt = stmt.limit(limit)
    stocks = list((await session.execute(stmt)).scalars().all())

    latest = {
        isin: (d, close)
        for isin, d, close in (
            await session.execute(
                select(PriceEod.isin, PriceEod.trade_date, PriceEod.close)
                .distinct(PriceEod.isin)
                .order_by(PriceEod.isin, PriceEod.trade_date.desc())
            )
        ).all()
    }

    indices: dict[str, list[str]] = {}
    for code, isin in (
        await session.execute(
            select(IndexConstituent.index_code, IndexConstituent.isin).where(
                IndexConstituent.effective_to.is_(None)
            )
        )
    ).all():
        indices.setdefault(isin, []).append(code)

    counts = {
        isin: n
        for isin, n in (
            await session.execute(
                select(CorporateAction.isin, func.count()).group_by(
                    CorporateAction.isin
                )
            )
        ).all()
    }

    recent: dict[str, list[EventLine]] = {}
    for ca in (
        (
            await session.execute(
                select(CorporateAction).order_by(
                    CorporateAction.isin, CorporateAction.ex_date.desc()
                )
            )
        )
        .scalars()
        .all()
    ):
        bucket = recent.setdefault(ca.isin, [])
        if len(bucket) < _RECENT_EVENTS:
            bucket.append(
                EventLine(
                    ca.ex_date,
                    ca.action_type,
                    event_detail(
                        ca.action_type,
                        ratio_numerator=ca.ratio_numerator,
                        ratio_denominator=ca.ratio_denominator,
                        amount_inr=ca.amount_inr,
                    ),
                )
            )

    today = today_ist()
    notes: list[NoteData] = []
    for s in stocks:
        lp = latest.get(s.isin)
        notes.append(
            NoteData(
                symbol=s.nse_symbol or s.isin,
                title=s.company_name,
                isin=s.isin,
                sector=s.sector,
                industry=s.industry,
                listed_on=s.listed_on,
                latest_close=lp[1] if lp else None,
                latest_date=lp[0] if lp else None,
                indices=sorted(indices.get(s.isin, [])),
                events_total=counts.get(s.isin, 0),
                recent_events=recent.get(s.isin, []),
                mcap_category=s.mcap_category,
                last_updated=today,
            )
        )
    return notes
