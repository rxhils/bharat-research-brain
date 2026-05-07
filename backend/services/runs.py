"""Helpers for the `data_ingestion_runs` audit table.

Every agent run opens a row here at start (status='running') and closes it
at finish with status, row_count, error_message, and provenance metadata.
Wraps SQLAlchemy session boilerplate so agent code stays focused on its job.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import DataIngestionRun


async def open_run(
    session: AsyncSession,
    *,
    agent_name: str,
    run_id: uuid.UUID,
    source_url: str | None = None,
    source_name: str | None = None,
) -> int:
    """Insert a 'running' row into `data_ingestion_runs`. Returns the row's id.

    Caller is responsible for committing the session.
    """
    row = DataIngestionRun(
        agent_name=agent_name,
        run_id=run_id,
        status="running",
        source_url=source_url,
        source_name=source_name,
    )
    session.add(row)
    await session.flush()
    return row.id


async def close_run(
    session: AsyncSession,
    *,
    run_pk: int,
    status: str,
    error_message: str | None = None,
    row_count: int | None = None,
    metadata: dict[str, Any] | None = None,
    source_url: str | None = None,
    source_name: str | None = None,
    downloaded_at_utc: datetime | None = None,
    file_sha256: str | None = None,
    source_trade_date: date | None = None,
) -> None:
    """Patch the run row with `finished_at`, `status`, and provenance fields.

    Caller is responsible for committing the session.
    """
    run = await session.get(DataIngestionRun, run_pk)
    if run is None:
        raise ValueError(f"data_ingestion_runs row {run_pk} not found")

    run.finished_at = datetime.now(UTC)
    run.status = status
    if error_message is not None:
        run.error_message = error_message
    if row_count is not None:
        run.row_count = row_count
    if metadata is not None:
        run.metadata_ = metadata
    if source_url is not None:
        run.source_url = source_url
    if source_name is not None:
        run.source_name = source_name
    if downloaded_at_utc is not None:
        run.downloaded_at_utc = downloaded_at_utc
    if file_sha256 is not None:
        run.file_sha256 = file_sha256
    if source_trade_date is not None:
        run.source_trade_date = source_trade_date
