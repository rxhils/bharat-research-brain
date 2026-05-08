"""Marker protocol for data source clients.

Every client in this package exposes one or more `fetch_*` async methods,
each returning a `(parsed_data, FetchMetadata)` tuple. Clients are stateless
across calls and own their own httpx connection lifecycle (per-call).
"""
from __future__ import annotations

from typing import Protocol


class DataSourceClient(Protocol):
    """Marker protocol for data source clients.

    Method signatures vary per source; this protocol only documents the
    shared contract that all clients are async and emit `FetchMetadata`.
    """
