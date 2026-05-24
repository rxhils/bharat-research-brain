"""bharat-research-brain operator CLI.

Run inside the backend container:

    docker compose exec backend python -m backend.cli <command>

Subcommands:
    version                       — package + alembic + schema_version
    health                        — probe FastAPI /health endpoint
    universe build [--dry-run]    — Universe Agent (stub until commit 13)
    universe show [--limit N]     — current universe (stub until commit 13)
"""
from __future__ import annotations

import asyncio
import os

# Configure logging before any module that calls structlog.get_logger() at import.
from backend.logging_setup import configure_logging

configure_logging(os.getenv("LOG_FORMAT", "console"))

import structlog  # noqa: E402
import typer  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

log = structlog.get_logger()
console = Console()

app = typer.Typer(help="bharat-research-brain CLI", no_args_is_help=True)
universe_app = typer.Typer(help="Universe agent commands", no_args_is_help=True)
app.add_typer(universe_app, name="universe")


# -----------------------------------------------------------------------------
# version
# -----------------------------------------------------------------------------


@app.command()
def version() -> None:
    """Print package version, alembic head, latest schema_version row."""
    asyncio.run(_version_async())


async def _version_async() -> None:
    from importlib import metadata as importlib_metadata

    from sqlalchemy import text

    from backend.db.session import SessionLocal

    pkg_version = importlib_metadata.version("bharat-research-brain")

    async with SessionLocal() as session:
        alembic_row = (
            await session.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar()
        latest = (
            await session.execute(
                text(
                    "SELECT version_label, applied_at, chunk_reference "
                    "FROM schema_version "
                    "ORDER BY applied_at DESC, version_label DESC LIMIT 1"
                )
            )
        ).first()

    table = Table(title="bharat-research-brain version")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("package", pkg_version)
    table.add_row("alembic head", str(alembic_row or "<none>"))
    if latest is not None:
        table.add_row("schema_version label", latest[0])
        table.add_row("schema_version applied_at", str(latest[1]))
        table.add_row("schema_version chunk", str(latest[2]))
    else:
        table.add_row("schema_version", "<empty>")
    console.print(table)


# -----------------------------------------------------------------------------
# health
# -----------------------------------------------------------------------------


@app.command()
def health() -> None:
    """Probe the FastAPI /health endpoint."""
    asyncio.run(_health_async())


async def _health_async() -> None:
    import httpx

    log.info("cli.health.start")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get("http://localhost:8000/health")
            resp.raise_for_status()
        except Exception as exc:
            console.print(f"[red]health probe failed:[/red] {exc}")
            log.error("cli.health.failed", error=str(exc))
            raise typer.Exit(code=1) from exc
    payload = resp.json()
    table = Table(title="/health")
    table.add_column("service", style="bold")
    table.add_column("status")
    for k, v in payload.items():
        color = "green" if v in ("ok", "healthy") else "red"
        table.add_row(k, f"[{color}]{v}[/{color}]")
    console.print(table)
    log.info("cli.health.finish", overall=payload.get("overall"))


# -----------------------------------------------------------------------------
# universe build / show
# -----------------------------------------------------------------------------


@universe_app.command("build")
def universe_build(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Compute the reconciliation plan but do not write to DB or vault.",
    ),
) -> None:
    """Run the Universe Agent. With --dry-run, plan only — no writes."""
    asyncio.run(_universe_build_async(dry_run=dry_run))


async def _universe_build_async(*, dry_run: bool) -> None:
    from backend.agents.base import RunContext
    from backend.agents.universe import UniverseAgent

    log.info("cli.universe.build.start", dry_run=dry_run)
    agent = UniverseAgent()
    ctx = RunContext()

    if dry_run:
        plan = await agent.plan(ctx)
        _render_plan(plan)
        log.info("cli.universe.build.finish", dry_run=True, **plan.counts())
        return

    result = await agent.run(ctx)
    table = Table(title="Universe build — APPLIED")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("status", result.status)
    table.add_row("rows inserted", str(result.rows_inserted))
    table.add_row("rows updated", str(result.rows_updated))
    for k, v in result.metrics.items():
        table.add_row(f"metric:{k}", str(int(v)))
    console.print(table)
    for w in result.warnings:
        console.print(f"  [yellow]![/yellow] {w}")
    log.info("cli.universe.build.finish", dry_run=False, status=result.status)


def _render_plan(plan: object) -> None:
    """Render a UniversePlan to the console (dry-run, zero writes)."""
    from backend.agents.universe import UniversePlan

    assert isinstance(plan, UniversePlan)
    counts = plan.counts()

    table = Table(title="Universe build — DRY RUN (no writes)")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("effective_date", str(plan.effective_date))
    table.add_row("securities (master)", str(plan.securities_count))
    table.add_row(
        "fetched indices", f"{len(plan.fetched_indices)}: {', '.join(plan.fetched_indices)}"
    )
    table.add_row(
        "deferred indices",
        ", ".join(plan.deferred_indices) if plan.deferred_indices else "<none>",
    )
    table.add_row(
        "failed indices",
        ", ".join(f"{k}={v}" for k, v in plan.failed_indices.items())
        if plan.failed_indices
        else "<none>",
    )
    table.add_row("stocks to insert", str(counts["stocks_to_insert"]))
    table.add_row("stocks to update", str(counts["stocks_to_update"]))
    table.add_row("memberships to open", str(counts["memberships_to_open"]))
    table.add_row("memberships to close", str(counts["memberships_to_close"]))
    table.add_row("constituents missing master", str(len(plan.constituents_missing_master)))
    table.add_row("unmapped industries", str(len(plan.unmapped_sectors)))
    console.print(table)

    for w in plan.warnings:
        console.print(f"  [yellow]![/yellow] {w}")

    sample = list(plan.stocks_to_insert.values())[:10]
    if sample:
        sample_table = Table(title="Sample stocks to insert (first 10)")
        sample_table.add_column("isin")
        sample_table.add_column("nse_symbol")
        sample_table.add_column("sector")
        sample_table.add_column("company")
        for ds in sample:
            sample_table.add_row(
                ds.isin, ds.nse_symbol or "—", ds.sector or "—", ds.company_name
            )
        console.print(sample_table)

    console.print(
        f"[dim]has_changes={plan.has_changes()} — DRY RUN, nothing was written.[/dim]"
    )


@universe_app.command("show")
def universe_show(
    limit: int = typer.Option(20, "--limit", help="Max rows to display."),
) -> None:
    """Show current universe state from Postgres (read-only)."""
    asyncio.run(_universe_show_async(limit=limit))


async def _universe_show_async(*, limit: int) -> None:
    from sqlalchemy import func, select

    from backend.db.models import IndexConstituent, Stock
    from backend.db.session import SessionLocal

    log.info("cli.universe.show.start", limit=limit)
    async with SessionLocal() as session:
        total_stocks = (
            await session.execute(select(func.count()).select_from(Stock))
        ).scalar_one()
        active_stocks = (
            await session.execute(
                select(func.count())
                .select_from(Stock)
                .where(Stock.delisted_on.is_(None))
            )
        ).scalar_one()
        active_members = (
            await session.execute(
                select(func.count())
                .select_from(IndexConstituent)
                .where(IndexConstituent.effective_to.is_(None))
            )
        ).scalar_one()
        per_index = (
            await session.execute(
                select(IndexConstituent.index_code, func.count())
                .where(IndexConstituent.effective_to.is_(None))
                .group_by(IndexConstituent.index_code)
                .order_by(func.count().desc())
            )
        ).all()
        sample = (
            (
                await session.execute(
                    select(Stock)
                    .where(Stock.delisted_on.is_(None))
                    .order_by(Stock.nse_symbol)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    summary = Table(title="Universe — current state")
    summary.add_column("field", style="bold")
    summary.add_column("value")
    summary.add_row("stocks (total)", str(total_stocks))
    summary.add_row("stocks (active)", str(active_stocks))
    summary.add_row("active memberships", str(active_members))
    console.print(summary)

    if per_index:
        idx_table = Table(title="Active memberships per index")
        idx_table.add_column("index_code")
        idx_table.add_column("members", justify="right")
        for code, count in per_index:
            idx_table.add_row(code, str(count))
        console.print(idx_table)

    if sample:
        stock_table = Table(title=f"Stocks (first {limit} by symbol)")
        stock_table.add_column("isin")
        stock_table.add_column("nse_symbol")
        stock_table.add_column("sector")
        stock_table.add_column("company")
        for s in sample:
            stock_table.add_row(
                s.isin, s.nse_symbol or "—", s.sector or "—", s.company_name
            )
        console.print(stock_table)

    log.info("cli.universe.show.finish", total=total_stocks, active=active_stocks)


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()
