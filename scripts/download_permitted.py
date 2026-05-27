#!/usr/bin/env python
"""Download market data from PERMITTED sources only (CLAUDE.md §2 rule 5 / §12).

Permitted here:
  * Frankfurter API  — public ECB FX (USD/INR).
  * Yahoo Finance via yfinance — macro index/commodity/VIX history.
  * Upstox News API — ONLY if both a token AND an explicit URL are configured in
    .env (UPSTOX_ACCESS_TOKEN + UPSTOX_NEWS_URL). We never guess an endpoint.

NOTHING is fetched from nseindia.com. NSE FII/DII, bulk-deal and block-deal data
are operator-downloaded CSVs ingested through the agents' `--file` flags
(`fii run --file ...`, `promoter ingest --file ...`). No TLS impersonation, no
browser-bypass, no scraping.

Usage:
    python scripts/download_permitted.py --fx --days 90
    python scripts/download_permitted.py --macro
    python scripts/download_permitted.py --news
    python scripts/download_permitted.py --all
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = _ROOT / "data"
FRANKFURTER = "https://api.frankfurter.app"
# Macro tickers (Yahoo Finance symbols) — same set the Macro Agent uses.
MACRO_TICKERS: dict[str, str] = {
    "nifty_50": "^NSEI",
    "crude_brent": "BZ=F",
    "india_vix": "^INDIAVIX",
}
_TIMEOUT = 30.0


def _load_dotenv() -> None:
    """Populate os.environ from repo-root .env (does not override existing vars)."""
    env = _ROOT / ".env"
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _write_csv(
    path: Path, header: Sequence[str], rows: Sequence[Sequence[Any]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _report(
    label: str, path: Path, header: Sequence[str], rows: Sequence[Sequence[Any]]
) -> None:
    print(f"\n[{label}] {len(rows)} rows -> {path}")
    print("  " + " | ".join(header))
    for row in rows[:3]:
        print("  " + " | ".join(str(c) for c in row))


def download_fx(days: int) -> None:
    """USD/INR daily series from Frankfurter (public ECB data)."""
    end = date.today()
    start = end - timedelta(days=days)
    url = f"{FRANKFURTER}/{start.isoformat()}..{end.isoformat()}?from=USD&to=INR"
    try:
        resp = httpx.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[fx] FAILED: {exc}")
        return
    rates = resp.json().get("rates", {})
    rows = [[d, rates[d].get("INR")] for d in sorted(rates)]
    out = DATA_DIR / f"usdinr_{end.isoformat()}.csv"
    _write_csv(out, ["date", "usd_inr"], rows)
    _report("fx", out, ["date", "usd_inr"], rows)


def download_macro(days: int) -> None:
    """Macro index / commodity / VIX history via yfinance (Yahoo Finance)."""
    try:
        import yfinance as yf
    except ImportError:
        print("[macro] yfinance not installed — skipping.")
        return
    end = date.today()
    for name, ticker in MACRO_TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period=f"{days}d")
        except Exception as exc:  # noqa: BLE001 - external feed, best-effort
            print(f"[macro:{name}] FAILED ({ticker}): {exc}")
            continue
        if hist is None or hist.empty or "Close" not in hist.columns:
            print(f"[macro:{name}] no data for {ticker} — skipping.")
            continue
        rows = [
            [ts.date().isoformat(), round(float(close), 4)]
            for ts, close in hist["Close"].dropna().items()
        ]
        out = DATA_DIR / f"macro_{name}_{end.isoformat()}.csv"
        _write_csv(out, ["date", "close"], rows)
        _report(f"macro:{name}", out, ["date", "close"], rows)


def download_news() -> None:
    """Upstox News — only when BOTH token and an explicit URL are configured."""
    token = os.getenv("UPSTOX_ACCESS_TOKEN")
    url = os.getenv("UPSTOX_NEWS_URL")
    if not token:
        print("[news] UPSTOX_ACCESS_TOKEN not in .env — skipping (optional).")
        return
    if not url:
        print(
            "[news] UPSTOX_NEWS_URL not set — skipping. Set the exact Upstox news "
            "endpoint in .env; we never call an unverified URL."
        )
        return
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"[news] FAILED: {exc}")
        return
    payload = resp.json()
    out = DATA_DIR / f"upstox_news_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if isinstance(payload, list):
        items: list[Any] = payload
    elif isinstance(payload, dict):
        items = payload.get("data") or payload.get("articles") or []
    else:
        items = []
    print(f"\n[news] {len(items)} items -> {out}")
    for item in items[:3]:
        title = (
            item.get("title") or item.get("headline")
            if isinstance(item, dict)
            else str(item)
        )
        print(f"  - {title}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Download market data from permitted sources only (no NSE scraping)."
    )
    parser.add_argument("--fx", action="store_true", help="USD/INR from Frankfurter.")
    parser.add_argument("--macro", action="store_true", help="Macro data via yfinance.")
    parser.add_argument("--news", action="store_true", help="Upstox News (if configured).")
    parser.add_argument("--all", action="store_true", help="All permitted sources.")
    parser.add_argument(
        "--days", type=int, default=90, help="Look-back window in days (default 90)."
    )
    args = parser.parse_args(argv)

    if not (args.fx or args.macro or args.news or args.all):
        parser.error("pass at least one of --fx / --macro / --news / --all")

    _load_dotenv()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Saving to {DATA_DIR}  (permitted sources only — no nseindia.com)")

    if args.all or args.fx:
        download_fx(args.days)
    if args.all or args.macro:
        download_macro(args.days)
    if args.all or args.news:
        download_news()


if __name__ == "__main__":
    main()
