"""Generic keyed SCD-2 diff engine.

Pure logic, no I/O. Given a `current` mapping and a `desired` mapping with
the same key space, `diff_keyed` classifies every key into one of four
buckets:

  - added     — key in `desired` only
  - removed   — key in `current` only
  - changed   — key in both, values differ (carries the (old, new) pair)
  - unchanged — key in both, values equal

The Universe Agent reuses this for three different SCD targets:
  - stocks            (key = isin,                value = tracked fields tuple)
  - index_constituents(key = (index_code, isin),  value = membership marker)
  - stock_identifiers (derived from the stocks `changed` bucket)

Equality is `==` on the values, so frozen dataclasses / tuples compare by
value, not identity.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from backend.errors import DiffEngineError

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class DiffResult(Generic[K, V]):
    """Classification of every key across `current` and `desired`."""

    added: dict[K, V] = field(default_factory=dict)
    removed: dict[K, V] = field(default_factory=dict)
    changed: dict[K, tuple[V, V]] = field(default_factory=dict)
    unchanged: dict[K, V] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        """Bucket sizes — convenient for dry-run reporting and metrics."""
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "changed": len(self.changed),
            "unchanged": len(self.unchanged),
        }

    def has_changes(self) -> bool:
        """True if anything would be inserted, closed, or modified."""
        return bool(self.added or self.removed or self.changed)


def diff_keyed(
    *,
    current: Mapping[K, V],
    desired: Mapping[K, V],
) -> DiffResult[K, V]:
    """Classify keys across `current` and `desired`. See module docstring."""
    try:
        current_keys = set(current)
        desired_keys = set(desired)
    except TypeError as exc:
        raise DiffEngineError(f"unhashable key in diff input: {exc}") from exc

    added = {k: desired[k] for k in desired_keys - current_keys}
    removed = {k: current[k] for k in current_keys - desired_keys}

    changed: dict[K, tuple[V, V]] = {}
    unchanged: dict[K, V] = {}
    for k in current_keys & desired_keys:
        old = current[k]
        new = desired[k]
        if old == new:
            unchanged[k] = new
        else:
            changed[k] = (old, new)

    return DiffResult(
        added=added,
        removed=removed,
        changed=changed,
        unchanged=unchanged,
    )
