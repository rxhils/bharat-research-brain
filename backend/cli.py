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
from datetime import date

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
intraday_app = typer.Typer(help="Intraday signal commands", no_args_is_help=True)
app.add_typer(intraday_app, name="intraday")
technical_app = typer.Typer(help="Technical agent commands", no_args_is_help=True)
app.add_typer(technical_app, name="technical")
news_app = typer.Typer(help="News agent commands", no_args_is_help=True)
app.add_typer(news_app, name="news")
sentiment_app = typer.Typer(help="Sentiment agent commands", no_args_is_help=True)
app.add_typer(sentiment_app, name="sentiment")
fundamentals_app = typer.Typer(
    help="Fundamentals agent commands", no_args_is_help=True
)
app.add_typer(fundamentals_app, name="fundamentals")
sector_app = typer.Typer(help="Sector agent commands", no_args_is_help=True)
app.add_typer(sector_app, name="sector")
fii_app = typer.Typer(help="FII/DII (FPI) flow agent commands", no_args_is_help=True)
app.add_typer(fii_app, name="fii")
macro_app = typer.Typer(help="Macro agent commands", no_args_is_help=True)
app.add_typer(macro_app, name="macro")
risk_app = typer.Typer(help="Risk agent commands", no_args_is_help=True)
app.add_typer(risk_app, name="risk")
ranking_app = typer.Typer(help="Ranking agent commands", no_args_is_help=True)
app.add_typer(ranking_app, name="ranking")
report_app = typer.Typer(help="Report agent commands", no_args_is_help=True)
app.add_typer(report_app, name="report")
auditor_app = typer.Typer(help="Meta-Auditor commands", no_args_is_help=True)
app.add_typer(auditor_app, name="auditor")


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
    from backend.services.intraday_signals import IntradaySignalService
    from backend.services.live_feed import LiveFeedService

    mode = "demo" if paper else None
    svc = LiveFeedService(mode=mode, signal_service=IntradaySignalService())
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
# intraday status
# -----------------------------------------------------------------------------


@intraday_app.command("status")
def intraday_status(
    isin: str | None = typer.Option(None, "--isin", help="Show one stock."),
    limit: int = typer.Option(10, "--limit", help="Top N by |volume z-score|."),
) -> None:
    """Show current intraday signals from Redis."""
    asyncio.run(_intraday_status_async(isin=isin, limit=limit))


async def _intraday_status_async(*, isin: str | None, limit: int) -> None:
    import json as _json

    from redis.asyncio import Redis

    from backend.config import settings
    from backend.services.intraday_signals import IntradaySignalService

    rows = await IntradaySignalService().status(isin=isin, limit=limit)
    if not rows:
        console.print(
            "[yellow]no intraday signals in Redis (live feed not running?)[/yellow]"
        )
        return

    client = Redis.from_url(settings.redis_url, decode_responses=True)
    table = Table(title="Intraday signals (by |volume z-score|)")
    table.add_column("symbol")
    table.add_column("ltp", justify="right")
    table.add_column("vwap_dist%", justify="right")
    table.add_column("vol_zscore", justify="right")
    table.add_column("momentum", justify="right")
    try:
        for sym, sig in rows:
            live = await client.get(f"live:{sym}")
            ltp = _json.loads(live)["ltp"] if live else None
            table.add_row(
                sym,
                f"{ltp:.2f}" if ltp is not None else "—",
                f"{sig['vwap_distance_pct']:.3f}",
                f"{sig['volume_zscore']:.2f}",
                f"{sig['momentum_5tick']:.4f}",
            )
    finally:
        await client.aclose()
    console.print(table)


# -----------------------------------------------------------------------------
# technical run / show
# -----------------------------------------------------------------------------


@technical_app.command("run")
def technical_run(
    isin: str | None = typer.Option(None, "--isin", help="Compute one stock."),
    all_: bool = typer.Option(False, "--all", help="Compute every active stock."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compute + print; write nothing."
    ),
) -> None:
    """Compute technical indicators into technical_signals."""
    if not isin and not all_:
        console.print("[red]provide --isin ISIN or --all[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_technical_run_async(isin=isin, all_=all_, dry_run=dry_run))


async def _technical_run_async(*, isin: str | None, all_: bool, dry_run: bool) -> None:
    from backend.agents.technical import TechnicalAgent

    log.info("cli.technical.run.start", isin=isin, all=all_, dry_run=dry_run)
    agent = TechnicalAgent()
    if all_:
        res = await agent.run_all(dry_run=dry_run)
        table = Table(
            title="Technical run --all" + (" — DRY RUN" if dry_run else " — APPLIED")
        )
        table.add_column("field", style="bold")
        table.add_column("value")
        table.add_row("stocks processed", str(res.stocks_processed))
        table.add_row("rows upserted", str(res.rows_upserted))
        table.add_row("skipped (no adj data)", str(res.skipped_no_data))
        console.print(table)
        return

    assert isin is not None
    row = await agent.run_isin(isin, dry_run=dry_run)
    if row is None:
        console.print(f"[yellow]no adjusted prices for {isin}[/yellow]")
        return
    console.print(
        f"[bold]{isin}[/bold] @ {row['computed_date']}: "
        f"rsi_14={row['rsi_14']} ema_200={row['ema_200']} "
        f"price_vs_ema200={row['price_vs_ema200']} ema_cross={row['ema_cross']}"
        + (" (DRY RUN)" if dry_run else "")
    )


@technical_app.command("show")
def technical_show(
    isin: str | None = typer.Option(None, "--isin", help="ISIN to display."),
    symbol: str | None = typer.Option(None, "--symbol", help="NSE symbol to display."),
) -> None:
    """Show recent technical_signals rows for one stock."""
    if not isin and not symbol:
        console.print("[red]provide --isin or --symbol[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_technical_show_async(isin=isin, symbol=symbol))


async def _technical_show_async(*, isin: str | None, symbol: str | None) -> None:
    from sqlalchemy import select

    from backend.db.models import Stock
    from backend.db.repositories import technical as tech_repo
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
        rows = await tech_repo.fetch_signals(session, isin=isin, limit=5)

    table = Table(title=f"technical_signals — {isin}")
    for col in (
        "date",
        "rsi_14",
        "ema_20",
        "ema_200",
        "price_vs_ema200",
        "ema_cross",
        "macd_hist",
    ):
        table.add_column(col)
    for r in rows:
        table.add_row(
            str(r.computed_date),
            str(r.rsi_14) if r.rsi_14 is not None else "—",
            str(r.ema_20) if r.ema_20 is not None else "—",
            str(r.ema_200) if r.ema_200 is not None else "—",
            r.price_vs_ema200 or "—",
            r.ema_cross or "—",
            str(r.macd_hist) if r.macd_hist is not None else "—",
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no technical signals for this stock yet[/yellow]")


# -----------------------------------------------------------------------------
# news fetch / show
# -----------------------------------------------------------------------------


_NEWS_SOURCES = (
    "rss",
    "newsapi",
    "marketaux",
    "nse-deals",
    "bse-announcements",
    "all",
)


@news_app.command("fetch")
def news_fetch(
    source: str = typer.Option(
        "rss",
        "--source",
        help="rss | newsapi | marketaux | nse-deals | bse-announcements | all.",
    ),
    bulk_file: str | None = typer.Option(
        None, "--bulk-file", help="Path to a downloaded NSE bulk-deal JSON file."
    ),
    block_file: str | None = typer.Option(
        None, "--block-file", help="Path to a downloaded NSE block-deal JSON file."
    ),
    bse_file: str | None = typer.Option(
        None, "--bse-file", help="Path to a downloaded BSE announcement JSON file."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Fetch + match, print sample, write nothing."
    ),
) -> None:
    """Fetch market news, dedup, match to ISINs, store in news_articles.

    nse-deals / bse-announcements ingest locally-downloaded published files
    (NSE/BSE website scraping is barred by CLAUDE.md §2 rule 5 / §12). Pass the
    relevant --bulk-file / --block-file / --bse-file; a missing file is non-fatal.
    """
    if source not in _NEWS_SOURCES:
        console.print(f"[red]--source must be one of {' | '.join(_NEWS_SOURCES)}[/red]")
        raise typer.Exit(code=1)
    asyncio.run(
        _news_fetch_async(
            source=source,
            dry_run=dry_run,
            bulk_file=bulk_file,
            block_file=block_file,
            bse_file=bse_file,
        )
    )


async def _news_fetch_async(
    *,
    source: str,
    dry_run: bool,
    bulk_file: str | None = None,
    block_file: str | None = None,
    bse_file: str | None = None,
) -> None:
    from backend.agents.news import NewsAgent

    log.info("cli.news.fetch.start", source=source, dry_run=dry_run)
    res = await NewsAgent().run(
        sources=(source,),
        dry_run=dry_run,
        nse_bulk_path=bulk_file,
        nse_block_path=block_file,
        bse_path=bse_file,
    )

    table = Table(
        title="News fetch" + (" — DRY RUN (no writes)" if dry_run else " — APPLIED")
    )
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("fetched", str(res.fetched))
    table.add_row("after dedup", str(res.deduped))
    table.add_row("matched to ISIN", str(res.matched))
    table.add_row("unmatched (market-wide)", str(res.unmatched))
    table.add_row("inserted", str(res.inserted))
    console.print(table)

    if res.sample:
        sample = Table(title="Sample (first 10)")
        sample.add_column("isin")
        sample.add_column("headline")
        for headline, isin in res.sample:
            sample.add_row(isin or "—", headline[:80])
        console.print(sample)
    if dry_run:
        console.print("[dim]DRY RUN — nothing written to news_articles.[/dim]")


@news_app.command("show")
def news_show(
    isin: str | None = typer.Option(None, "--isin", help="Filter by ISIN."),
    symbol: str | None = typer.Option(None, "--symbol", help="Filter by NSE symbol."),
    unmatched: bool = typer.Option(
        False, "--unmatched", help="Show market-wide (isin NULL) articles."
    ),
    limit: int = typer.Option(20, "--limit", help="Max rows."),
) -> None:
    """Show stored news articles."""
    asyncio.run(
        _news_show_async(isin=isin, symbol=symbol, unmatched=unmatched, limit=limit)
    )


async def _news_show_async(
    *, isin: str | None, symbol: str | None, unmatched: bool, limit: int
) -> None:
    from sqlalchemy import select

    from backend.db.models import Stock
    from backend.db.repositories import news as news_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        if not unmatched and isin is None and symbol is not None:
            isin = (
                await session.execute(
                    select(Stock.isin).where(Stock.nse_symbol == symbol)
                )
            ).scalar_one_or_none()
            if isin is None:
                console.print(f"[red]no stock with nse_symbol={symbol!r}[/red]")
                raise typer.Exit(code=1)
        rows = await news_repo.fetch(
            session, isin=isin, unmatched=unmatched, limit=limit
        )

    title = "Unmatched news" if unmatched else f"News — {isin or 'all'}"
    table = Table(title=title)
    table.add_column("published")
    table.add_column("isin")
    table.add_column("source")
    table.add_column("headline")
    for r in rows:
        table.add_row(
            r.published_at.strftime("%Y-%m-%d %H:%M") if r.published_at else "—",
            r.isin or "—",
            r.source_name,
            r.headline[:70],
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no articles[/yellow]")


# -----------------------------------------------------------------------------
# sentiment
# -----------------------------------------------------------------------------
@sentiment_app.command("run")
def sentiment_run(
    isin: str | None = typer.Option(
        None, "--isin", help="Only score articles for this ISIN."
    ),
    batch_size: int = typer.Option(32, "--batch-size", help="Articles per batch."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Score one batch, print samples, write nothing."
    ),
) -> None:
    """Score unscored news with FinBERT, write sentiment_label + sentiment_score."""
    asyncio.run(
        _sentiment_run_async(isin=isin, batch_size=batch_size, dry_run=dry_run)
    )


async def _sentiment_run_async(
    *, isin: str | None, batch_size: int, dry_run: bool
) -> None:
    from backend.agents.sentiment import SentimentAgent, _text_of, build_updates
    from backend.db.repositories import news as news_repo
    from backend.db.session import SessionLocal

    log.info("cli.sentiment.run.start", isin=isin, batch_size=batch_size, dry_run=dry_run)

    agent = SentimentAgent()

    if dry_run:
        # Score a single small sample so the operator can eyeball the mapping
        # before committing the (slow) full pass. Nothing is written.
        import asyncio as _asyncio

        async with SessionLocal() as session:
            rows = await news_repo.fetch_unscored(session, isin=isin, limit=5)
        if not rows:
            console.print("[yellow]no unscored articles[/yellow]")
            return
        articles = [(r.id, r.headline, r.summary) for r in rows]
        texts = [_text_of(h, s) for _id, h, s in articles]
        results = await _asyncio.to_thread(agent.finbert.score_batch, texts)
        updates = build_updates(articles, results)

        table = Table(title="Sentiment — DRY RUN (5 samples, no writes)")
        table.add_column("label", style="bold")
        table.add_column("score", justify="right")
        table.add_column("headline")
        for (_id, headline, _s), u in zip(articles, updates, strict=True):
            table.add_row(u["sentiment_label"], f"{u['sentiment_score']:+.4f}", headline[:70])
        console.print(table)
        console.print("[dim]DRY RUN — nothing written to news_articles.[/dim]")
        return

    res = await agent.run(batch_size=batch_size, isin=isin)
    table = Table(title="Sentiment run — APPLIED")
    table.add_column("field", style="bold")
    table.add_column("value", justify="right")
    table.add_row("scored", str(res["scored"]))
    table.add_row("updated", str(res["updated"]))
    table.add_row("bull", str(res["bull"]))
    table.add_row("bear", str(res["bear"]))
    table.add_row("neutral", str(res["neutral"]))
    console.print(table)


@sentiment_app.command("show")
def sentiment_show(
    isin: str | None = typer.Option(None, "--isin", help="Filter by ISIN."),
    symbol: str | None = typer.Option(None, "--symbol", help="Filter by NSE symbol."),
    limit: int = typer.Option(20, "--limit", help="Max rows."),
) -> None:
    """Show scored news articles (symbol, headline, label, score, published_at)."""
    asyncio.run(_sentiment_show_async(isin=isin, symbol=symbol, limit=limit))


async def _sentiment_show_async(
    *, isin: str | None, symbol: str | None, limit: int
) -> None:
    from sqlalchemy import select

    from backend.db.models import NewsArticle, Stock
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
        stmt = select(NewsArticle, Stock.nse_symbol).join(
            Stock, NewsArticle.isin == Stock.isin, isouter=True
        )
        if isin is not None:
            stmt = stmt.where(NewsArticle.isin == isin)
        stmt = stmt.where(NewsArticle.sentiment_label.is_not(None))
        stmt = stmt.order_by(NewsArticle.published_at.desc().nullslast()).limit(limit)
        rows = (await session.execute(stmt)).all()

    table = Table(title=f"Scored news — {isin or 'all'}")
    table.add_column("symbol")
    table.add_column("headline")
    table.add_column("label", style="bold")
    table.add_column("score", justify="right")
    table.add_column("published")
    for article, sym in rows:
        table.add_row(
            sym or "—",
            article.headline[:60],
            article.sentiment_label or "—",
            f"{float(article.sentiment_score):+.4f}"
            if article.sentiment_score is not None
            else "—",
            article.published_at.strftime("%Y-%m-%d %H:%M")
            if article.published_at
            else "—",
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no scored articles[/yellow]")


# -----------------------------------------------------------------------------
# fundamentals
# -----------------------------------------------------------------------------
@fundamentals_app.command("run")
def fundamentals_run(
    isin: str | None = typer.Option(None, "--isin", help="Fetch one ISIN only."),
    all_: bool = typer.Option(False, "--all", help="Fetch all active stocks."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Fetch + map, print sample, write nothing."
    ),
) -> None:
    """Fetch yfinance fundamentals, store, and classify mcap_category."""
    if not all_ and isin is None:
        console.print("[red]pass --isin ISIN or --all[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_fundamentals_run_async(isin=isin, dry_run=dry_run))


async def _fundamentals_run_async(*, isin: str | None, dry_run: bool) -> None:
    from backend.agents.fundamentals import FundamentalsAgent, mcap_to_category

    log.info("cli.fundamentals.run.start", isin=isin, dry_run=dry_run)
    res = await FundamentalsAgent().run_all(isin=isin, dry_run=dry_run)

    table = Table(
        title="Fundamentals run"
        + (" — DRY RUN (no writes)" if dry_run else " — APPLIED")
    )
    table.add_column("field", style="bold")
    table.add_column("value", justify="right")
    table.add_row("attempted", str(res.stocks_attempted))
    table.add_row("succeeded", str(res.stocks_succeeded))
    table.add_row("failed", str(res.stocks_failed))
    table.add_row("rows ready", str(res.rows_ready))
    if not dry_run:
        table.add_row("rows upserted", str(res.rows_upserted))
        table.add_row("mcap categories set", str(res.categories_updated))
    console.print(table)

    if dry_run:

        def _f(value: object) -> str:
            return f"{float(value):.4f}" if value is not None else "—"

        for row in res.samples:
            mcap_cr = (
                f"{row.market_cap / 1e7:,.0f} Cr" if row.market_cap is not None else "—"
            )
            detail = Table(title=f"Fundamentals (preview) — {row.isin}")
            detail.add_column("field", style="bold")
            detail.add_column("value", justify="right")
            detail.add_row("pe_ratio", _f(row.pe_ratio))
            detail.add_row("pb_ratio", _f(row.pb_ratio))
            detail.add_row("roe", _f(row.roe))
            detail.add_row("roce (ROA proxy)", _f(row.roce))
            detail.add_row("debt_to_equity", _f(row.debt_to_equity))
            detail.add_row("revenue_growth", _f(row.revenue_growth))
            detail.add_row("earnings_growth", _f(row.earnings_growth))
            detail.add_row("profit_margin", _f(row.profit_margin))
            detail.add_row("market_cap (INR)", str(row.market_cap or "—"))
            detail.add_row("market_cap (Cr)", mcap_cr)
            detail.add_row("→ mcap_category", mcap_to_category(row.market_cap) or "—")
            detail.add_row("dividend_yield", _f(row.dividend_yield))
            detail.add_row("52w_high", _f(row.fifty_two_week_high))
            detail.add_row("52w_low", _f(row.fifty_two_week_low))
            detail.add_row("avg_volume_30d", str(row.avg_volume_30d or "—"))
            detail.add_row("promoter_holding", _f(row.promoter_holding))
            console.print(detail)
        console.print("[dim]DRY RUN — nothing written to fundamental_signals.[/dim]")


@fundamentals_app.command("show")
def fundamentals_show(
    isin: str | None = typer.Option(None, "--isin", help="Filter by ISIN."),
    symbol: str | None = typer.Option(None, "--symbol", help="Filter by NSE symbol."),
) -> None:
    """Show the latest stored fundamentals for a stock."""
    asyncio.run(_fundamentals_show_async(isin=isin, symbol=symbol))


async def _fundamentals_show_async(*, isin: str | None, symbol: str | None) -> None:
    from sqlalchemy import select

    from backend.db.models import Stock
    from backend.db.repositories import fundamentals as fund_repo
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
        if isin is None:
            console.print("[red]pass --isin ISIN or --symbol SYMBOL[/red]")
            raise typer.Exit(code=1)
        row = await fund_repo.fetch_latest(session, isin=isin)
        stock = (
            await session.execute(
                select(Stock.nse_symbol, Stock.mcap_category).where(
                    Stock.isin == isin
                )
            )
        ).first()

    sym = stock[0] if stock else None
    mcap_category = stock[1] if stock else None

    if row is None:
        console.print(f"[yellow]no fundamentals for {isin}[/yellow]")
        return

    def _f(value: object) -> str:
        return f"{float(value):.4f}" if value is not None else "—"

    table = Table(title=f"Fundamentals — {sym or isin}")
    table.add_column("symbol")
    table.add_column("pe", justify="right")
    table.add_column("pb", justify="right")
    table.add_column("roe", justify="right")
    table.add_column("d/e", justify="right")
    table.add_column("rev_growth", justify="right")
    table.add_column("mcap_category")
    table.add_column("fetched_date")
    table.add_row(
        sym or "—",
        _f(row.pe_ratio),
        _f(row.pb_ratio),
        _f(row.roe),
        _f(row.debt_to_equity),
        _f(row.revenue_growth),
        mcap_category or "—",
        row.fetched_date.isoformat(),
    )
    console.print(table)


# -----------------------------------------------------------------------------
# sector
# -----------------------------------------------------------------------------
@sector_app.command("run")
def sector_run(
    sector: str | None = typer.Option(None, "--sector", help="Compute one sector."),
    all_: bool = typer.Option(False, "--all", help="Compute all sectors."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compute + print, write nothing."
    ),
) -> None:
    """Compute sector momentum signals from existing DB data (no external calls)."""
    if not all_ and sector is None:
        console.print("[red]pass --sector NAME or --all[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_sector_run_async(sector=sector, dry_run=dry_run))


def _sector_table(rows: list[object], title: str) -> Table:
    from backend.agents.sector import SectorRow

    def _f(value: object) -> str:
        return f"{float(value):.4f}" if value is not None else "—"

    table = Table(title=title)
    table.add_column("sector")
    table.add_column("signal", style="bold")
    table.add_column("avg_rsi", justify="right")
    table.add_column("pct>ema200", justify="right")
    table.add_column("mom_7d", justify="right")
    table.add_column("mom_30d", justify="right")
    table.add_column("avg_sent", justify="right")
    for r in rows:
        assert isinstance(r, SectorRow)
        table.add_row(
            r.sector,
            r.signal,
            _f(r.avg_rsi_14),
            _f(r.pct_above_ema200),
            _f(r.momentum_7d),
            _f(r.momentum_30d),
            _f(r.avg_sentiment_score),
        )
    return table


async def _sector_run_async(*, sector: str | None, dry_run: bool) -> None:
    from backend.agents.sector import SectorAgent

    log.info("cli.sector.run.start", sector=sector, dry_run=dry_run)
    agent = SectorAgent()
    if sector is not None and not dry_run:
        from backend.db.repositories import sector as sector_repo
        from backend.db.repositories._helpers import today_ist
        from backend.db.session import SessionLocal

        row = await agent.compute_sector(sector, today_ist())
        async with SessionLocal() as session:
            await sector_repo.bulk_upsert(session, [_row_payload(row)])
            await session.commit()
        console.print(_sector_table([row], "Sector run — APPLIED"))
        return

    res = await agent.run_all(dry_run=dry_run)
    title = "Sector run — " + ("DRY RUN (no writes)" if dry_run else "APPLIED")
    rows = [r for r in res.rows if sector is None or r.sector == sector]
    console.print(_sector_table(rows, title))
    if not dry_run:
        console.print(f"[green]Upserted {res.rows_upserted} sector rows[/green]")
    else:
        console.print("[dim]DRY RUN — nothing written to sector_signals.[/dim]")


def _row_payload(row: object) -> dict[str, object]:
    from backend.agents.sector import _row_to_dict

    return _row_to_dict(row)  # type: ignore[arg-type]


@sector_app.command("show")
def sector_show(
    limit: int = typer.Option(20, "--limit", help="Max rows."),
) -> None:
    """Show the latest stored sector signals (most momentum first)."""
    asyncio.run(_sector_show_async(limit=limit))


async def _sector_show_async(*, limit: int) -> None:
    from backend.db.repositories import sector as sector_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        rows = await sector_repo.fetch_signals(session, limit=limit)

    def _f(value: object) -> str:
        return f"{float(value):.4f}" if value is not None else "—"

    table = Table(title="Sector signals (latest)")
    table.add_column("sector")
    table.add_column("signal", style="bold")
    table.add_column("avg_rsi", justify="right")
    table.add_column("pct>ema200", justify="right")
    table.add_column("mom_7d", justify="right")
    table.add_column("mom_30d", justify="right")
    table.add_column("avg_sent", justify="right")
    for r in rows:
        table.add_row(
            r.sector,
            r.signal,
            _f(r.avg_rsi_14),
            _f(r.pct_above_ema200),
            _f(r.momentum_7d),
            _f(r.momentum_30d),
            _f(r.avg_sentiment_score),
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no sector signals — run 'sector run --all' first[/yellow]")


# -----------------------------------------------------------------------------
# fii (FII/DII / FPI flows)
# -----------------------------------------------------------------------------
@fii_app.command("run")
def fii_run(
    file: str | None = typer.Option(
        None, "--file", help="Path to a downloaded NSDL/SEBI FPI CSV file."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Parse + compute, print, write nothing."
    ),
) -> None:
    """Ingest FPI flows from a local file, compute rolling sums + signal, upsert.

    Source is a locally-downloaded NSDL/SEBI FPI file — NSE website scraping is
    barred by CLAUDE.md §2 rule 5 / §12. A missing/blocked file is non-fatal:
    the run reports 0 rows and writes nothing.
    """
    asyncio.run(_fii_run_async(file=file, dry_run=dry_run))


async def _fii_run_async(*, file: str | None, dry_run: bool) -> None:
    from backend.agents.fii_dii import FiiDiiAgent

    log.info("cli.fii.run.start", file=file, dry_run=dry_run)
    res = await FiiDiiAgent().run(path=file, dry_run=dry_run)

    if res.rows_parsed == 0:
        console.print(
            "[yellow]No FPI rows parsed.[/yellow] "
            "Pass --file with a downloaded NSDL/SEBI FPI CSV "
            "(headers: flow_date,fii_net_cr,dii_net_cr)."
        )
        return

    def _f(value: object) -> str:
        return f"{float(value):,.2f}" if value is not None else "—"

    table = Table(
        title="FII/DII (FPI) flows — last 10"
        + (" — DRY RUN (no writes)" if dry_run else " — APPLIED")
    )
    table.add_column("date")
    table.add_column("fii_net", justify="right")
    table.add_column("dii_net", justify="right")
    table.add_column("fii_5d_sum", justify="right")
    table.add_column("fii_signal", style="bold")
    for r in res.flows[-10:]:
        table.add_row(
            r.flow_date.isoformat(),
            _f(r.fii_net_cr),
            _f(r.dii_net_cr),
            _f(r.fii_5d_sum),
            r.fii_signal,
        )
    console.print(table)
    if dry_run:
        console.print("[dim]DRY RUN — nothing written to fii_dii_flows.[/dim]")
    else:
        console.print(f"[green]Upserted {res.rows_upserted} flow rows[/green]")


@fii_app.command("show")
def fii_show(
    limit: int = typer.Option(30, "--limit", help="Max rows."),
) -> None:
    """Show stored FII/DII (FPI) flows, newest first."""
    asyncio.run(_fii_show_async(limit=limit))


async def _fii_show_async(*, limit: int) -> None:
    from backend.db.repositories import fii_dii as fii_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        rows = await fii_repo.fetch_recent(session, limit=limit)

    def _f(value: object) -> str:
        return f"{float(value):,.2f}" if value is not None else "—"

    table = Table(title="FII/DII (FPI) flows")
    table.add_column("date")
    table.add_column("fii_net", justify="right")
    table.add_column("dii_net", justify="right")
    table.add_column("fii_5d_sum", justify="right")
    table.add_column("fii_signal", style="bold")
    for r in rows:
        table.add_row(
            r.flow_date.isoformat(),
            _f(r.fii_net_cr),
            _f(r.dii_net_cr),
            _f(r.fii_5d_sum),
            r.fii_signal,
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no flow rows — run 'fii run --file <csv>' first[/yellow]")


# -----------------------------------------------------------------------------
# macro
# -----------------------------------------------------------------------------
@macro_app.command("run")
def macro_run(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Fetch + compute regime, print, write nothing."
    ),
) -> None:
    """Fetch macro indicators (public sources), compute regime, upsert macro_signals."""
    asyncio.run(_macro_run_async(dry_run=dry_run))


def _macro_value(value: object) -> str:
    return f"{float(value):,.4f}" if value is not None else "—"


async def _macro_run_async(*, dry_run: bool) -> None:
    from backend.agents.macro import REGIME, MacroAgent

    log.info("cli.macro.run.start", dry_run=dry_run)
    readings = await MacroAgent().run(dry_run=dry_run)
    regime = readings[REGIME].signal

    table = Table(
        title="Macro run"
        + (" — DRY RUN (no writes)" if dry_run else " — APPLIED")
        + f"  ·  regime: {regime}"
    )
    table.add_column("indicator")
    table.add_column("value", justify="right")
    table.add_column("signal", style="bold")
    table.add_column("weight", justify="right")
    table.add_column("source")
    for ind, r in readings.items():
        table.add_row(
            ind,
            _macro_value(r.value),
            r.signal,
            _macro_value(r.regime_weight),
            r.source,
        )
    console.print(table)
    if dry_run:
        console.print("[dim]DRY RUN — nothing written to macro_signals.[/dim]")


@macro_app.command("show")
def macro_show() -> None:
    """Show the latest stored macro signals + regime."""
    asyncio.run(_macro_show_async())


async def _macro_show_async() -> None:
    from backend.db.repositories import macro as macro_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        rows = await macro_repo.fetch_latest(session)

    regime = next((r.signal for r in rows if r.indicator == "regime"), "—")
    table = Table(title=f"Macro signals (latest)  ·  regime: {regime}")
    table.add_column("indicator")
    table.add_column("value", justify="right")
    table.add_column("signal", style="bold")
    table.add_column("regime")
    table.add_column("computed_date")
    for r in rows:
        table.add_row(
            r.indicator,
            _macro_value(r.value),
            r.signal,
            regime if r.indicator == "regime" else "",
            r.computed_date.isoformat(),
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no macro signals — run 'macro run' first[/yellow]")


# -----------------------------------------------------------------------------
# risk
# -----------------------------------------------------------------------------
@risk_app.command("run")
def risk_run(
    isin: str | None = typer.Option(None, "--isin", help="Compute one ISIN only."),
    all_: bool = typer.Option(False, "--all", help="Compute all active stocks."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compute + print top 10, write nothing."
    ),
) -> None:
    """Compute per-stock risk flags from existing DB data (no external calls)."""
    if not all_ and isin is None:
        console.print("[red]pass --isin ISIN or --all[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_risk_run_async(isin=isin, dry_run=dry_run))


def _risk_num(value: object) -> str:
    return f"{float(value):.2f}" if value is not None else "—"


async def _risk_run_async(*, isin: str | None, dry_run: bool) -> None:
    from backend.agents.risk import RiskAgent

    log.info("cli.risk.run.start", isin=isin, dry_run=dry_run)
    rows = await RiskAgent().run_all(isin=isin, dry_run=dry_run)

    table = Table(
        title="Risk run — "
        + ("DRY RUN (no writes), top 10" if dry_run else "APPLIED, top 10")
    )
    table.add_column("isin")
    table.add_column("atr_pct", justify="right")
    table.add_column("volatility", style="bold")
    table.add_column("news_spike")
    table.add_column("risk_score", justify="right")
    for r in rows[:10]:
        table.add_row(
            r.isin,
            _risk_num(r.atr_pct),
            r.volatility_flag,
            "yes" if r.news_spike else "no",
            _risk_num(r.risk_score),
        )
    console.print(table)
    console.print(f"[dim]computed {len(rows)} stocks[/dim]")
    if dry_run:
        console.print("[dim]DRY RUN — nothing written to risk_signals.[/dim]")


@risk_app.command("show")
def risk_show(
    limit: int = typer.Option(20, "--limit", help="Max rows."),
    flag: str | None = typer.Option(
        None, "--flag", help="Filter by volatility_flag (low|medium|high)."
    ),
) -> None:
    """Show the latest stored risk signals (highest risk first)."""
    asyncio.run(_risk_show_async(limit=limit, flag=flag))


async def _risk_show_async(*, limit: int, flag: str | None) -> None:
    from backend.db.repositories import risk as risk_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        rows = await risk_repo.fetch_signals(session, limit=limit, flag=flag)

    table = Table(title="Risk signals (latest)" + (f" — {flag}" if flag else ""))
    table.add_column("symbol")
    table.add_column("atr_pct", justify="right")
    table.add_column("volatility_flag", style="bold")
    table.add_column("news_spike")
    table.add_column("risk_score", justify="right")
    for r, sym in rows:
        table.add_row(
            sym or r.isin,
            _risk_num(r.atr_pct),
            r.volatility_flag,
            "yes" if r.news_spike else "no",
            _risk_num(r.risk_score),
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no risk signals — run 'risk run --all' first[/yellow]")


# -----------------------------------------------------------------------------
# ranking
# -----------------------------------------------------------------------------
@ranking_app.command("run")
def ranking_run(
    all_: bool = typer.Option(False, "--all", help="Rank all active stocks."),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Compute + print top 20, write nothing."
    ),
) -> None:
    """Compute the composite 0-100 morning ranking for every stock."""
    if not all_ and not dry_run:
        console.print("[red]pass --all (optionally with --dry-run)[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_ranking_run_async(dry_run=dry_run))


def _score(value: object) -> str:
    return f"{float(value):.2f}" if value is not None else "—"


async def _ranking_run_async(*, dry_run: bool) -> None:
    from backend.agents.ranking import RankingAgent

    log.info("cli.ranking.run.start", dry_run=dry_run)
    rows = await RankingAgent().run_all(dry_run=dry_run)

    table = Table(
        title="Ranking — "
        + ("DRY RUN (no writes), top 20" if dry_run else "APPLIED, top 20")
    )
    table.add_column("#", justify="right")
    table.add_column("isin")
    table.add_column("score", justify="right")
    table.add_column("label", style="bold")
    table.add_column("f", justify="right")
    table.add_column("t", justify="right")
    table.add_column("m", justify="right")
    table.add_column("risk_pen", justify="right")
    for n, r in enumerate(rows[:20], start=1):
        table.add_row(
            str(n),
            r.isin,
            _score(r.composite_score),
            r.signal_label,
            _score(r.fundamental_score),
            _score(r.technical_score),
            _score(r.macro_score),
            _score(r.risk_penalty),
        )
    console.print(table)
    console.print(f"[dim]ranked {len(rows)} stocks[/dim]")
    if dry_run:
        console.print("[dim]DRY RUN — nothing written to stock_rankings.[/dim]")


@ranking_app.command("show")
def ranking_show(
    limit: int = typer.Option(20, "--limit", help="Max rows."),
    sector: str | None = typer.Option(None, "--sector", help="Filter by sector."),
    signal: str | None = typer.Option(
        None, "--signal", help="Filter by signal_label (e.g. bullish-watch)."
    ),
) -> None:
    """Show the latest stored rankings (highest score first)."""
    asyncio.run(_ranking_show_async(limit=limit, sector=sector, signal=signal))


async def _ranking_show_async(
    *, limit: int, sector: str | None, signal: str | None
) -> None:
    from backend.db.repositories import ranking as ranking_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        rows = await ranking_repo.fetch_rankings(
            session, limit=limit, sector=sector, signal=signal
        )

    title = "Rankings (latest)"
    if sector:
        title += f" — {sector}"
    if signal:
        title += f" — {signal}"
    table = Table(title=title)
    table.add_column("rank", justify="right")
    table.add_column("symbol")
    table.add_column("sector")
    table.add_column("score", justify="right")
    table.add_column("label", style="bold")
    table.add_column("f_score", justify="right")
    table.add_column("t_score", justify="right")
    table.add_column("m_score", justify="right")
    table.add_column("risk_penalty", justify="right")
    for n, (r, sym, sec) in enumerate(rows, start=1):
        table.add_row(
            str(n),
            sym or r.isin,
            sec or "—",
            _score(r.composite_score),
            r.signal_label,
            _score(r.fundamental_score),
            _score(r.technical_score),
            _score(r.macro_score),
            _score(r.risk_penalty),
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no rankings — run 'ranking run --all' first[/yellow]")


# -----------------------------------------------------------------------------
# report
# -----------------------------------------------------------------------------
def _parse_report_date(value: str | None) -> date | None:
    from datetime import date as _date

    from backend.db.repositories._helpers import today_ist

    if value is None:
        return None
    if value.lower() == "today":
        return today_ist()
    return _date.fromisoformat(value)


@report_app.command("run")
def report_run(
    date_: str | None = typer.Option(None, "--date", help="Report date (ISO|today)."),
    out: str | None = typer.Option(
        None, "--out", help="Obsidian dir to write {date}.md (real run only)."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Assemble + print template with placeholders; no Ollama/DB/vault.",
    ),
) -> None:
    """Generate the daily research note (LLM prose via Ollama qwen2.5:14b)."""
    asyncio.run(
        _report_run_async(as_of=_parse_report_date(date_), out=out, dry_run=dry_run)
    )


async def _report_run_async(
    *, as_of: date | None, out: str | None, dry_run: bool
) -> None:
    import sys

    from backend.agents.report import ReportAgent, word_count

    log.info("cli.report.run.start", dry_run=dry_run, out=out)
    body = await ReportAgent().run(as_of_date=as_of, out_dir=out, dry_run=dry_run)

    if dry_run:
        console.print(
            "[dim]--- DRY RUN: template with placeholders, nothing written ---[/dim]"
        )
        sys.stdout.write(body + "\n")
        return
    console.print(
        f"[green]Report generated[/green] — {word_count(body)} words"
        + (f", written to {out}/" if out else "")
    )


@report_app.command("show")
def report_show(
    date_: str | None = typer.Option(
        None, "--date", help="Print this report's body (ISO|today)."
    ),
    limit: int = typer.Option(5, "--limit", help="Rows when listing reports."),
) -> None:
    """List recent reports, or print one report's body with --date."""
    asyncio.run(_report_show_async(date_=_parse_report_date(date_), limit=limit))


async def _report_show_async(*, date_: date | None, limit: int) -> None:
    import sys

    from backend.db.repositories import report as report_repo
    from backend.db.session import SessionLocal

    async with SessionLocal() as session:
        if date_ is not None:
            row = await report_repo.fetch_report(session, report_date=date_)
            if row is None:
                console.print(f"[yellow]no report for {date_.isoformat()}[/yellow]")
                return
            sys.stdout.write(row.body_md + "\n")
            return
        rows = await report_repo.fetch_reports(session, limit=limit)

    table = Table(title="Daily reports")
    table.add_column("report_date")
    table.add_column("words", justify="right")
    table.add_column("audit_passed")
    table.add_column("macro_summary")
    for r in rows:
        table.add_row(
            r.report_date.isoformat(),
            str(r.word_count),
            "yes" if r.audit_passed else "no",
            (r.macro_summary or "")[:70],
        )
    console.print(table)
    if not rows:
        console.print("[yellow]no reports — run 'report run' first[/yellow]")


# -----------------------------------------------------------------------------
# auditor (Meta-Auditor)
# -----------------------------------------------------------------------------
@auditor_app.command("run")
def auditor_run(
    date_: str | None = typer.Option(None, "--date", help="Report date (ISO|today)."),
    out: str | None = typer.Option(
        "/vault/04_Reports/Audits", "--out", help="Obsidian dir for the audit log."
    ),
) -> None:
    """Audit a daily report against the 5 rules; set audit_passed; write log."""
    asyncio.run(_auditor_run_async(as_of=_parse_report_date(date_), out=out))


def _print_audit(result: object, title: str) -> None:
    from backend.agents.meta_auditor import AuditResult

    assert isinstance(result, AuditResult)
    table = Table(title=title)
    table.add_column("field", style="bold")
    table.add_column("value")
    table.add_row("passed", "yes" if result.passed else "no")
    table.add_row("rules_checked", str(result.rules_checked))
    table.add_row("rules_passed", str(result.rules_passed))
    table.add_row("checked_at", result.checked_at.isoformat())
    console.print(table)
    if result.failures:
        console.print("[red]Failures:[/red]")
        for f in result.failures:
            console.print(f"  - {f}")
    else:
        console.print("[green]All rules passed.[/green]")


async def _auditor_run_async(*, as_of: date | None, out: str | None) -> None:
    from backend.agents.meta_auditor import MetaAuditor

    log.info("cli.auditor.run.start", out=out)
    result = await MetaAuditor().run(report_date=as_of, out_dir=out)
    _print_audit(result, "Audit — APPLIED (audit_passed updated)")


@auditor_app.command("show")
def auditor_show(
    date_: str | None = typer.Option(None, "--date", help="Report date (ISO|today)."),
) -> None:
    """Re-run the 5 rules read-only and show the result (no DB write)."""
    asyncio.run(_auditor_show_async(as_of=_parse_report_date(date_)))


async def _auditor_show_async(*, as_of: date | None) -> None:
    from backend.agents.meta_auditor import MetaAuditor

    auditor = MetaAuditor()
    target = as_of or await auditor._latest_report_date()
    if target is None:
        console.print("[yellow]no reports to audit[/yellow]")
        return
    result = await auditor.audit_report(target)
    _print_audit(result, f"Audit (read-only) — {target.isoformat()}")


# -----------------------------------------------------------------------------
# entrypoint
# -----------------------------------------------------------------------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()
