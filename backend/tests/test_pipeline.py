"""Tests for the Nightly Scheduler (Chunk 4.6) — orchestration core, no DB.

`execute_steps` runs a sequence of named async steps, isolating failures (one
agent raising must NOT stop the rest) and aggregating an overall status.
`summarize_status` is pure. Real agent wiring + APScheduler are exercised by the
live `pipeline run`, not unit-tested.
"""
from __future__ import annotations

from datetime import date

from backend.orchestration.scheduler import (
    PipelineResult,
    execute_steps,
    summarize_status,
)


# ---------------------------------------------------------------------------
# summarize_status (pure)
# ---------------------------------------------------------------------------
def test_summarize_all_success() -> None:
    assert summarize_status(["success", "success"]) == "success"


def test_summarize_all_failed() -> None:
    assert summarize_status(["failed", "failed"]) == "failed"


def test_summarize_partial() -> None:
    assert summarize_status(["success", "failed", "success"]) == "partial"


def test_summarize_empty() -> None:
    assert summarize_status([]) == "skipped"


# ---------------------------------------------------------------------------
# execute_steps — failure isolation
# ---------------------------------------------------------------------------
async def test_one_failure_does_not_stop_the_rest() -> None:
    ran: list[str] = []

    async def ok_a() -> None:
        ran.append("a")

    async def boom() -> None:
        ran.append("b")
        raise RuntimeError("agent b exploded")

    async def ok_c() -> None:
        ran.append("c")

    steps = [("a", ok_a), ("b", boom), ("c", ok_c)]
    result = await execute_steps(steps, run_date=date(2026, 5, 26))

    # All three ran despite b raising.
    assert ran == ["a", "b", "c"]
    assert isinstance(result, PipelineResult)
    assert result.status == "partial"
    assert len(result.agents_run) == 3
    by_agent = {r["agent"]: r for r in result.agents_run}
    assert by_agent["a"]["status"] == "success"
    assert by_agent["b"]["status"] == "failed"
    assert "agent b exploded" in by_agent["b"]["error"]
    assert by_agent["c"]["status"] == "success"
    assert all("duration_seconds" in r for r in result.agents_run)
    assert result.error_message and "b" in result.error_message


async def test_all_success() -> None:
    async def noop() -> None:
        return None

    result = await execute_steps(
        [("x", noop), ("y", noop)], run_date=date(2026, 5, 26)
    )
    assert result.status == "success"
    assert result.error_message is None
    assert result.total_duration_seconds >= 0


async def test_all_failed() -> None:
    async def boom() -> None:
        raise ValueError("nope")

    result = await execute_steps([("x", boom)], run_date=date(2026, 5, 26))
    assert result.status == "failed"
    assert result.run_date == date(2026, 5, 26)
