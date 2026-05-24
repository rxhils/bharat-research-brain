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
# universe build / show (stubs until commit 13)
# -----------------------------------------------------------------------------


@universe_app.command("build")
def universe_build(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Compute diff but do not write to DB or vault.",
    ),
) -> None:
    """Run the Universe Agent (full implementation lands in commit 13)."""
    log.info("cli.universe.build.start", dry_run=dry_run)
    console.print(
        "[yellow]universe build:[/yellow] not implemented yet "
        "(stubbed by commit 10 of Chunk 1.2; real agent ships in commit 13)"
    )
    if dry_run:
        console.print("  [dim]--dry-run mode requested[/dim]")
    log.info("cli.universe.build.finish", dry_run=dry_run)


@universe_app.command("show")
def universe_show(
    limit: int = typer.Option(20, "--limit", help="Max rows to display."),
) -> None:
    """Show current universe state from Postgres (commit 13)."""
    log.info("cli.universe.show.start", limit=limit)
    console.print(
        "[yellow]universe show:[/yellow] not implemented yet "
        "(stubbed by commit 10 of Chunk 1.2)"
    )
    log.info("cli.universe.show.finish")


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()
