"""niftyindices.com / NSE archives data source — index-constituent CSVs.

15 indices supported (4 broad + 11 sectoral). Per CLAUDE.md §2 rule 5,
these CSVs are exchange-published and permitted for download.

URL strategy:
- PRIMARY:  https://www.niftyindices.com/IndexConstituent/<filename>.csv
- FALLBACK: https://nsearchives.nseindia.com/content/indices/<filename>.csv
  (only on HTTP 404 OR soft-404; any other error fails loud)

Soft-404 detection: niftyindices.com returns HTTP 200 with an HTML body
(`<title>Error 404</title>`) when an invalid filename is requested. We
sniff the body for HTML markers and treat as 404 — pattern likely applies
to other Indian-data-source servers.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from io import StringIO

import structlog

from backend.data_sources._http import FetchMetadata, fetch_bytes
from backend.errors import DataSourceError

log = structlog.get_logger()


PRIMARY_BASE_URL = "https://www.niftyindices.com/IndexConstituent/"
FALLBACK_BASE_URL = "https://nsearchives.nseindia.com/content/indices/"


# Sentinel for indices whose filename has not been verified.
# fetch_index_constituents raises DataSourceError(reason_code="deferred_filename")
# on access — never makes an HTTP call. Resolve via operator browser check
# and update the map in a follow-up commit.
_DEFERRED_FILENAME = "<DEFERRED>"


# ---------------------------------------------------------------------------
# index_code → filename map
# ---------------------------------------------------------------------------
NIFTYINDICES_FILENAMES: dict[str, str] = {
    "NIFTY50": "ind_nifty50list.csv",
    "NIFTY100": "ind_nifty100list.csv",
    "NIFTY200": "ind_nifty200list.csv",
    "NIFTY500": "ind_nifty500list.csv",
    "NIFTYBANK": "ind_niftybanklist.csv",
    "NIFTYIT": "ind_niftyitlist.csv",
    "NIFTYAUTO": "ind_niftyautolist.csv",
    "NIFTYPHARMA": "ind_niftypharmalist.csv",
    "NIFTYFMCG": "ind_niftyfmcglist.csv",
    "NIFTYMETAL": "ind_niftymetallist.csv",
    "NIFTYENERGY": "ind_niftyenergylist.csv",
    "NIFTYREALTY": "ind_niftyrealtylist.csv",
    "NIFTYMEDIA": "ind_niftymedialist.csv",
    "NIFTYPSUBANK": "ind_niftypsubanklist.csv",
    "NIFTYMIDCAP150": "ind_niftymidcap150list.csv",
    # Filename unverified — operator must check the niftyindices.com
    # landing page and paste the correct CSV filename. See AGENTS.md.
    "NIFTYFINSERVICE": _DEFERRED_FILENAME,
}

ALLOWED_SERIES = frozenset({"EQ", "BE", "BZ"})

_HTML_PREFIXES: tuple[bytes, ...] = (b"<!doctype", b"<html", b"<?xml")


def _looks_like_html(body: bytes) -> bool:
    """Sniff first 200 bytes (lstripped + lower-cased) for HTML/XML markers."""
    head = body.lstrip()[:200].lower()
    return any(head.startswith(p) for p in _HTML_PREFIXES)


@dataclass(frozen=True)
class Constituent:
    company_name: str
    industry: str | None
    nse_symbol: str
    series: str
    isin: str


class NiftyIndicesClient:
    """Async client for niftyindices.com / nsearchives.nseindia.com index CSVs."""

    async def fetch_index_constituents(
        self,
        index_code: str,
        *,
        cache_ttl: int = 3600,
    ) -> tuple[list[Constituent], FetchMetadata]:
        """Fetch the constituents of `index_code`.

        - Validates `index_code` is in the filename map.
        - Refuses sentinel `_DEFERRED_FILENAME` entries (raises with
          reason_code='deferred_filename').
        - Tries PRIMARY_BASE_URL. On HTTP 404 or soft-404 (HTML body),
          falls back to FALLBACK_BASE_URL once. Any other error fails
          loud per CLAUDE.md §2 rule 5.
        - Returned `meta.source_url` is the URL that actually succeeded.
        """
        if index_code not in NIFTYINDICES_FILENAMES:
            raise DataSourceError(
                f"unknown index_code {index_code!r} — "
                f"add to NIFTYINDICES_FILENAMES map"
            )
        filename = NIFTYINDICES_FILENAMES[index_code]
        if filename == _DEFERRED_FILENAME:
            raise DataSourceError(
                f"Filename for index_code={index_code!r} is not yet verified. "
                "See AGENTS.md follow-up. Operator must verify via browser "
                "at the index landing page on niftyindices.com and update the map.",
                reason_code="deferred_filename",
            )

        primary_url = f"{PRIMARY_BASE_URL}{filename}"
        fallback_url = f"{FALLBACK_BASE_URL}{filename}"
        bound = log.bind(index_code=index_code, filename=filename)

        body, meta = await self._fetch_with_fallback(
            primary_url, fallback_url, bound, cache_ttl
        )
        rows = self._parse_csv(body)
        meta = replace(meta, row_count=len(rows))
        bound.info(
            "niftyindices.fetched",
            count=len(rows),
            source_url=meta.source_url,
            http_status=meta.http_status,
            cache_hit=meta.cache_hit,
        )
        return rows, meta

    async def _fetch_with_fallback(
        self,
        primary_url: str,
        fallback_url: str,
        bound_log: structlog.stdlib.BoundLogger,
        cache_ttl: int,
    ) -> tuple[bytes, FetchMetadata]:
        """Try primary; on 404 or soft-404, fall back to FALLBACK_BASE_URL once."""
        try:
            body, meta = await fetch_bytes(primary_url, cache_ttl=cache_ttl)
            self._raise_if_html(body, primary_url, status_hint=meta.http_status)
            return body, meta
        except DataSourceError as exc:
            should_fallback = (
                exc.status_code == 404
                or exc.reason_code == "soft_404_html_body"
            )
            if not should_fallback:
                raise
            bound_log.warning(
                "niftyindices.fallback",
                primary_url=primary_url,
                fallback_url=fallback_url,
                reason=exc.reason_code or f"status_{exc.status_code}",
            )
            body, meta = await fetch_bytes(fallback_url, cache_ttl=cache_ttl)
            try:
                self._raise_if_html(body, fallback_url, status_hint=meta.http_status)
            except DataSourceError as fb_exc:
                raise DataSourceError(
                    f"soft-404 from BOTH primary ({primary_url}) and "
                    f"fallback ({fallback_url}). {fb_exc}",
                    status_code=fb_exc.status_code,
                    reason_code="soft_404_html_body",
                ) from fb_exc
            return body, meta

    @staticmethod
    def _raise_if_html(body: bytes, url: str, *, status_hint: int) -> None:
        """If body sniffs as HTML/XML, raise a soft-404 DataSourceError."""
        if not _looks_like_html(body):
            return
        preview = body[:200].decode("utf-8", errors="replace").replace("\n", " ")
        log.warning(
            "niftyindices.soft_404",
            source_url=url,
            http_status=status_hint,
            preview=preview,
        )
        raise DataSourceError(
            f"soft-404 from {url} — server returned HTTP {status_hint} with HTML body "
            f"(likely 'Error 404' page). First 200 bytes: {preview!r}",
            status_code=status_hint,
            reason_code="soft_404_html_body",
        )

    @staticmethod
    def _parse_csv(body: bytes) -> list[Constituent]:
        text = body.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(StringIO(text))
        out: list[Constituent] = []
        for row in reader:
            series = (row.get("Series") or "").strip().upper()
            if series not in ALLOWED_SERIES:
                continue
            isin = (row.get("ISIN Code") or "").strip()
            symbol = (row.get("Symbol") or "").strip()
            if not isin or not symbol:
                continue
            industry_raw = (row.get("Industry") or "").strip()
            out.append(
                Constituent(
                    company_name=(row.get("Company Name") or "").strip(),
                    industry=industry_raw or None,
                    nse_symbol=symbol,
                    series=series,
                    isin=isin,
                )
            )
        return out
