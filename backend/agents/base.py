"""BaseAgent abstract class + run-lifecycle bookkeeping.

Every agent subclasses `BaseAgent` and implements `_execute(ctx)` plus
`health()`. The `run` method (defined here) wraps `_execute` with:

  1. Insert a row in `data_ingestion_runs` with status='running'.
  2. Call subclass `_execute(ctx)`.
  3. Update the run row with finished_at, status, row_count, metadata.
  4. On `BharatError` subclasses: log to the run row as 'failed' and re-raise.

Subclasses MUST NOT override `run`. They override `_execute`.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import ClassVar

import structlog

from backend.db.session import SessionLocal
from backend.errors import BharatError

log = structlog.get_logger()


@dataclass
class RunContext:
    """Per-invocation context passed into an agent's `_execute`."""

    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    operator_invoked: bool = True
    trade_date: date | None = None


@dataclass
class AgentResult:
    """Structured outcome of a single agent run."""

    status: str = "success"  # 'success' | 'failed' | 'partial'
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_deleted: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    vault_writes: list[str] = field(default_factory=list)
    telegram_alerts: list[str] = field(default_factory=list)


@dataclass
class HealthStatus:
    """Lightweight per-agent health probe result."""

    healthy: bool
    detail: str = ""


class BaseAgent(ABC):
    """Abstract base for every agent in the system.

    Subclasses set `name` as a `ClassVar[str]` and implement `_execute` + `health`.
    Subclasses MUST NOT override `run` — it owns the run-lifecycle contract.
    """

    name: ClassVar[str] = ""

    def __init__(self) -> None:
        if not self.name:
            raise ValueError(
                f"{type(self).__name__} must set ClassVar `name` (e.g. name = 'universe')"
            )

    async def run(self, ctx: RunContext) -> AgentResult:
        """Wraps subclass `_execute` with run-lifecycle bookkeeping."""
        # Lazy import to avoid circular: services.runs → models → base.
        from backend.services.runs import close_run, open_run

        bound_log = log.bind(agent=self.name, run_id=str(ctx.run_id))
        bound_log.info("agent.run.start", started_at=ctx.started_at.isoformat())

        async with SessionLocal() as session:
            run_pk = await open_run(session, agent_name=self.name, run_id=ctx.run_id)
            await session.commit()

        try:
            result = await self._execute(ctx)
        except BharatError as exc:
            bound_log.error(
                "agent.run.error",
                exc_type=type(exc).__name__,
                exc_msg=str(exc),
            )
            async with SessionLocal() as session:
                await close_run(
                    session,
                    run_pk=run_pk,
                    status="failed",
                    error_message=f"{type(exc).__name__}: {exc}",
                    row_count=0,
                    metadata={"exception": type(exc).__name__},
                )
                await session.commit()
            raise

        async with SessionLocal() as session:
            await close_run(
                session,
                run_pk=run_pk,
                status=result.status,
                error_message="\n".join(result.errors) if result.errors else None,
                row_count=result.rows_inserted + result.rows_updated + result.rows_deleted,
                metadata={
                    "warnings": result.warnings,
                    "metrics": result.metrics,
                    "vault_writes": result.vault_writes,
                    "telegram_alerts": result.telegram_alerts,
                },
            )
            await session.commit()

        bound_log.info(
            "agent.run.finish",
            status=result.status,
            inserted=result.rows_inserted,
            updated=result.rows_updated,
            deleted=result.rows_deleted,
            warnings=len(result.warnings),
        )
        return result

    @abstractmethod
    async def _execute(self, ctx: RunContext) -> AgentResult:
        """Subclass implements the agent's actual work here."""

    @abstractmethod
    async def health(self) -> HealthStatus:
        """Subclass returns whether the agent's prerequisites are met."""
