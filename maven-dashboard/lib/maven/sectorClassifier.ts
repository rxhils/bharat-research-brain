// Sector classification for the Nifty 500 stock-mover leaderboard.
//
// Source of truth: the committed nifty500.json snapshot's NSE "Industry" column (from NSE's
// published, downloadable index-constituents CSV - a documented static map, not a guess).
// The one refinement: "banks" uses the NSE "Financial Services" industry PLUS a company-name
// match (Indian banks all carry "Bank" in their listed name) - a documented heuristic, labeled
// as such in the limitation text. Sectors are never fabricated: symbols without industry
// metadata are excluded from sector-scoped rankings.

import nifty500 from "./data/nifty500.json";

export type SectorScope =
  | "banks" | "financials" | "it" | "pharma" | "realty" | "auto" | "metals" | "energy" | "fmcg";

type ScopeDef = { label: string; industries: string[]; nameRe?: RegExp; note?: string };

// NSE industry values verified against the committed snapshot (20 distinct industries, 500 rows).
const SCOPES: Record<SectorScope, ScopeDef> = {
  banks: {
    label: "banks", industries: ["Financial Services"], nameRe: /bank/i,
    note: "Bank filter = NSE 'Financial Services' classification plus company-name matching (documented heuristic).",
  },
  financials: { label: "financial services", industries: ["Financial Services"] },
  it: { label: "IT", industries: ["Information Technology"] },
  pharma: { label: "pharma & healthcare", industries: ["Healthcare"] },
  realty: { label: "realty", industries: ["Realty"] },
  auto: { label: "auto", industries: ["Automobile and Auto Components"] },
  metals: { label: "metals & mining", industries: ["Metals & Mining"] },
  energy: { label: "energy (oil, gas & power)", industries: ["Oil Gas & Consumable Fuels", "Power"] },
  fmcg: { label: "FMCG", industries: ["Fast Moving Consumer Goods"] },
};

const INDUSTRY_BY_SYMBOL = new Map<string, string>();
for (const c of (nifty500 as any).constituents as { s: string; industry?: string }[]) {
  if (c.s && c.industry) INDUSTRY_BY_SYMBOL.set(c.s.toUpperCase(), c.industry);
}

/** NSE industry for a Nifty 500 symbol (source: committed NSE CSV snapshot). */
export function industryOf(symbol: string): string | undefined {
  return INDUSTRY_BY_SYMBOL.get((symbol || "").toUpperCase());
}

export function sectorLabelOf(scope: SectorScope): string { return SCOPES[scope].label; }
export function sectorNoteOf(scope: SectorScope): string | undefined { return SCOPES[scope].note; }

/** True when a symbol belongs to the requested sector scope. Unknown industry -> excluded. */
export function symbolInScope(symbol: string, companyName: string, scope: SectorScope): boolean {
  const def = SCOPES[scope];
  const ind = industryOf(symbol);
  if (!ind || !def.industries.includes(ind)) return false;
  if (def.nameRe && !def.nameRe.test(companyName || "")) return false;
  return true;
}

export type SectorScopeMatch = { scope: SectorScope; label: string; note?: string };

/**
 * Detect a sector scope in a mover query. Tested against BOTH the raw query (needed for the
 * uppercase "IT" ticker-style token - lowercase "it" is a pronoun) and the normalized query.
 * PSU/private bank asks map to "banks" with an honest note (the split isn't in the sector data).
 */
export function parseSectorScope(rawQuery: string, normalized: string): SectorScopeMatch | null {
  const n = normalized || "";
  const mk = (scope: SectorScope, note?: string): SectorScopeMatch =>
    ({ scope, label: SCOPES[scope].label, note: note ?? SCOPES[scope].note });

  if (/\b(psu|public sector) banks?\b/.test(n))
    return mk("banks", "PSU vs private bank split is unavailable in the current sector data; showing all Nifty 500 banks.");
  if (/\bprivate banks?\b/.test(n))
    return mk("banks", "PSU vs private bank split is unavailable in the current sector data; showing all Nifty 500 banks.");
  if (/\bbank(s|ing)?\b/.test(n)) return mk("banks");
  if (/\b(it|tech|software|infotech) (stocks?|sector|gainers?|losers?|movers?|pack|names|companies)\b/.test(n) || /\bIT\b/.test(rawQuery || ""))
    return mk("it");
  if (/\b(pharma|pharmaceutical|healthcare|health care|drug ?makers?)\b/.test(n)) return mk("pharma");
  if (/\b(realty|real estate|property|developers?)\b/.test(n)) return mk("realty");
  if (/\b(auto|autos|automobile|automakers?|car ?makers?)\b/.test(n)) return mk("auto");
  if (/\b(metals?|steel|mining)\b/.test(n)) return mk("metals");
  if (/\b(energy|oil|gas|omcs?|power)\b/.test(n)) return mk("energy");
  if (/\b(fmcg|consumer staples)\b/.test(n)) return mk("fmcg");
  if (/\b(financials?|nbfcs?|financial (stocks?|services|names))\b/.test(n)) return mk("financials");
  return null;
}
