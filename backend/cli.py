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
prices_app = typer.Typer(help="Price agent commands", no_args_is_help=True)
app.add_typer(prices_app, name="prices")
quality_app = typer.Typer(help="Data quality agent commands", no_args_is_help=True)
app.add_typer(quality_app, name="quality")
events_app = typer.Typer(help="Corporate events agent commands", no_args_is_help=True)
app.add_typer(events_app, name="events")
vault_app = typer.Typer(help="Vault writer commands", no_args_is_help=True)
app.add_typer(vault_app, name="vault")
live_app = typer.Typer(help="Live price feed commands", no_args_is_help=True)
app.add_typer(live_app, name="live")


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
    sector: str | None = typer.Option(
        None, "--sector", help="Filter active stocks by canonical sector."
    ),
    index: str | None = typer.Option(
        None, "--index", help="List active members of an index_code."
    ),
) -> None:
    """Show current universe state from Postgres (read-only).

    With --index, lists active members of that index. With --sector, lists
    active stocks in that canonical sector. Otherwise shows the summary,
    per-index counts, and a stock sample.
    """
    asyncio.run(_universe_show_async(limit=limit, sector=sector, index=index))


async def _universe_show_async(
    *, limit: int, sector: str | None, index: str | None
) -> None:
    from sqlalchemy import func, select

    from backend.db.models import IndexConstituent, Stock
    from backend.db.session import SessionLocal

    log.info("cli.universe.show.start", limit=limit, sector=sector, index=index)
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

        per_index = []
        sample: list[Stock] = []
        filtered_count: int | None = None
        if index is not None:
            filtered_count = (
                await session.execute(
                    select(func.count())
                    .select_from(IndexConstituent)
                    .where(
                        IndexConstituent.index_code == index,
                        IndexConstituent.effective_to.is_(None),
                    )
                )
            ).scalar_one()
            sample = list(
                (
                    await session.execute(
                        select(Stock)
                        .join(IndexConstituent, IndexConstituent.isin == Stock.isin)
                        .where(
                            IndexConstituent.index_code == index,
                            IndexConstituent.effective_to.is_(None),
                        )
                        .order_by(Stock.nse_symbol)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
        elif sector is not None:
            filtered_count = (
                await session.execute(
                    select(func.count())
                    .select_from(Stock)
                    .where(Stock.delisted_on.is_(None), Stock.sector == sector)
                )
            ).scalar_one()
            sample = list(
                (
                    await session.execute(
                        select(Stock)
                        .where(Stock.delisted_on.is_(None), Stock.sector == sector)
                        .order_by(Stock.nse_symbol)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
        else:
            per_index = (
                await session.execute(
                    select(IndexConstituent.index_code, func.count())
                    .where(IndexConstituent.effective_to.is_(None))
                    .group_by(IndexConstituent.index_code)
                    .order_by(func.count().desc())
                )
            ).all()
            sample = list(
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
    if index is not None:
        summary.add_row(f"members of {index}", str(filtered_count))
    elif sector is not None:
        summary.add_row(f"active stocks in {sector}", str(filtered_count))
    console.print(summary)

    if per_index:
        idx_table = Table(title="Active memberships per index")
        idx_table.add_column("index_code")
        idx_table.add_column("members", justify="right")
        for code, count in per_index:
            idx_table.add_row(code, str(count))
        console.print(idx_table)

    if sample:
        if index is not None:
            title = f"Members of {index} (first {limit} by symbol)"
        elif sector is not None:
            title = f"{sector} stocks (first {limit} by symbol)"
        else:
            title = f"Stocks (first {limit} by symbol)"
        stock_table = Table(title=title)
        stock_table.add_column("isin")
        stock_table.add_column("nse_symbol")
        stock_table.add_column("sector")
        stock_table.add_column("company")
        for s in sample:
            stock_table.add_row(
                s.isin, s.nse_symbol or "—", s.sector or "—", s.company_name
            )
        console.print(stock_table)
    elif index is not None or sector is not None:
        console.print("[yellow]no matching active rows[/yellow]")

    log.info("cli.universe.show.finish", total=total_stocks, active=active_stocks)


# -----------------------------------------------------------------------------
# prices backfill / fetch-today / show
# -----------------------------------------------------------------------------


@prices_app.command("backfill")
def prices_backfill(
    years: int = typer.Option(5, "--years", help="Look back this many years."),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date YYYY-MM-DD (overrides --years)."
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date YYYY-MM-DD (defaults to today IST)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Download + parse, print plan, write nothing."
    ),
) -> None:
    """Backfill prices_eod from NSE bhavcopies for missing trading days."""
    asyncio.run(
        _prices_backfill_async(
            years=years, from_date=from_date, to_date=to_date, dry_run=dry_run
        )
    )


async def _prices_backfill_async(
    *, years: int, from_date: str | None, to_date: str | None, dry_run: bool
) -> None:
    from datetime import date, timedelta

    from backend.agents.base import RunContext
    from backend.agents.price import PriceAgent, PriceRequest
    from backend.db.repositories._helpers import today_ist

    end = date.fromisoformat(to_date) if to_date else today_ist()
    start = date.fromisoformat(from_date) if from_date else end - timedelta(days=years * 365)
    log.info("cli.prices.backfill.start", start=str(start), end=str(end), dry_run=dry_run)

    if dry_run:
        result = await PriceAgent().backfill(start=start, end=end, dry_run=True)
        _render_backfill_plan(start, end, result)
        return

    agent = PriceAgent(request=PriceRequest(mode="backfill", start=start, end=end))
    agent_result = await agent.run(RunContext())
    table = Table(title="Prices backfill — APPLIED")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("status", agent_result.status)
    table.add_row("rows inserted", str(agent_result.rows_inserted))
    for k, v in agent_result.metrics.items():
        table.add_row(f"metric:{k}", str(int(v)))
    console.print(table)
    console.print(f"[dim]{len(agent_result.warnings)} warnings logged to data_quality_log[/dim]")
    log.info("cli.prices.backfill.finish", status=agent_result.status)


def _render_backfill_plan(start: object, end: object, result: object) -> None:
    from backend.agents.price import PriceResult

    assert isinstance(result, PriceResult)
    table = Table(title="Prices backfill — DRY RUN (no writes)")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("date range", f"{start} .. {end}")
    table.add_row("open trading days (calendar)", str(result.open_days))
    table.add_row("already present in prices_eod", str(result.present_days))
    table.add_row("would download (missing)", str(result.dates_attempted))
    table.add_row("downloaded OK", str(result.dates_succeeded))
    table.add_row("download failed", str(result.dates_failed))
    table.add_row("rows ready to insert", str(result.rows_ready))
    table.add_row("rows skipped (series/universe)", str(result.rows_skipped))
    table.add_row("rows warned (quality)", str(result.rows_warned))
    console.print(table)

    sample = sorted(result.missing)[:15]
    if sample:
        console.print("[bold]Sample dates to fetch (first 15):[/bold]")
        console.print("  " + ", ".join(str(d) for d in sample))
    if result.failed_dates:
        console.print(
            "[yellow]failed dates (first 15):[/yellow] "
            + ", ".join(str(d) for d in sorted(result.failed_dates)[:15])
        )
    console.print("[dim]DRY RUN — nothing was written to prices_eod.[/dim]")


@prices_app.command("fetch-today")
def prices_fetch_today(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Download + parse, write nothing."
    ),
) -> None:
    """Fetch today's bhavcopy and insert new rows (skips non-trading days)."""
    asyncio.run(_prices_fetch_today_async(dry_run=dry_run))


async def _prices_fetch_today_async(*, dry_run: bool) -> None:
    from backend.agents.base import RunContext
    from backend.agents.price import PriceAgent, PriceRequest

    log.info("cli.prices.fetch_today.start", dry_run=dry_run)
    if dry_run:
        result = await PriceAgent().fetch_today(dry_run=True)
        if result.note:
            console.print(f"[yellow]{result.note}[/yellow]")
        table = Table(title="Prices fetch-today — DRY RUN")
        table.add_column("field", style="bold")
        table.add_column("value")
        for k, v in result.counts().items():
            table.add_row(k, str(v))
        console.print(table)
        return

    agent = PriceAgent(request=PriceRequest(mode="today"))
    agent_result = await agent.run(RunContext())
    console.print(
        f"fetch-today: status={agent_result.status}, "
        f"rows inserted={agent_result.rows_inserted}"
    )
    log.info("cli.prices.fetch_today.finish", status=agent_result.status)


@prices_app.command("show")
def prices_show(
    isin: str | None = typer.Option(None, "--isin", help="ISIN to display."),
    symbol: str | None = typer.Option(None, "--symbol", help="NSE symbol to display."),
    limit: int = typer.Option(30, "--limit", help="Most recent N rows."),
) -> None:
    """Show the most recent EOD rows for one stock (by --isin or --symbol)."""
    if not isin and not symbol:
        console.print("[red]provide --isin or --symbol[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_prices_show_async(isin=isin, symbol=symbol, limit=limit))


async def _prices_show_async(
    *, isin: str | None, symbol: str | None, limit: int
) -> None:
    from sqlalchemy import select

    from backend.db.models import PriceEod, Stock
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        if isin is None and symbol is not None:
            isin = (
                await session.execute(
                    select(Stock.isin).where(Stock.nse_symbol == symbol)
                )
            ).scalar_one_or_none()
            if isin is None:
                console.print(f"[red]no stock with nse_symbol={symbol!r}[/red]")
                raise typer.Exit(code=1)

        label = (
            await session.execute(
                select(Stock.nse_symbol, Stock.company_name).where(Stock.isin == isin)
            )
        ).first()
        rows = (
            (
                await session.execute(
                    select(PriceEod)
                    .where(PriceEod.isin == isin)
                    .order_by(PriceEod.trade_date.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    heading = f"{isin}"
    if label is not None:
        heading = f"{label[0]} ({isin}) — {label[1]}"
    table = Table(title=f"Prices (most recent {limit}) — {heading}")
    for col in ("date", "open", "high", "low", "close", "volume", "delivery_pct"):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r.trade_date),
            _fmt(r.open),
            _fmt(r.high),
            _fmt(r.low),
            _fmt(r.close),
            str(r.volume if r.volume is not None else "—"),
            _fmt(r.delivery_pct),
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no price rows for this stock yet[/yellow]")


def _fmt(value: object) -> str:
    return "—" if value is None else str(value)


# -----------------------------------------------------------------------------
# quality run / show
# -----------------------------------------------------------------------------


@quality_app.command("run")
def quality_run(
    fix: bool = typer.Option(
        False, "--fix", help="Re-fetch bhavcopies for PRICE_GAP dates, then persist."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Run checks and print summary; write nothing."
    ),
) -> None:
    """Run the Data Quality Agent over prices_eod + stocks."""
    asyncio.run(_quality_run_async(fix=fix, dry_run=dry_run))


async def _quality_run_async(*, fix: bool, dry_run: bool) -> None:
    from backend.agents.base import RunContext
    from backend.agents.data_quality import DataQualityAgent
    from backend.agents.price import PriceAgent, PriceRequest

    log.info("cli.quality.run.start", fix=fix, dry_run=dry_run)

    if fix and not dry_run:
        # Detect (no write) → re-fetch gap span → persist final findings.
        report = await DataQualityAgent().run_checks(dry_run=True)
        firsts = [
            f.context["first_gap"]
            for f in report.findings
            if f.code == "PRICE_GAP" and f.context.get("first_gap")
        ]
        lasts = [
            f.context["last_gap"]
            for f in report.findings
            if f.code == "PRICE_GAP" and f.context.get("last_gap")
        ]
        if firsts:
            from datetime import date as _date

            start = _date.fromisoformat(min(firsts))
            end = _date.fromisoformat(max(lasts))
            console.print(
                f"[bold]--fix:[/bold] re-fetching bhavcopies for gap span "
                f"{start} .. {end}"
            )
            price_res = await PriceAgent(
                request=PriceRequest(mode="backfill", start=start, end=end)
            ).run(RunContext())
            console.print(
                f"  re-fetch: {price_res.rows_inserted} new price rows inserted"
            )
        else:
            console.print("[dim]--fix: no PRICE_GAP findings to re-fetch[/dim]")
        result = await DataQualityAgent().run(RunContext())
        _render_quality_result(result, persisted=True)
        return

    if dry_run:
        report = await DataQualityAgent().run_checks(dry_run=True)
        _render_quality_report(report)
        return

    result = await DataQualityAgent().run(RunContext())
    _render_quality_result(result, persisted=True)


def _render_quality_report(report: object) -> None:
    from backend.agents.data_quality import QualityReport

    assert isinstance(report, QualityReport)
    table = Table(title="Data quality — DRY RUN (no writes)")
    table.add_column("code", style="bold")
    table.add_column("findings", justify="right")
    for code, n in sorted(report.by_code().items()):
        table.add_row(code, str(n))
    table.add_row("[bold]TOTAL[/bold]", str(len(report.findings)))
    console.print(table)
    sev = report.by_severity()
    console.print(
        f"severity: [red]error={sev.get('error', 0)}[/red] "
        f"[yellow]warn={sev.get('warn', 0)}[/yellow]"
    )
    for f in report.findings[:10]:
        console.print(f"  [{ 'red' if f.severity=='error' else 'yellow'}]{f.code}[/] "
                      f"{f.isin}: {f.message}")
    console.print("[dim]DRY RUN — nothing written to data_quality_log.[/dim]")


def _render_quality_result(result: object, *, persisted: bool) -> None:
    from backend.agents.base import AgentResult

    assert isinstance(result, AgentResult)
    table = Table(title="Data quality — APPLIED")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("status", result.status)
    table.add_row("findings written", str(result.rows_inserted))
    for k, v in sorted(result.metrics.items()):
        table.add_row(f"code:{k}", str(int(v)))
    console.print(table)


@quality_app.command("show")
def quality_show(
    severity: str | None = typer.Option(
        None, "--severity", help="Filter: warn | error."
    ),
    limit: int = typer.Option(50, "--limit", help="Most recent N findings."),
) -> None:
    """Show recent data_quality_log findings."""
    asyncio.run(_quality_show_async(severity=severity, limit=limit))


async def _quality_show_async(*, severity: str | None, limit: int) -> None:
    from backend.db.repositories import data_quality as dq_repo
    from backend.db.session import SessionLocal

    if severity is not None and severity not in ("warn", "error"):
        console.print("[red]--severity must be 'warn' or 'error'[/red]")
        raise typer.Exit(code=1)

    async with SessionLocal() as session:
        rows = await dq_repo.fetch_findings(session, severity=severity, limit=limit)

    table = Table(title=f"data_quality_log (most recent {limit})")
    table.add_column("detected_at")
    table.add_column("severity")
    table.add_column("code")
    table.add_column("isin")
    table.add_column("message")
    for r in rows:
        color = "red" if r.severity == "error" else "yellow"
        table.add_row(
            r.detected_at.strftime("%Y-%m-%d %H:%M"),
            f"[{color}]{r.severity}[/{color}]",
            r.code,
            r.isin or "—",
            r.message,
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no findings[/yellow]")


# -----------------------------------------------------------------------------
# events backfill / show
# -----------------------------------------------------------------------------


@events_app.command("backfill")
def events_backfill(
    years: int = typer.Option(5, "--years", help="Look back this many years."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Fetch + map, print summary, write nothing."
    ),
) -> None:
    """Backfill corporate_actions (splits + dividends) from yfinance."""
    asyncio.run(_events_backfill_async(years=years, dry_run=dry_run))


async def _events_backfill_async(*, years: int, dry_run: bool) -> None:
    from backend.agents.base import RunContext
    from backend.agents.corporate_events import CorporateEventsAgent

    log.info("cli.events.backfill.start", years=years, dry_run=dry_run)
    if dry_run:
        result = await CorporateEventsAgent().backfill(years=years, dry_run=True)
        table = Table(title="Corporate events backfill — DRY RUN (no writes)")
        table.add_column("field", style="bold")
        table.add_column("value")
        table.add_row("stocks attempted", str(result.stocks_attempted))
        table.add_row("stocks succeeded", str(result.stocks_succeeded))
        table.add_row("stocks failed", str(result.stocks_failed))
        table.add_row("splits found", str(result.splits))
        table.add_row("dividends found", str(result.dividends))
        table.add_row("rows ready to insert", str(result.rows_ready))
        console.print(table)
        console.print("[dim]DRY RUN — nothing written to corporate_actions.[/dim]")
        return

    agent_result = await CorporateEventsAgent().run(RunContext())
    table = Table(title="Corporate events backfill — APPLIED")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("status", agent_result.status)
    table.add_row("rows inserted", str(agent_result.rows_inserted))
    for k, v in sorted(agent_result.metrics.items()):
        table.add_row(f"metric:{k}", str(int(v)))
    console.print(table)
    log.info("cli.events.backfill.finish", status=agent_result.status)


@events_app.command("show")
def events_show(
    isin: str | None = typer.Option(None, "--isin", help="Filter by ISIN."),
    symbol: str | None = typer.Option(None, "--symbol", help="Filter by NSE symbol."),
    action_type: str | None = typer.Option(
        None, "--type", help="Filter by action_type (split | dividend | ...)."
    ),
    limit: int = typer.Option(30, "--limit", help="Most recent N events."),
) -> None:
    """Show recent corporate_actions rows."""
    asyncio.run(
        _events_show_async(
            isin=isin, symbol=symbol, action_type=action_type, limit=limit
        )
    )


async def _events_show_async(
    *, isin: str | None, symbol: str | None, action_type: str | None, limit: int
) -> None:
    from sqlalchemy import select

    from backend.db.models import Stock
    from backend.db.repositories import corporate_actions as ca_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        if isin is None and symbol is not None:
            isin = (
                await session.execute(
                    select(Stock.isin).where(Stock.nse_symbol == symbol)
                )
            ).scalar_one_or_none()
            if isin is None:
                console.print(f"[red]no stock with nse_symbol={symbol!r}[/red]")
                raise typer.Exit(code=1)
        rows = await ca_repo.fetch_actions(
            session, isin=isin, action_type=action_type, limit=limit
        )

    table = Table(title=f"corporate_actions (most recent {limit})")
    table.add_column("ex_date")
    table.add_column("isin")
    table.add_column("type")
    table.add_column("ratio / amount")
    table.add_column("description")
    for r in rows:
        if r.action_type == "dividend":
            detail = f"Rs {r.amount_inr}/sh"
        elif r.ratio_numerator is not None:
            detail = f"{r.ratio_numerator}:{r.ratio_denominator}"
        else:
            detail = "—"
        table.add_row(
            str(r.ex_date), r.isin, r.action_type, detail, r.description or "—"
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no corporate actions found[/yellow]")


# -----------------------------------------------------------------------------
# vault write
# -----------------------------------------------------------------------------


@vault_app.command("write")
def vault_write(
    limit: int | None = typer.Option(None, "--limit", help="First N stocks only."),
    symbol: str | None = typer.Option(None, "--symbol", help="Write just one stock."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print one sample note to stdout; write nothing."
    ),
    emit: bool = typer.Option(
        False,
        "--emit",
        help="Emit NDJSON {symbol, filename, note} for Claude Code to write via MCP.",
    ),
    out_file: str | None = typer.Option(
        None, "--out-file", help="With --emit, write NDJSON to this path (clean UTF-8)."
    ),
    out: str | None = typer.Option(
        None,
        "--out",
        help="Write each note as a .md into this directory (use with a -v vault mount).",
    ),
) -> None:
    """Render per-stock vault notes from the DB.

    The container cannot reach the host vault path, so actual file writes are
    performed by Claude Code via the filesystem MCP using --emit output.
    --dry-run prints one sample note; neither flag prints guidance.
    """
    asyncio.run(
        _vault_write_async(
            limit=limit,
            symbol=symbol,
            dry_run=dry_run,
            emit=emit,
            out_file=out_file,
            out=out,
        )
    )


def _write_notes_to_dir(notes: list[object], out_dir: str) -> int:
    """Sync writer: render each note, preserve post-marker content, write file."""
    from pathlib import Path

    from backend.agents.vault_writer import NoteData, note_filename, render_note

    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    written = 0
    for nd in notes:
        assert isinstance(nd, NoteData)
        fp = base / note_filename(nd.symbol)
        existing = fp.read_text(encoding="utf-8") if fp.exists() else None
        fp.write_text(render_note(nd, existing), encoding="utf-8")
        written += 1
        if written % 50 == 0:
            print(f"Written {written}/{len(notes)}")  # noqa: T201
    return written


async def _vault_write_async(
    *,
    limit: int | None,
    symbol: str | None,
    dry_run: bool,
    emit: bool,
    out_file: str | None,
    out: str | None,
) -> None:
    import json
    import sys

    from backend.agents.vault_writer import assemble_notes, note_filename, render_note
    from backend.db.session import SessionLocal

    log.info("cli.vault.write.start", limit=limit, symbol=symbol, dry_run=dry_run, emit=emit)
    async with SessionLocal() as session:
        notes = await assemble_notes(
            session, symbol=symbol, limit=(1 if dry_run and not symbol else limit)
        )

    if not notes:
        console.print("[yellow]no matching stocks[/yellow]")
        raise typer.Exit(code=1)

    if dry_run:
        sample = render_note(notes[0])
        console.print(
            f"[dim]--- sample note for {notes[0].symbol} "
            f"({len(notes)} would be rendered) — DRY RUN, nothing written ---[/dim]"
        )
        sys.stdout.write(sample + "\n")
        return

    if emit:
        lines = [
            json.dumps(
                {
                    "symbol": nd.symbol,
                    "filename": note_filename(nd.symbol),
                    "note": render_note(nd),
                },
                ensure_ascii=False,
            )
            for nd in notes
        ]
        if out_file is not None:
            from pathlib import Path

            await asyncio.to_thread(
                Path(out_file).write_text, "\n".join(lines) + "\n", encoding="utf-8"
            )
        else:
            for line in lines:
                sys.stdout.write(line + "\n")
        log.info("cli.vault.write.emit", count=len(notes), out_file=out_file)
        return

    if out is not None:
        written = await asyncio.to_thread(_write_notes_to_dir, list(notes), out)
        console.print(f"[green]Written {written}/{len(notes)}[/green] notes to {out}")
        log.info("cli.vault.write.out", count=written, out=out)
        return

    console.print(
        f"[yellow]{len(notes)} notes ready.[/yellow] The backend container cannot "
        "write to the host vault. Use [bold]--emit[/bold] (Claude Code writes via "
        "the filesystem MCP) or [bold]--dry-run[/bold] for a sample."
    )


# -----------------------------------------------------------------------------
# prices adjust
# -----------------------------------------------------------------------------


@prices_app.command("adjust")
def prices_adjust(
    isin: str | None = typer.Option(None, "--isin", help="Adjust one stock."),
    all_: bool = typer.Option(False, "--all", help="Adjust every active stock."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compute + print sample; write nothing."
    ),
) -> None:
    """Compute back-adjusted prices into prices_eod_adjusted."""
    if not isin and not all_:
        console.print("[red]provide --isin ISIN or --all[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_prices_adjust_async(isin=isin, all_=all_, dry_run=dry_run))


async def _prices_adjust_async(
    *, isin: str | None, all_: bool, dry_run: bool
) -> None:
    from backend.agents.price_adjust import AdjustedPriceAgent

    log.info("cli.prices.adjust.start", isin=isin, all=all_, dry_run=dry_run)
    agent = AdjustedPriceAgent()

    if all_:
        result = await agent.adjust_all(dry_run=dry_run)
        table = Table(
            title="Prices adjust --all" + (" — DRY RUN" if dry_run else " — APPLIED")
        )
        table.add_column("field", style="bold")
        table.add_column("value")
        table.add_row("stocks processed", str(result.stocks_processed))
        table.add_row("raw bars seen", str(result.bars))
        table.add_row("actions applied", str(result.actions))
        table.add_row("rows upserted", str(result.rows_upserted))
        console.print(table)
        if dry_run:
            console.print("[dim]DRY RUN — nothing written.[/dim]")
        return

    assert isin is not None
    result = await agent.adjust_isin(isin, dry_run=dry_run)
    console.print(
        f"[bold]{isin}[/bold]: {result.bars} raw bars, {result.actions} actions, "
        f"{result.rows_upserted} rows upserted"
        + (" (DRY RUN)" if dry_run else "")
    )
    sample = Table(title="adj_factor boundaries (one row per change)")
    sample.add_column("trade_date")
    sample.add_column("adj_close", justify="right")
    sample.add_column("adj_factor (multiplier)", justify="right")
    for d, adj_close, factor in result.sample:
        sample.add_row(str(d), str(adj_close) if adj_close is not None else "—", str(factor))
    console.print(sample)
    if dry_run:
        console.print("[dim]DRY RUN — nothing written to prices_eod_adjusted.[/dim]")
    log.info("cli.prices.adjust.finish", isin=isin, upserted=result.rows_upserted)


# -----------------------------------------------------------------------------
# live start / status / stop
# -----------------------------------------------------------------------------


@live_app.command("start")
def live_start(
    paper: bool = typer.Option(
        False, "--paper", help="Force DEMO mode (synthetic ticks; no broker)."
    ),
    duration: float = typer.Option(
        0.0, "--duration", help="Run for N seconds then stop (0 = until stopped)."
    ),
) -> None:
    """Start the live price feed → Redis."""
    asyncio.run(_live_start_async(paper=paper, duration=duration))


async def _live_start_async(*, paper: bool, duration: float) -> None:
    from backend.services.live_feed import LiveFeedService

    mode = "demo" if paper else None
    svc = LiveFeedService(mode=mode)
    log.info("cli.live.start", mode=svc.mode, paper=paper, duration=duration)
    await svc.connect()
    console.print(
        f"[green]live feed started[/green] mode={svc.mode} "
        f"symbols={svc.symbol_count} ttl=300s"
    )
    try:
        rounds = await svc.stream(interval=2.0, duration=duration)
        console.print(f"[dim]streamed {rounds} round(s); stopped.[/dim]")
    except KeyboardInterrupt:
        console.print("[yellow]interrupted[/yellow]")
    finally:
        await svc.disconnect()
    log.info("cli.live.start.finish")


@live_app.command("status")
def live_status() -> None:
    """Show live-feed status from Redis."""
    asyncio.run(_live_status_async())


async def _live_status_async() -> None:
    from backend.services.live_feed import LiveFeedService

    st = await LiveFeedService().status()
    meta = st["meta"]
    table = Table(title="Live feed status")
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("mode", str(meta["mode"]) if meta else "—")
    table.add_row("started_at", str(meta["started_at"]) if meta else "—")
    table.add_row("symbol_count (meta)", str(meta["symbol_count"]) if meta else "—")
    table.add_row("live keys in Redis", str(st["live_count"]))
    console.print(table)

    if st["samples"]:
        sample = Table(title="Sample live ticks (first 5)")
        sample.add_column("key")
        sample.add_column("ltp", justify="right")
        sample.add_column("timestamp")
        for key, ltp, ts in st["samples"]:
            sample.add_row(key, str(ltp), str(ts))
        console.print(sample)
    else:
        console.print("[yellow]no live ticks in Redis (feed not running?)[/yellow]")


@live_app.command("stop")
def live_stop() -> None:
    """Signal a running live feed to shut down gracefully."""
    asyncio.run(_live_stop_async())


async def _live_stop_async() -> None:
    from redis.asyncio import Redis

    from backend.config import settings
    from backend.services.live_feed import STOP_KEY

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.set(STOP_KEY, "1")
    finally:
        await client.aclose()
    console.print(f"[green]stop signal sent[/green] ({STOP_KEY}=1)")
    log.info("cli.live.stop")


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()
