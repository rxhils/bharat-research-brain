"""Project-wide exception hierarchy.

Every error raised inside an agent's `_execute` should subclass `BharatError`.
The `BaseAgent.run` wrapper catches `BharatError` subclasses, logs them to
`data_ingestion_runs.error_message` with status='failed', and re-raises.
"""
from __future__ import annotations


class BharatError(Exception):
    """Base for all project-specific errors. Never raise raw `Exception`."""


class DataSourceError(BharatError):
    """Failure to fetch from an external data source.

    Use for HTTP errors after exhausted retries, parse failures, schema
    mismatches at the source boundary.
    """


class ValidationError(BharatError):
    """Data failed validation against expected schema or constraints."""


class DiffEngineError(BharatError):
    """Failure inside the diff engine — e.g., key collision, comparator error."""


class VaultIntegrityError(BharatError):
    """Vault file violated the frontmatter contract."""


class LLMError(BharatError):
    """LLM call failed or returned invalid output (Phase 2+)."""
