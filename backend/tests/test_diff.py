"""Tests for backend.agents._diff — the generic keyed SCD-2 diff engine.

The diff engine is pure logic: given a `current` mapping and a `desired`
mapping (both keyed the same way), it classifies every key into added /
removed / changed / unchanged. The Universe Agent reuses it for stocks
(key=isin), index constituents (key=(index_code, isin)), and identifier
history. Equality is `==` on the values.
"""
from __future__ import annotations

from backend.agents._diff import DiffResult, diff_keyed


# ---------------------------------------------------------------------------
# 1. Everything added when current is empty.
# ---------------------------------------------------------------------------
def test_all_added_when_current_empty() -> None:
    result = diff_keyed(current={}, desired={"A": 1, "B": 2})
    assert result.added == {"A": 1, "B": 2}
    assert result.removed == {}
    assert result.changed == {}
    assert result.unchanged == {}


# ---------------------------------------------------------------------------
# 2. Everything removed when desired is empty.
# ---------------------------------------------------------------------------
def test_all_removed_when_desired_empty() -> None:
    result = diff_keyed(current={"A": 1, "B": 2}, desired={})
    assert result.added == {}
    assert result.removed == {"A": 1, "B": 2}
    assert result.changed == {}
    assert result.unchanged == {}


# ---------------------------------------------------------------------------
# 3. Identical inputs → everything unchanged.
# ---------------------------------------------------------------------------
def test_identical_is_unchanged() -> None:
    same = {"A": 1, "B": 2}
    result = diff_keyed(current=same, desired=dict(same))
    assert result.added == {}
    assert result.removed == {}
    assert result.changed == {}
    assert result.unchanged == {"A": 1, "B": 2}


# ---------------------------------------------------------------------------
# 4. Same key, different value → changed carries (old, new).
# ---------------------------------------------------------------------------
def test_changed_carries_old_and_new() -> None:
    result = diff_keyed(current={"A": 1}, desired={"A": 99})
    assert result.changed == {"A": (1, 99)}
    assert result.added == {}
    assert result.removed == {}
    assert result.unchanged == {}


# ---------------------------------------------------------------------------
# 5. A mix of all four classifications in one pass.
# ---------------------------------------------------------------------------
def test_mixed_classification() -> None:
    current = {"keep": 1, "change": 2, "drop": 3}
    desired = {"keep": 1, "change": 22, "new": 4}
    result = diff_keyed(current=current, desired=desired)
    assert result.unchanged == {"keep": 1}
    assert result.changed == {"change": (2, 22)}
    assert result.removed == {"drop": 3}
    assert result.added == {"new": 4}


# ---------------------------------------------------------------------------
# 6. Empty/empty → all buckets empty (no crash).
# ---------------------------------------------------------------------------
def test_empty_both() -> None:
    result = diff_keyed(current={}, desired={})
    assert result.added == {}
    assert result.removed == {}
    assert result.changed == {}
    assert result.unchanged == {}


# ---------------------------------------------------------------------------
# 7. Tuple keys work (used for (index_code, isin) constituent membership).
# ---------------------------------------------------------------------------
def test_tuple_keys() -> None:
    current = {("NIFTY50", "INE001"): True, ("NIFTY50", "INE002"): True}
    desired = {("NIFTY50", "INE002"): True, ("NIFTY50", "INE003"): True}
    result = diff_keyed(current=current, desired=desired)
    assert result.added == {("NIFTY50", "INE003"): True}
    assert result.removed == {("NIFTY50", "INE001"): True}
    assert result.unchanged == {("NIFTY50", "INE002"): True}
    assert result.changed == {}


# ---------------------------------------------------------------------------
# 8. Frozen / tuple values compare by equality, not identity.
# ---------------------------------------------------------------------------
def test_value_equality_not_identity() -> None:
    # Distinct objects that are == should count as unchanged.
    result = diff_keyed(current={"A": (1, "x")}, desired={"A": (1, "x")})
    assert result.unchanged == {"A": (1, "x")}
    assert result.changed == {}


# ---------------------------------------------------------------------------
# 9. counts() / has_changes() convenience reporting.
# ---------------------------------------------------------------------------
def test_counts_and_has_changes() -> None:
    result = diff_keyed(current={"a": 1}, desired={"a": 1, "b": 2})
    assert result.counts() == {"added": 1, "removed": 0, "changed": 0, "unchanged": 1}
    assert result.has_changes() is True

    no_change = diff_keyed(current={"a": 1}, desired={"a": 1})
    assert no_change.has_changes() is False


# ---------------------------------------------------------------------------
# 10. DiffResult is the public return type.
# ---------------------------------------------------------------------------
def test_returns_diffresult() -> None:
    result = diff_keyed(current={}, desired={})
    assert isinstance(result, DiffResult)
