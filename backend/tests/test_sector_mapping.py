"""Tests for backend.data_sources.sector_mapping."""
from __future__ import annotations

import pytest

from backend.data_sources.sector_mapping import (
    CANONICAL_SECTORS,
    HARMONIZATION_MAP,
    harmonize_sector,
    is_canonical_sector,
)


# ---------------------------------------------------------------------------
# 1. Known mappings normalize to canonical names.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Oil Gas & Consumable Fuels", "Energy"),
        ("Financial Services", "Financials"),
        ("Information Technology", "IT"),
        ("Fast Moving Consumer Goods", "FMCG"),
        ("Healthcare", "Pharma"),
    ],
)
def test_known_mapping_normalizes(raw: str, expected: str) -> None:
    canonical, was_mapped = harmonize_sector(raw)
    assert canonical == expected
    assert was_mapped is True


# ---------------------------------------------------------------------------
# 2. Case-insensitive + whitespace-tolerant lookup.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw",
    [
        "OIL GAS & CONSUMABLE FUELS",
        "oil gas & consumable fuels",
        "  Oil Gas & Consumable Fuels  ",
        "Oil Gas & Consumable Fuels",
    ],
)
def test_case_insensitive(raw: str) -> None:
    canonical, was_mapped = harmonize_sector(raw)
    assert canonical == "Energy"
    assert was_mapped is True


# ---------------------------------------------------------------------------
# 3. Unknown values pass through with was_mapped=False.
# ---------------------------------------------------------------------------
def test_unknown_passes_through_with_flag() -> None:
    canonical, was_mapped = harmonize_sector("Quantum Computing")
    assert canonical == "Quantum Computing"
    assert was_mapped is False


def test_unknown_passes_through_with_strip() -> None:
    canonical, was_mapped = harmonize_sector("  Quantum Computing  ")
    assert canonical == "Quantum Computing"
    assert was_mapped is False


# ---------------------------------------------------------------------------
# 4. None / empty / whitespace → (None, False).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw", [None, "", "   ", "\t\n"])
def test_none_and_empty(raw: str | None) -> None:
    canonical, was_mapped = harmonize_sector(raw)
    assert canonical is None
    assert was_mapped is False


# ---------------------------------------------------------------------------
# 5. Every map value is in the canonical set.
# ---------------------------------------------------------------------------
def test_canonical_set_no_overlap() -> None:
    for raw, canonical in HARMONIZATION_MAP.items():
        assert canonical in CANONICAL_SECTORS, (
            f"{raw!r} → {canonical!r}, not in CANONICAL_SECTORS"
        )


# ---------------------------------------------------------------------------
# 6. is_canonical_sector is case-sensitive on the output side.
# ---------------------------------------------------------------------------
def test_is_canonical_sector() -> None:
    assert is_canonical_sector("Energy") is True
    assert is_canonical_sector("energy") is False
    assert is_canonical_sector("ENERGY") is False
    assert is_canonical_sector("Quantum Computing") is False
    # Spot-check a few more canonicals.
    assert is_canonical_sector("Financials") is True
    assert is_canonical_sector("Agro") is True  # defined for future-proofing
