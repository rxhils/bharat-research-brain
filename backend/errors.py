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

    Optional `status_code` carries the HTTP status (when applicable) so
    callers can branch on it without parsing the message string.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        reason_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.reason_code = reason_code
        # reason_code values used in this codebase:
        #   "soft_404_html_body"  — HTTP 200 with HTML body (custom 404 page)
        #   "deferred_filename"   — filename in source map is sentinel
        #   "rate_limited"        — actual 429 (caller should not retry)
        #   "auth_required"       — actual 403 (anti-bot or auth missing)


class ValidationError(BharatError):
    """Data failed validation against expected schema or constraints."""


class DiffEngineError(BharatError):
    """Failure inside the diff engine — e.g., key collision, comparator error."""


class VaultIntegrityError(BharatError):
    """Vault file violated the frontmatter contract."""


class LLMError(BharatError):
    """LLM call failed or returned invalid output (Phase 2+)."""
