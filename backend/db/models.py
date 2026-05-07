from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class SchemaVersion(Base):
    """Operational migration log.

    Updated by every Alembic migration's final op. Distinct from Alembic's
    internal alembic_version table — gives operators a one-query summary of
    project schema history with descriptions.
    """

    __tablename__ = "schema_version"

    version_label: Mapped[str] = mapped_column(String(32), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    description: Mapped[str | None] = mapped_column(Text)
    chunk_reference: Mapped[str | None] = mapped_column(String(32))


class Stock(Base):
    """Universe master row per ISIN.

    Mutable parent table. All updates MUST flow through the ORM so
    `updated_at` is maintained via SQLAlchemy `onupdate=func.now()`.
    Identity / classification changes are recorded in `stock_identifiers`
    (SCD Type 2). Delisted stocks carry `delisted_on`; rows are never deleted.
    """

    __tablename__ = "stocks"

    isin: Mapped[str] = mapped_column(String(12), primary_key=True)
    nse_symbol: Mapped[str | None] = mapped_column(String(20))
    bse_symbol: Mapped[str | None] = mapped_column(String(20))
    yfinance_symbol: Mapped[str | None] = mapped_column(String(24))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    sector: Mapped[str | None] = mapped_column(String(80))
    mcap_category: Mapped[str | None] = mapped_column(String(8))
    mcap_inr_cr: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    listed_on: Mapped[date | None] = mapped_column(Date)
    delisted_on: Mapped[date | None] = mapped_column(Date)
    is_fno: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    lot_size_fno: Mapped[int | None] = mapped_column(Integer)
    last_refreshed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("length(isin) = 12", name="isin_length"),
        CheckConstraint(
            "mcap_category IS NULL OR mcap_category IN ('large','mid','small','micro')",
            name="mcap_category_allowed",
        ),
        CheckConstraint(
            "delisted_on IS NULL OR listed_on IS NULL OR delisted_on >= listed_on",
            name="delisted_after_listed",
        ),
        Index(
            "idx_stocks_nse_symbol_active",
            "nse_symbol",
            unique=True,
            postgresql_where=text("delisted_on IS NULL"),
        ),
        Index(
            "idx_stocks_bse_symbol_active",
            "bse_symbol",
            unique=True,
            postgresql_where=text("delisted_on IS NULL"),
        ),
        Index("idx_stocks_sector", "sector"),
        Index(
            "idx_stocks_active",
            "delisted_on",
            postgresql_where=text("delisted_on IS NULL"),
        ),
        # idx_stocks_name_trgm (GIN gin_trgm_ops on company_name) added by
        # hand in the 0001 migration — autogenerate is blind to trigram.
    )


class StockIdentifier(Base):
    """SCD Type 2 history of identity / classification fields per stock.

    Append-only with effective-date close-out. When the Universe Agent
    detects a change, it end-dates the current row (sets `effective_to`)
    and inserts a new row. Cascades on stock deletion since identity history
    is rebuildable from sources.
    """

    __tablename__ = "stock_identifiers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("stocks.isin", ondelete="CASCADE"),
        nullable=False,
    )
    identifier_type: Mapped[str] = mapped_column(String(24), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "identifier_type IN ('nse_symbol','bse_symbol','company_name',"
            "'industry','sector','mcap_category','lot_size_fno','is_fno')",
            name="identifier_type_allowed",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="effective_range",
        ),
        UniqueConstraint(
            "isin",
            "identifier_type",
            "effective_from",
            name="stock_identifiers_isin_type_effective_from",
        ),
        Index(
            "idx_stock_identifiers_lookup",
            "isin",
            "identifier_type",
            text("effective_from DESC"),
        ),
        Index(
            "idx_stock_identifiers_current",
            "isin",
            "identifier_type",
            postgresql_where=text("effective_to IS NULL"),
        ),
        Index("idx_stock_identifiers_reverse", "identifier_type", "value"),
    )


class MarketIndex(Base):
    """Index registry (Nifty 50 / 100 / 200 / 500 + sectorals + thematics).

    Mutable parent table; all updates MUST flow through the ORM. Renamed
    `MarketIndex` in Python to avoid collision with `sqlalchemy.Index`;
    DB table name remains `indices`.
    """

    __tablename__ = "indices"

    index_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    index_name: Mapped[str] = mapped_column(String(120), nullable=False)
    index_type: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "index_type IN ('broad','sector','thematic')",
            name="index_type_allowed",
        ),
    )


class IndexConstituent(Base):
    """Slowly-changing membership of stocks in indices.

    Source of truth for survivorship-bias-free backtests. Append-only with
    `effective_to` close-out. Backtest queries MUST filter
    `effective_from <= trade_date < effective_to` (CLAUDE.md §4).
    """

    __tablename__ = "index_constituents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    index_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("indices.index_code", ondelete="RESTRICT"),
        nullable=False,
    )
    isin: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("stocks.isin", ondelete="RESTRICT"),
        nullable=False,
    )
    weight_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    recorded_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="effective_range",
        ),
        UniqueConstraint(
            "index_code",
            "isin",
            "effective_from",
            name="constituents_index_isin_effective_from",
        ),
        Index(
            "idx_constituents_lookup",
            "index_code",
            "isin",
            text("effective_from DESC"),
        ),
        Index(
            "idx_constituents_active",
            "index_code",
            "effective_to",
            postgresql_where=text("effective_to IS NULL"),
        ),
        Index(
            "idx_constituents_isin_history",
            "isin",
            text("effective_from DESC"),
        ),
    )


class PriceEod(Base):
    """End-of-day OHLCV + delivery per (trade_date, isin).

    Raw values from source — no `adj_*` columns yet (Phase 2.5). Composite PK
    `(trade_date, isin)` ordered to match future PARTITION BY RANGE(trade_date).
    """

    __tablename__ = "prices_eod"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    isin: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("stocks.isin", ondelete="RESTRICT"),
        primary_key=True,
    )
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    prev_close: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    turnover_inr: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    delivery_qty: Mapped[int | None] = mapped_column(BigInteger)
    delivery_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    trade_count: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    ingestion_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("data_ingestion_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    inserted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("open IS NULL OR open >= 0", name="open_non_negative"),
        CheckConstraint(
            "high IS NULL OR low IS NULL OR high >= low",
            name="high_ge_low",
        ),
        CheckConstraint(
            "delivery_pct IS NULL OR (delivery_pct >= 0 AND delivery_pct <= 100)",
            name="delivery_pct_range",
        ),
        CheckConstraint("volume IS NULL OR volume >= 0", name="volume_non_negative"),
        CheckConstraint(
            "source IN ('nse_bhavcopy','openalgo','yfinance')",
            name="source_allowed",
        ),
        Index("idx_prices_eod_isin_date", "isin", text("trade_date DESC")),
        Index("idx_prices_eod_source_date", "source", text("trade_date DESC")),
    )


class CorporateAction(Base):
    """Splits, bonuses, dividends, rights, spinoffs, mergers.

    Insert-only. Drives Phase 2.5 adjusted-price computation.
    """

    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    isin: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("stocks.isin", ondelete="RESTRICT"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date)
    announcement_date: Mapped[date | None] = mapped_column(Date)
    ratio_numerator: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    ratio_denominator: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    amount_inr: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('split','bonus','dividend','rights','spinoff','merger')",
            name="action_type_allowed",
        ),
        UniqueConstraint(
            "isin",
            "action_type",
            "ex_date",
            name="corporate_actions_isin_type_exdate",
        ),
        Index("idx_ca_isin_exdate", "isin", text("ex_date DESC")),
        Index("idx_ca_exdate", "ex_date"),
    )


class TradingCalendar(Base):
    """Per-exchange open/closed flag for every calendar day.

    Mutable parent table; all updates MUST flow through the ORM. Holiday rows
    populate `holiday_name`; weekend rows use 'Weekend'. Diwali muhurat sessions
    are separate rows with `session_type='muhurat'`.
    """

    __tablename__ = "trading_calendar"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    exchange: Mapped[str] = mapped_column(
        String(8), primary_key=True, server_default=text("'NSE'")
    )
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)
    session_type: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'regular'")
    )
    holiday_name: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "session_type IN ('regular','muhurat','closed')",
            name="session_type_allowed",
        ),
        CheckConstraint("exchange IN ('NSE','BSE')", name="exchange_allowed"),
        CheckConstraint(
            "NOT is_open OR session_type <> 'closed'",
            name="open_session_consistent",
        ),
        Index(
            "idx_calendar_open",
            "exchange",
            "trade_date",
            postgresql_where=text("is_open"),
        ),
    )


class DataIngestionRun(Base):
    """One row per agent invocation. Captures source, file hash, status.

    Every `prices_eod` row references one. `data_quality_log` rows optionally do.
    """

    __tablename__ = "data_ingestion_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        server_default=text("gen_random_uuid()"),
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'running'")
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str | None] = mapped_column(String(64))
    downloaded_at_utc: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    file_sha256: Mapped[str | None] = mapped_column(CHAR(64))
    row_count: Mapped[int | None] = mapped_column(BigInteger)
    source_trade_date: Mapped[date | None] = mapped_column(Date)
    error_message: Mapped[str | None] = mapped_column(Text)
    # `metadata` is reserved on DeclarativeBase — Python attr is `metadata_`,
    # SQL column is `metadata`. Access via `run.metadata_` in app code.
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','success','failed','partial')",
            name="status_allowed",
        ),
        CheckConstraint(
            "file_sha256 IS NULL OR length(file_sha256) = 64",
            name="sha256_length",
        ),
        Index(
            "idx_ingestion_agent_started",
            "agent_name",
            text("started_at DESC"),
        ),
        Index(
            "idx_ingestion_failed",
            "status",
            text("started_at DESC"),
            postgresql_where=text("status <> 'success'"),
        ),
    )


class DataQualityLog(Base):
    """Structured warnings / errors emitted by the Data Quality Agent.

    Cascades on stock deletion (rebuildable). Run linkage uses SET NULL so
    quality events outlive defective run rows defensively.
    """

    __tablename__ = "data_quality_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("data_ingestion_runs.id", ondelete="SET NULL"),
    )
    isin: Mapped[str | None] = mapped_column(
        String(12),
        ForeignKey("stocks.isin", ondelete="CASCADE"),
    )
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(64))

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info','warn','error')",
            name="severity_allowed",
        ),
        Index(
            "idx_dql_open",
            "severity",
            text("detected_at DESC"),
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index("idx_dql_isin", "isin", text("detected_at DESC")),
        Index("idx_dql_code", "code", text("detected_at DESC")),
    )
