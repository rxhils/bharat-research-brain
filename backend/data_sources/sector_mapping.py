"""Sector name harmonization.

Source data (niftyindices.com `Industry` column) uses verbose, evolving
labels. Downstream agents (Ranking, Risk, Sector) need a stable canonical
vocabulary. This module is the single source of truth for that mapping.

CONVENTIONS:
- Lookup is case-insensitive (raw input is stripped + casefolded).
- Output (canonical) is title-cased / abbreviated as locked by operator.
- Unknown raw values pass through unchanged with `was_mapped=False`.
  Caller is expected to log a `data_quality_log` warn entry.
- Adding a new mapping = a code commit, reviewed.

Discovered 2026-05-08 from NIFTY500 ∪ NIFTYMIDCAP150 (~650 ISIN union):
20 distinct raw values, all fit the canonical buckets below.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical vocabulary (operator-locked).
# ---------------------------------------------------------------------------
CANONICAL_SECTORS: frozenset[str] = frozenset(
    {
        "Energy",
        "Financials",
        "IT",
        "FMCG",
        "Pharma",
        "Auto",
        "Metals",
        "Capital Goods",
        "Construction",
        "Realty",
        "Power",
        "Telecom",
        "Media",
        "Services",
        "Consumer Durables",
        "Consumer Services",
        "Chemicals",
        "Diversified",
        "Textiles",
        "Agro",
    }
)


# ---------------------------------------------------------------------------
# Raw → canonical map. Keys are EXACT strings as observed in source data.
# Lookup is case-insensitive (caller-side), so casing of keys is documentary.
# ---------------------------------------------------------------------------
HARMONIZATION_MAP: dict[str, str] = {
    # Financials
    "Financial Services": "Financials",
    # Capital Goods
    "Capital Goods": "Capital Goods",
    # Pharma / Healthcare
    "Healthcare": "Pharma",
    # Auto
    "Automobile and Auto Components": "Auto",
    # Consumer Services (e.g., retail, hospitality)
    "Consumer Services": "Consumer Services",
    # FMCG
    "Fast Moving Consumer Goods": "FMCG",
    # IT
    "Information Technology": "IT",
    # Chemicals
    "Chemicals": "Chemicals",
    # Metals
    "Metals & Mining": "Metals",
    # Power / Utilities
    "Power": "Power",
    # Energy (oil & gas)
    "Oil Gas & Consumable Fuels": "Energy",
    # Consumer Durables
    "Consumer Durables": "Consumer Durables",
    # Services (commercial / supplies)
    "Services": "Services",
    # Realty (kept distinct from Construction per operator rule)
    "Realty": "Realty",
    # Construction (cement, materials, builders) — TWO source labels merge here
    "Construction Materials": "Construction",
    "Construction": "Construction",
    # Telecom
    "Telecommunication": "Telecom",
    # Textiles
    "Textiles": "Textiles",
    # Diversified / Conglomerates
    "Diversified": "Diversified",
    # Media
    "Media Entertainment & Publication": "Media",
}


# Lookup map keyed by casefold of the raw label. Built once at import.
_LOOKUP_BY_CASEFOLD: dict[str, str] = {
    raw.strip().casefold(): canonical for raw, canonical in HARMONIZATION_MAP.items()
}


def harmonize_sector(raw: str | None) -> tuple[str | None, bool]:
    """Map a raw industry/sector label to its canonical name.

    Returns (canonical_or_passthrough, was_mapped).

    - None / empty / whitespace-only → (None, False).
    - Known mapping (case-insensitive after strip) → (canonical, True).
    - Unknown → (raw.strip(), False); caller is expected to warn-log.
    """
    if raw is None:
        return None, False
    stripped = raw.strip()
    if not stripped:
        return None, False
    canonical = _LOOKUP_BY_CASEFOLD.get(stripped.casefold())
    if canonical is not None:
        return canonical, True
    return stripped, False


def is_canonical_sector(name: str) -> bool:
    """True iff `name` is one of the operator-locked canonical sectors.

    Case-sensitive on the canonical side: callers must already pass the
    title-case form (use `harmonize_sector` to obtain it).
    """
    return name in CANONICAL_SECTORS
