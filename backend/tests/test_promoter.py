"""Tests for the Promoter Agent (Chunk 4.9 improvement 5) — offline, no DB.

`classify_pledge_risk` and `parse_promoter_xml` are pure; `fetch_records` reads a
local XML/XBRL file (operator-downloaded BSE shareholding pattern) and is
exercised via a tmp file. No network, no database.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from backend.agents.promoter import (
    PromoterAgent,
    PromoterRow,
    RawPromoter,
    classify_pledge_risk,
    parse_promoter_xml,
)

_XML = """<?xml version="1.0"?>
<ShareholdingPatterns>
  <Record>
    <ISIN>INE002A01018</ISIN>
    <ReportDate>2026-03-31</ReportDate>
    <PromoterHoldingPct>50.42</PromoterHoldingPct>
    <PromoterPledgedPct>12.5</PromoterPledgedPct>
  </Record>
  <Record>
    <ISIN>INE040A01034</ISIN>
    <ReportDate>2026-03-31</ReportDate>
    <PromoterHoldingPct>25.60</PromoterHoldingPct>
    <PromoterPledgedPct>60.0</PromoterPledgedPct>
  </Record>
</ShareholdingPatterns>
"""

# Same data, namespaced (XBRL files carry namespace prefixes).
_XML_NS = """<?xml version="1.0"?>
<shp:ShareholdingPatterns xmlns:shp="http://bse.example/shp">
  <shp:Record>
    <shp:ISIN>INE002A01018</shp:ISIN>
    <shp:ReportDate>2026-03-31</shp:ReportDate>
    <shp:PromoterHoldingPct>50.42</shp:PromoterHoldingPct>
    <shp:PromoterPledgedPct>12.5</shp:PromoterPledgedPct>
  </shp:Record>
</shp:ShareholdingPatterns>
"""


# ---------------------------------------------------------------------------
# classify_pledge_risk — boundaries (lower-inclusive, >=50 critical)
# ---------------------------------------------------------------------------
def test_classify_pledge_risk_levels() -> None:
    assert classify_pledge_risk(Decimal("5")) == "safe"
    assert classify_pledge_risk(Decimal("9.99")) == "safe"
    assert classify_pledge_risk(Decimal("10")) == "moderate"
    assert classify_pledge_risk(Decimal("29.99")) == "moderate"
    assert classify_pledge_risk(Decimal("30")) == "high"
    assert classify_pledge_risk(Decimal("49.99")) == "high"
    assert classify_pledge_risk(Decimal("50")) == "critical"
    assert classify_pledge_risk(Decimal("75")) == "critical"


def test_classify_pledge_risk_none_is_safe() -> None:
    assert classify_pledge_risk(None) == "safe"


# ---------------------------------------------------------------------------
# parse_promoter_xml — plain + namespaced
# ---------------------------------------------------------------------------
def test_parse_promoter_xml() -> None:
    rows = parse_promoter_xml(_XML)
    assert len(rows) == 2
    assert rows[0] == RawPromoter(
        isin="INE002A01018",
        report_date=date(2026, 3, 31),
        promoter_holding_pct=Decimal("50.42"),
        promoter_pledged_pct=Decimal("12.5"),
    )
    assert rows[1].isin == "INE040A01034"
    assert rows[1].promoter_pledged_pct == Decimal("60.0")


def test_parse_promoter_xml_namespaced() -> None:
    rows = parse_promoter_xml(_XML_NS)
    assert len(rows) == 1
    assert rows[0].isin == "INE002A01018"
    assert rows[0].promoter_pledged_pct == Decimal("12.5")


def test_parse_promoter_xml_empty() -> None:
    assert parse_promoter_xml("<ShareholdingPatterns></ShareholdingPatterns>") == []


# ---------------------------------------------------------------------------
# fetch_records — reads a tmp file, computes pledge_risk_flag
# ---------------------------------------------------------------------------
async def test_fetch_records_classifies(tmp_path: Path) -> None:
    f = tmp_path / "shp.xml"
    f.write_text(_XML, encoding="utf-8")
    rows = await PromoterAgent().fetch_records(str(f))
    assert len(rows) == 2
    assert isinstance(rows[0], PromoterRow)
    # 12.5% pledged -> moderate; 60% pledged -> critical
    assert rows[0].pledge_risk_flag == "moderate"
    assert rows[1].pledge_risk_flag == "critical"
    assert rows[0].source == "bse_xbrl_file"


async def test_fetch_records_missing_file_returns_empty() -> None:
    rows = await PromoterAgent().fetch_records("/no/such/file.xml")
    assert rows == []
