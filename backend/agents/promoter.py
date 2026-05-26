"""Promoter Agent (Chunk 4.9 improvement 5) — promoter holding + pledge ingest.

File-ingest, same shape as the FII/DII agent (Chunk 3.6): the operator downloads
BSE shareholding-pattern XBRL/XML files quarterly and the agent parses them. No
NSE/BSE scraping (CLAUDE.md §2 rule 5) — only a locally-saved file.

`classify_pledge_risk` and `parse_promoter_xml` are pure (unit tested);
`fetch_records` reads a local file; `run` validates ISINs against the universe
and upserts into `promoter_signals`. A high promoter pledge is a governance red
flag, so `pledge_risk_flag` feeds a Risk Agent adjustment.

PARSER NOTE: BSE XBRL tag names vary by template/namespace. The parser is
tolerant — it strips namespaces and matches by local element name against an
alias set. The exact tag aliases should be confirmed against a real downloaded
file (follow-up in AGENTS.md §16); the contract used here is one ISIN element
plus sibling holding/pledge/date elements per record.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

import structlog

log = structlog.get_logger()

SOURCE = "bse_xbrl_file"

# Pledge-risk bands (% of promoter holding that is pledged). Lower-bound
# inclusive; >=50% is critical.
_MODERATE_MIN = Decimal("10")
_HIGH_MIN = Decimal("30")
_CRITICAL_MIN = Decimal("50")

# Tolerant local-name aliases (lower-cased, namespace-stripped).
_ISIN_TAGS = {"isin"}
_DATE_TAGS = {"reportdate", "quarterend", "quarterenddate", "asondate", "date"}
_HOLDING_TAGS = {
    "promoterholdingpct",
    "promoterholding",
    "promotershareholdingpct",
    "promotergroupholdingpct",
    "shareholdingofpromoterandpromotergroup",
}
_PLEDGED_TAGS = {
    "promoterpledgedpct",
    "pledgedpct",
    "pledged",
    "sharespledgedpct",
    "encumberedpct",
    "percentageofsharespledged",
}


@dataclass(frozen=True)
class RawPromoter:
    isin: str
    report_date: date
    promoter_holding_pct: Decimal | None
    promoter_pledged_pct: Decimal | None


@dataclass(frozen=True)
class PromoterRow:
    isin: str
    report_date: date
    promoter_holding_pct: Decimal | None
    promoter_pledged_pct: Decimal | None
    pledge_risk_flag: str
    source: str = SOURCE


@dataclass
class PromoterResult:
    rows_parsed: int = 0
    rows_upserted: int = 0
    rows_skipped_unknown_isin: int = 0
    rows: list[PromoterRow] = field(default_factory=list)


def classify_pledge_risk(pledged_pct: Decimal | None) -> str:
    """Map promoter-pledged % to safe / moderate / high / critical.

    None (no pledge reported) -> safe. Bands: <10 safe, 10-30 moderate,
    30-50 high, >=50 critical.
    """
    if pledged_pct is None:
        return "safe"
    if pledged_pct < _MODERATE_MIN:
        return "safe"
    if pledged_pct < _HIGH_MIN:
        return "moderate"
    if pledged_pct < _CRITICAL_MIN:
        return "high"
    return "critical"


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].strip().lower()


def _parse_date(raw: str) -> date | None:
    s = raw.strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_pct(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    s = raw.strip().replace(",", "").replace("%", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_promoter_xml(text: str) -> list[RawPromoter]:
    """Parse a BSE shareholding-pattern XML/XBRL into RawPromoter rows.

    Tolerant: each record is an element containing an ISIN child; the holding,
    pledge, and report-date siblings are matched by local tag name. Records
    missing an ISIN or a parseable date are skipped.
    """
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        log.warning("promoter.parse.bad_xml", error=str(exc))
        return []

    parent_map = {child: parent for parent in root.iter() for child in parent}
    rows: list[RawPromoter] = []
    for el in root.iter():
        if _localname(el.tag) not in _ISIN_TAGS or not (el.text and el.text.strip()):
            continue
        parent = parent_map.get(el)
        if parent is None:
            continue
        fields = {_localname(c.tag): (c.text or "").strip() for c in parent}
        isin = (el.text or "").strip()
        report_date = next(
            (_parse_date(fields[k]) for k in _DATE_TAGS if fields.get(k)), None
        )
        if report_date is None:
            log.warning("promoter.parse.no_date", isin=isin)
            continue
        holding = next(
            (_parse_pct(fields[k]) for k in _HOLDING_TAGS if fields.get(k)), None
        )
        pledged = next(
            (_parse_pct(fields[k]) for k in _PLEDGED_TAGS if fields.get(k)), None
        )
        rows.append(RawPromoter(isin, report_date, holding, pledged))
    return rows


def _to_row(raw: RawPromoter) -> PromoterRow:
    return PromoterRow(
        isin=raw.isin,
        report_date=raw.report_date,
        promoter_holding_pct=raw.promoter_holding_pct,
        promoter_pledged_pct=raw.promoter_pledged_pct,
        pledge_risk_flag=classify_pledge_risk(raw.promoter_pledged_pct),
        source=SOURCE,
    )


class PromoterAgent:
    name = "promoter"

    async def fetch_records(self, path: str | None) -> list[PromoterRow]:
        """Read + parse + classify a local BSE shareholding file. [] on any issue."""
        if not path:
            log.warning("promoter.fetch.no_file", reason="no path provided")
            return []
        text = await asyncio.to_thread(self._read_file, path)
        if text is None:
            return []
        return [_to_row(r) for r in parse_promoter_xml(text)]

    @staticmethod
    def _read_file(path: str) -> str | None:
        p = Path(path)
        if not p.exists():
            log.warning("promoter.fetch.missing", path=path)
            return None
        try:
            return p.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("promoter.fetch.read_failed", path=path, error=str(exc))
            return None

    async def run(
        self, *, path: str | None = None, dry_run: bool = False
    ) -> PromoterResult:
        from backend.db.repositories import promoter as promoter_repo
        from backend.db.session import SessionLocal

        rows = await self.fetch_records(path)
        result = PromoterResult(rows_parsed=len(rows), rows=rows)
        if dry_run or not rows:
            log.info(
                "promoter.run.done",
                parsed=result.rows_parsed,
                upserted=0,
                dry_run=dry_run,
            )
            return result

        async with SessionLocal() as session:
            known = await promoter_repo.fetch_known_isins(
                session, [r.isin for r in rows]
            )
            valid = [r for r in rows if r.isin in known]
            result.rows_skipped_unknown_isin = len(rows) - len(valid)
            if valid:
                payload = [_row_to_dict(r) for r in valid]
                result.rows_upserted = await promoter_repo.bulk_upsert(
                    session, payload
                )
                await session.commit()

        log.info(
            "promoter.run.done",
            parsed=result.rows_parsed,
            upserted=result.rows_upserted,
            skipped_unknown_isin=result.rows_skipped_unknown_isin,
            dry_run=dry_run,
        )
        return result


def _row_to_dict(row: PromoterRow) -> dict[str, object]:
    return {
        "isin": row.isin,
        "report_date": row.report_date,
        "promoter_holding_pct": row.promoter_holding_pct,
        "promoter_pledged_pct": row.promoter_pledged_pct,
        "pledge_risk_flag": row.pledge_risk_flag,
        "source": row.source,
    }
