"""Universe Agent — builds the tradable-universe master from exchange CSVs.

Responsibilities (Phase 1, Chunk 1.2, commit 13):
  1. Fetch the NSE equity security master (canonical company/listing fields).
  2. Fetch index-constituent CSVs for every seeded, non-deferred index.
  3. Reconcile against current DB state via the generic diff engine and apply
     SCD-2 changes to `stocks`, `stock_identifiers`, and `index_constituents`.

Design split:
  - `build_plan(...)` is PURE (no I/O). It is the agent's brain and is unit
    tested directly.
  - `UniverseAgent.plan()` (read-only) and `._execute()` (apply) are thin
    orchestration: fetch → load current → build_plan → [apply].

Scope notes:
  - NIFTYFINSERVICE filename is deferred — skipped cleanly, its existing
    memberships are preserved (never closed).
  - Leaving an index is NOT a delisting: the membership row is closed but the
    stock row is left untouched. `delisted_on` is out of scope for commit 13.
  - F&O fields (`is_fno`, `lot_size_fno`) are out of scope — a separate
    monthly refresh owns them (CLAUDE.md §4).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import ClassVar

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents._diff import diff_keyed
from backend.agents.base import AgentResult, BaseAgent, HealthStatus, RunContext
from backend.data_sources.niftyindices import (
    _DEFERRED_FILENAME,
    NIFTYINDICES_FILENAMES,
    Constituent,
    NiftyIndicesClient,
)
from backend.data_sources.nse_archives import NSEArchivesClient, NSESecurity
from backend.data_sources.openalgo import OpenAlgoClient
from backend.data_sources.sector_mapping import harmonize_sector
from backend.db.models import IndexConstituent, MarketIndex, Stock, StockIdentifier
from backend.db.repositories import index_constituents as constituents_repo
from backend.db.repositories import stock_identifiers as identifiers_repo
from backend.db.repositories import stocks as stocks_repo
from backend.db.repositories._helpers import today_ist
from backend.db.session import SessionLocal
from backend.errors import DataSourceError

log = structlog.get_logger()

SOURCE_MASTER = "nse_archives"
SOURCE_INDEX = "niftyindices"

# Fields tracked in stock_identifiers SCD-2 history. A change to any of these
# end-dates the current identifier row and opens a new one.
TRACKED_FIELDS: tuple[str, ...] = ("nse_symbol", "company_name", "industry", "sector")

_IDENTIFIER_SOURCE: dict[str, str] = {
    "nse_symbol": SOURCE_MASTER,
    "company_name": SOURCE_MASTER,
    "industry": SOURCE_INDEX,
    "sector": SOURCE_INDEX,
}


# ---------------------------------------------------------------------------
# Plan value objects
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class StockFields:
    """The mutable stock fields that drive the diff and SCD-2 identifier rows."""

    nse_symbol: str | None
    company_name: str
    industry: str | None
    sector: str | None


@dataclass(frozen=True)
class DesiredStock:
    """A stock as the sources say it should be, ready for insert."""

    isin: str
    nse_symbol: str | None
    company_name: str
    industry: str | None
    sector: str | None
    listed_on: date | None

    def fields(self) -> StockFields:
        return StockFields(
            nse_symbol=self.nse_symbol,
            company_name=self.company_name,
            industry=self.industry,
            sector=self.sector,
        )


@dataclass
class UniversePlan:
    """A fully-computed reconciliation plan. Pure data — no I/O performed yet."""

    effective_date: date
    securities_count: int
    fetched_indices: list[str]
    deferred_indices: list[str]
    failed_indices: dict[str, str]
    stocks_to_insert: dict[str, DesiredStock] = field(default_factory=dict)
    stocks_to_update: dict[str, list[tuple[str, object, object]]] = field(
        default_factory=dict
    )
    memberships_to_open: list[tuple[str, str]] = field(default_factory=list)
    memberships_to_close: list[tuple[str, str]] = field(default_factory=list)
    unmapped_sectors: dict[str, int] = field(default_factory=dict)
    constituents_missing_master: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "stocks_to_insert": len(self.stocks_to_insert),
            "stocks_to_update": len(self.stocks_to_update),
            "memberships_to_open": len(self.memberships_to_open),
            "memberships_to_close": len(self.memberships_to_close),
        }

    def has_changes(self) -> bool:
        return bool(
            self.stocks_to_insert
            or self.stocks_to_update
            or self.memberships_to_open
            or self.memberships_to_close
        )


# ---------------------------------------------------------------------------
# Pure planner
# ---------------------------------------------------------------------------
def build_plan(
    *,
    securities: list[NSESecurity],
    constituents_by_index: dict[str, list[Constituent]],
    current_stocks: dict[str, StockFields],
    current_memberships: set[tuple[str, str]],
    deferred_indices: list[str],
    failed_indices: dict[str, str],
    effective_date: date,
) -> UniversePlan:
    """Reconcile fetched data against current DB state. Pure; see module doc."""
    master_by_isin: dict[str, NSESecurity] = {}
    for sec in securities:
        master_by_isin.setdefault(sec.isin, sec)

    fetched_indices = sorted(constituents_by_index)
    plan = UniversePlan(
        effective_date=effective_date,
        securities_count=len(master_by_isin),
        fetched_indices=fetched_indices,
        deferred_indices=sorted(deferred_indices),
        failed_indices=dict(failed_indices),
    )

    # ----- Build the desired stock universe (union of all constituents) -----
    desired_stocks: dict[str, DesiredStock] = {}
    for code in fetched_indices:
        for con in constituents_by_index[code]:
            isin = con.isin
            if isin in desired_stocks:
                continue  # first index that lists this ISIN wins
            sec = master_by_isin.get(isin)
            if sec is None:
                plan.constituents_missing_master.append(isin)
            sector, was_mapped = harmonize_sector(con.industry)
            if con.industry and not was_mapped:
                plan.unmapped_sectors[con.industry] = (
                    plan.unmapped_sectors.get(con.industry, 0) + 1
                )
            desired_stocks[isin] = DesiredStock(
                isin=isin,
                nse_symbol=(sec.nse_symbol if sec else con.nse_symbol) or con.nse_symbol,
                company_name=(sec.company_name if sec else con.company_name)
                or con.company_name,
                industry=con.industry,
                sector=sector,
                listed_on=sec.listed_on if sec else None,
            )
    plan.constituents_missing_master.sort()

    # ----- Stocks diff -----
    desired_fields = {isin: ds.fields() for isin, ds in desired_stocks.items()}
    stock_diff = diff_keyed(current=current_stocks, desired=desired_fields)
    for isin in stock_diff.added:
        plan.stocks_to_insert[isin] = desired_stocks[isin]
    for isin, (old, new) in stock_diff.changed.items():
        deltas: list[tuple[str, object, object]] = []
        for fname in TRACKED_FIELDS:
            old_v = getattr(old, fname)
            new_v = getattr(new, fname)
            if old_v != new_v:
                deltas.append((fname, old_v, new_v))
        if deltas:
            plan.stocks_to_update[isin] = deltas
    # `removed` stocks (no longer in any tracked index) are intentionally
    # left in place — leaving an index is not a delisting.

    # ----- Membership diff (only over indices we actually fetched) -----
    desired_membership = {
        (code, con.isin): True
        for code in fetched_indices
        for con in constituents_by_index[code]
    }
    current_for_fetched = {
        (code, isin): True
        for (code, isin) in current_memberships
        if code in constituents_by_index
    }
    member_diff = diff_keyed(current=current_for_fetched, desired=desired_membership)
    plan.memberships_to_open = sorted(member_diff.added)
    plan.memberships_to_close = sorted(member_diff.removed)

    # ----- Warnings (human-readable, for the run record + dry-run output) -----
    if plan.deferred_indices:
        plan.warnings.append(
            f"deferred indices (filename unverified): {', '.join(plan.deferred_indices)}"
        )
    for code, reason in sorted(plan.failed_indices.items()):
        plan.warnings.append(f"index {code} fetch failed: {reason}")
    if plan.unmapped_sectors:
        plan.warnings.append(
            f"unmapped industries (passthrough): {sorted(plan.unmapped_sectors)}"
        )
    if plan.constituents_missing_master:
        plan.warnings.append(
            f"{len(plan.constituents_missing_master)} constituents absent from "
            "security master (inserted from constituent data)"
        )
    return plan


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
class UniverseAgent(BaseAgent):
    """Reconciles the stock universe + index memberships from exchange CSVs."""

    name: ClassVar[str] = "universe"

    def __init__(
        self,
        *,
        nse_client: NSEArchivesClient | None = None,
        nifty_client: NiftyIndicesClient | None = None,
        openalgo_client: OpenAlgoClient | None = None,
    ) -> None:
        super().__init__()
        self.nse = nse_client or NSEArchivesClient()
        self.nifty = nifty_client or NiftyIndicesClient()
        self.openalgo = openalgo_client or OpenAlgoClient()

    # ----- orchestration -----
    async def plan(self, ctx: RunContext) -> UniversePlan:
        """Compute the reconciliation plan WITHOUT writing anything (dry-run)."""
        async with SessionLocal() as session:
            seeded = await self._seeded_index_codes(session)
            current_stocks, current_memberships, _, _, _ = await self._load_current(
                session
            )
        securities, by_index, deferred, failed = await self._fetch(seeded)
        return build_plan(
            securities=securities,
            constituents_by_index=by_index,
            current_stocks=current_stocks,
            current_memberships=current_memberships,
            deferred_indices=deferred,
            failed_indices=failed,
            effective_date=ctx.trade_date or today_ist(),
        )

    async def _execute(self, ctx: RunContext) -> AgentResult:
        eff = ctx.trade_date or today_ist()
        async with SessionLocal() as session:
            seeded = await self._seeded_index_codes(session)
        securities, by_index, deferred, failed = await self._fetch(seeded)

        async with SessionLocal() as session:
            (
                current_stocks,
                current_memberships,
                stock_rows,
                membership_rows,
                identifier_rows,
            ) = await self._load_current(session)
            plan = build_plan(
                securities=securities,
                constituents_by_index=by_index,
                current_stocks=current_stocks,
                current_memberships=current_memberships,
                deferred_indices=deferred,
                failed_indices=failed,
                effective_date=eff,
            )
            await self._apply(
                session,
                plan=plan,
                stock_rows=stock_rows,
                membership_rows=membership_rows,
                identifier_rows=identifier_rows,
                effective_date=eff,
            )
            await session.commit()

        counts = plan.counts()
        return AgentResult(
            status="partial" if plan.failed_indices else "success",
            rows_inserted=counts["stocks_to_insert"] + counts["memberships_to_open"],
            rows_updated=counts["stocks_to_update"] + counts["memberships_to_close"],
            warnings=list(plan.warnings),
            metrics={k: float(v) for k, v in counts.items()}
            | {"securities": float(plan.securities_count)},
        )

    # ----- fetch -----
    async def _fetch(
        self, seeded_codes: list[str]
    ) -> tuple[
        list[NSESecurity], dict[str, list[Constituent]], list[str], dict[str, str]
    ]:
        securities, _ = await self.nse.fetch_security_master()

        by_index: dict[str, list[Constituent]] = {}
        deferred: list[str] = []
        failed: dict[str, str] = {}
        for code in seeded_codes:
            filename = NIFTYINDICES_FILENAMES.get(code)
            if filename is None:
                failed[code] = "no_filename_mapping"
                continue
            if filename == _DEFERRED_FILENAME:
                deferred.append(code)
                continue
            try:
                cons, _ = await self.nifty.fetch_index_constituents(code)
            except DataSourceError as exc:
                if exc.reason_code == "deferred_filename":
                    deferred.append(code)
                else:
                    reason = exc.reason_code or (
                        f"status_{exc.status_code}" if exc.status_code else "error"
                    )
                    failed[code] = reason
                    log.error("universe.index.failed", index_code=code, reason=reason)
                continue
            by_index[code] = cons

        # Tertiary cross-check (stub in Chunk 1.2) — tolerate cleanly.
        oa_symbols, oa_meta = await self.openalgo.fetch_symbol_master()
        if oa_meta.is_stub or not oa_symbols:
            log.info("universe.openalgo.unavailable", is_stub=oa_meta.is_stub)

        return securities, by_index, deferred, failed

    # ----- current state -----
    @staticmethod
    async def _seeded_index_codes(session: AsyncSession) -> list[str]:
        rows = (await session.execute(select(MarketIndex.index_code))).scalars().all()
        return sorted(rows)

    @staticmethod
    async def _load_current(
        session: AsyncSession,
    ) -> tuple[
        dict[str, StockFields],
        set[tuple[str, str]],
        dict[str, Stock],
        dict[tuple[str, str], IndexConstituent],
        dict[tuple[str, str], StockIdentifier],
    ]:
        stock_rows = await stocks_repo.fetch_all_by_isin(session)
        current_stocks = {
            isin: StockFields(
                nse_symbol=row.nse_symbol,
                company_name=row.company_name,
                industry=row.industry,
                sector=row.sector,
            )
            for isin, row in stock_rows.items()
        }
        active = await constituents_repo.fetch_active(session)
        membership_rows = {(c.index_code, c.isin): c for c in active}
        current_memberships = set(membership_rows)
        identifier_rows = await identifiers_repo.fetch_current(session)
        return (
            current_stocks,
            current_memberships,
            stock_rows,
            membership_rows,
            identifier_rows,
        )

    # ----- apply -----
    async def _apply(
        self,
        session: AsyncSession,
        *,
        plan: UniversePlan,
        stock_rows: dict[str, Stock],
        membership_rows: dict[tuple[str, str], IndexConstituent],
        identifier_rows: dict[tuple[str, str], StockIdentifier],
        effective_date: date,
    ) -> None:
        # Inserts: new stock row + an identifier row per non-null tracked field.
        for isin, ds in plan.stocks_to_insert.items():
            await stocks_repo.insert(
                session,
                isin=ds.isin,
                company_name=ds.company_name,
                nse_symbol=ds.nse_symbol,
                industry=ds.industry,
                sector=ds.sector,
                listed_on=ds.listed_on,
            )
            for fname in TRACKED_FIELDS:
                value = getattr(ds, fname)
                if value is None:
                    continue
                await identifiers_repo.open_identifier(
                    session,
                    isin=isin,
                    identifier_type=fname,
                    value=str(value),
                    effective_from=effective_date,
                    source=_IDENTIFIER_SOURCE[fname],
                )

        # Updates: mutate ORM row + close/open identifier rows for changed fields.
        for isin, deltas in plan.stocks_to_update.items():
            row = stock_rows[isin]
            for fname, _old, new in deltas:
                setattr(row, fname, new)
                existing = identifier_rows.get((isin, fname))
                if existing is not None:
                    identifiers_repo.close_identifier(
                        existing, effective_to=effective_date
                    )
                if new is not None:
                    await identifiers_repo.open_identifier(
                        session,
                        isin=isin,
                        identifier_type=fname,
                        value=str(new),
                        effective_from=effective_date,
                        source=_IDENTIFIER_SOURCE[fname],
                    )

        # Membership opens / closes.
        for index_code, isin in plan.memberships_to_open:
            await constituents_repo.open_membership(
                session,
                index_code=index_code,
                isin=isin,
                effective_from=effective_date,
                source=SOURCE_INDEX,
            )
        for index_code, isin in plan.memberships_to_close:
            row = membership_rows[(index_code, isin)]
            constituents_repo.close_membership(row, effective_to=effective_date)

    # ----- health -----
    async def health(self) -> HealthStatus:
        async with SessionLocal() as session:
            seeded = await self._seeded_index_codes(session)
        if not seeded:
            return HealthStatus(healthy=False, detail="no indices seeded")
        buildable = [
            c
            for c in seeded
            if NIFTYINDICES_FILENAMES.get(c) not in (None, _DEFERRED_FILENAME)
        ]
        return HealthStatus(
            healthy=bool(buildable),
            detail=f"{len(buildable)}/{len(seeded)} indices buildable",
        )
